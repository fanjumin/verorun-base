#!/bin/bash
# ==========================================================================
# setup_private_ca_ip.sh — VeroRun 企业内网 HTTPS（无自定义域名，IP 直连模式）
#
# 功能：
#   - 复用同一私域根CA（/etc/verorun/ca/，与 setup_private_ca.sh 共用，客户端只装一次根证书）
#   - 为内网 IP 签发 IP-SAN 服务器证书（SAN: IP:<lan_ip> + IP:127.0.0.1 + DNS:localhost）
#   - 生成 nginx 443 路径路由 snippet（/etc/nginx/sites-enabled/verorun-intra-lanip.conf），
#     与官方无域名 nginx 配置并存；update 后 snippet 仍存活（write_nginx_config 只覆盖 verorun.conf）
#   - 将 .env 的 DEPLOY_PROTOCOL 置为 https（保证 JWT secure cookie 正常）
#
# 用法：
#   sudo bash setup_private_ca_ip.sh                          # 自动探测内网IP
#   sudo bash setup_private_ca_ip.sh --ip 192.168.1.100       # 指定内网IP（IP变化后重跑）
#   sudo bash setup_private_ca_ip.sh --domain verorun.intra   # 追加DNS别名并入SAN（域名+IP双访问）
#   sudo bash setup_private_ca_ip.sh --days 730               # 自定义有效期（默认 3650 天）
#   sudo bash setup_private_ca_ip.sh --force                  # 强制重签服务器证书
#
# 约定：
#   - 不修改任何官方脚本（install.sh / install-official.sh / common.sh）
#   - 幂等、非交互、无 TTY 依赖、外部命令失败即退出
#   - 注意：官方无域名 nginx 配置不写入80→443跳转，用户需直接访问 https://<IP>
# ==========================================================================
set -euo pipefail

# ── 常量 ────────────────────────────────────────────────
CA_DIR="/etc/verorun/ca"
CERT_DIR="/etc/verorun/certs/lanip"
NGINX_SNIPPET="/etc/nginx/sites-enabled/verorun-intra-lanip.conf"
DEFAULT_DAYS=3650
RENEW_THRESHOLD_SECONDS=2592000          # 30天；剩余有效期低于此值则自动重签
IP_RE='^([0-9]{1,3}\.){3}[0-9]{1,3}$'
FQDN_RE='^([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'

# ── 全局变量 ────────────────────────────────────────────
LAN_IP=""
EXTRA_DOMAIN=""                          # 审计 F-08：可选的 DNS 别名（并入 SAN）
FORCE=0
CERT_DAYS="${DEFAULT_DAYS}"
CA_NAME="VeroRun Intranet Root CA"
CA_ORG="VeroRun"
_TMP=""

# ── 工具函数 ────────────────────────────────────────────
log()  { echo "[INFO] $*"; }
ok()   { echo "[OK]   $*"; }
warn() { echo "[WARN] $*"; }
fail() { echo "[FAIL] $*" >&2; exit 1; }

cleanup() {
    if [ -n "${_TMP}" ] && [ -d "${_TMP}" ]; then
        rm -rf "${_TMP}"
    fi
}
trap cleanup EXIT

usage() {
    cat <<EOF
用法：sudo bash $0 [选项]
选项：
  --ip IP        内网IP（默认自动探测；内网IP变化后重新指定并重跑）
  --domain FQDN  追加DNS别名并入SAN（如 verorun.intra；域名+IP 双访问，需 DNS/hosts 解析到本机）
  --days N       服务器证书有效期天数（默认 ${DEFAULT_DAYS}）
  --ca-name X    根CA CN（默认 "${CA_NAME}"）
  --ca-org X     根CA O（默认 "${CA_ORG}"）
  --force        强制重签服务器证书（不触碰已存在的根CA）
EOF
}

parse_args() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --ip) shift; [ $# -gt 0 ] && LAN_IP="$1" || { echo "[FAIL] --ip requires a value"; exit 1; } ;;
            --domain) shift; [ $# -gt 0 ] && EXTRA_DOMAIN="$1" || { echo "[FAIL] --domain requires a value"; exit 1; } ;;
            --force) FORCE=1 ;;
            --days) shift; [ $# -gt 0 ] && CERT_DAYS="$1" || { echo "[FAIL] --days requires a value"; exit 1; } ;;
            --ca-name) shift; [ $# -gt 0 ] && CA_NAME="$1" || { echo "[FAIL] --ca-name requires a value"; exit 1; } ;;
            --ca-org) shift; [ $# -gt 0 ] && CA_ORG="$1" || { echo "[FAIL] --ca-org requires a value"; exit 1; } ;;
            -h|--help) usage; exit 0 ;;
            *) echo "[FAIL] Unknown option: $1"; usage; exit 1 ;;
        esac
        shift
    done
}

preflight() {
    [ "$(id -u)" -eq 0 ] || fail "必须以 root 运行：sudo bash $0"
    command -v openssl >/dev/null 2>&1 || fail "未找到 openssl，请先安装：sudo apt-get install -y openssl"
    command -v nginx >/dev/null 2>&1 || fail "未找到 nginx，请先完成官方安装"
    case "${CERT_DAYS}" in
        ''|*[!0-9]*) fail "证书有效期必须是正整数（--days）" ;;
    esac
    if [ -n "${EXTRA_DOMAIN}" ]; then
        echo "${EXTRA_DOMAIN}" | grep -qE "${FQDN_RE}" || fail "非法域名：${EXTRA_DOMAIN}（--domain 需为合法 FQDN，如 verorun.intra）"
    fi
    mkdir -p "${CA_DIR}" "${CERT_DIR}"
    umask 077
}

# 自动探测第一个内网IPv4（审计 F-13+S-2：排除 docker0/br-*/veth* 等虚拟网卡，避免 SAN 与真实访问 IP 不匹配）
detect_lan_ip() {
    if [ -n "${LAN_IP}" ]; then
        echo "${LAN_IP}" | grep -qE "${IP_RE}" || fail "非法IP：${LAN_IP}"
        return 0
    fi
    local ip=""
    # 优先 ip 命令（带接口名，可精确排除虚拟网卡）；hostname -I 无接口名，仅作兜底并过滤常见虚拟网段
    if command -v ip >/dev/null 2>&1; then
        ip="$(ip -4 -o addr show scope global 2>/dev/null \
            | grep -vE '^[0-9]+: (docker0|br-|veth|virbr|vnet|tun|lo)[0-9a-f]*' \
            | grep -oE 'inet [0-9.]+' | awk '{print $2}' | head -1)" || true
    fi
    if [ -z "${ip}" ] && command -v hostname >/dev/null 2>&1; then
        ip="$(hostname -I 2>/dev/null | tr ' ' '\n' \
            | grep -vE '^(127\.|169\.254\.|172\.(1[7-9]|2[0-9]|3[01])\.)' | head -1)" || true
    fi
    [ -z "${ip}" ] && fail "无法自动探测内网IP，请用 --ip 指定"
    LAN_IP="${ip}"
    ok "探测到内网IP：${LAN_IP}"
}

# ── 根CA引导（幂等；与 setup_private_ca.sh 保持一致，改动须两边同步；Audit F-04：根私钥 AES-256 加密） ──
bootstrap_root_ca() {
    local key="${CA_DIR}/rootCA.key"
    local pem="${CA_DIR}/rootCA.pem"
    local pass_file="${CA_DIR}/rootCA.key.pass"
    if [ -f "${key}" ] && [ -f "${pem}" ]; then
        if grep -q "ENCRYPTED" "${key}" 2>/dev/null; then
            # 已加密私钥：必须存在密码文件，否则无法签发服务器证书
            [ -f "${pass_file}" ] || fail "根CA私钥已加密但缺少 ${pass_file}，无法签发证书"
            ok "根CA已存在（加密私钥），复用：${pem}"
        else
            # 旧版未加密私钥：就地升级为 AES-256 加密（幂等，仅执行一次）
            warn "检测到未加密的根CA私钥，正在升级为 AES-256 加密..."
            local pass
            pass="$(openssl rand -base64 32 | tr -d '\n')" || fail "无法生成CA私钥密码（需 openssl）"
            openssl rsa -in "${key}" -out "${key}.new" -aes256 -passout pass:"${pass}" || fail "根CA私钥加密失败"
            mv "${key}.new" "${key}"
            umask 077
            echo "${pass}" > "${pass_file}"
            chmod 400 "${pass_file}"
            chmod 600 "${key}"
            ok "根CA私钥已加密升级，复用：${pem}"
        fi
        return 0
    fi
    if [ -f "${key}" ] || [ -f "${pem}" ]; then
        fail "根CA文件不完整（key/pem 缺一），请人工检查 ${CA_DIR} 后重试"
    fi
    log "生成根CA私钥与自签根证书（有效期 ${DEFAULT_DAYS} 天）..."
    local pass
    pass="$(openssl rand -base64 32 | tr -d '\n')" || fail "无法生成CA私钥密码（需 openssl）"
    openssl genrsa -aes256 -passout pass:"${pass}" -out "${key}" 4096
    openssl req -x509 -new -key "${key}" -sha256 -days "${DEFAULT_DAYS}" \
        -subj "/CN=${CA_NAME}/O=${CA_ORG}" -out "${pem}" -passin pass:"${pass}"
    umask 077
    echo "${pass}" > "${pass_file}"
    chmod 400 "${pass_file}"
    chmod 600 "${key}"
    chmod 644 "${pem}"
    ok "根CA已创建（加密私钥）：${pem}"
}

# 证书已存在、SAN 含当前 IP（及可选的 --domain）且剩余有效期足够 → 返回0（幂等跳过）
cert_is_valid() {
    local fullchain="$1"
    local privkey="$2"
    [ -f "${fullchain}" ] && [ -f "${privkey}" ] || return 1
    openssl x509 -in "${fullchain}" -noout -checkend "${RENEW_THRESHOLD_SECONDS}" 2>/dev/null || return 1
    openssl x509 -in "${fullchain}" -noout -ext subjectAltName 2>/dev/null | grep -q "${LAN_IP}" || return 1
    if [ -n "${EXTRA_DOMAIN}" ]; then
        openssl x509 -in "${fullchain}" -noout -ext subjectAltName 2>/dev/null | grep -q "${EXTRA_DOMAIN}" || return 1
    fi
    return 0
}

issue_ip_cert() {
    local fullchain="${CERT_DIR}/fullchain.pem"
    local privkey="${CERT_DIR}/privkey.pem"

    if [ "${FORCE}" != "1" ] && cert_is_valid "${fullchain}" "${privkey}"; then
        ok "IP证书已存在且 SAN 含 ${LAN_IP}，跳过签发：${fullchain}"
        chmod 600 "${privkey}"
        chmod 644 "${fullchain}"
        return 0
    fi

    _TMP="$(mktemp -d)"
    log "为 ${LAN_IP} 签发 IP-SAN 服务器证书（有效期 ${CERT_DAYS} 天）..."

    local _san="IP:${LAN_IP},IP:127.0.0.1,DNS:localhost"
    if [ -n "${EXTRA_DOMAIN}" ]; then
        _san="${_san},DNS:${EXTRA_DOMAIN}"
        log "SAN 追加 DNS 别名：${EXTRA_DOMAIN}"
    fi

    openssl genrsa -out "${_TMP}/server.key" 2048
    openssl req -new -key "${_TMP}/server.key" \
        -subj "/CN=${LAN_IP}/O=${CA_ORG}" -out "${_TMP}/server.csr"
    cat > "${_TMP}/server.ext" <<EXT
subjectAltName=${_san}
basicConstraints=CA:FALSE
keyUsage=digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
EXT
    openssl x509 -req -in "${_TMP}/server.csr" \
        -CA "${CA_DIR}/rootCA.pem" -CAkey "${CA_DIR}/rootCA.key" -passin file:"${CA_DIR}/rootCA.key.pass" -CAcreateserial \
        -out "${_TMP}/server.crt" -days "${CERT_DAYS}" -sha256 \
        -extfile "${_TMP}/server.ext"
    cat "${_TMP}/server.crt" "${CA_DIR}/rootCA.pem" > "${_TMP}/fullchain.pem"

    # 覆盖前备份旧证书（可安全回滚）
    if [ -f "${fullchain}" ]; then
        cp "${fullchain}" "${fullchain}.bak.$(date +%s)"
        cp "${privkey}"  "${privkey}.bak.$(date +%s)"
    fi
    install -m 600 "${_TMP}/server.key" "${privkey}"
    install -m 644 "${_TMP}/fullchain.pem" "${fullchain}"
    ok "IP证书已安装：${fullchain}"
}

# 生成 443 路径路由 snippet（自包含：自带 log_format 与限流 zone，避免与 verorun.conf 依赖顺序冲突）
write_nginx_snippet() {
    log "生成 nginx snippet：${NGINX_SNIPPET}"
    # 审计 F-09：server_name 白名单化（与 write_nginx_config 的 M11 一致）——
    # 仅 LAN_IP / 可选 --domain / localhost 命中；未知 Host 由 default_server 444 拒绝（防 Host 头注入 / 缓存投毒）
    local _server_name="${LAN_IP}"
    [ -n "${EXTRA_DOMAIN}" ] && _server_name="${_server_name} ${EXTRA_DOMAIN}"
    _server_name="${_server_name} localhost"
    cat > "${NGINX_SNIPPET}" <<NGXEOF
# VeroRun Intranet HTTPS (LAN IP, no custom domain) — auto-generated by setup_private_ca_ip.sh
log_format verorun_intra_redact '\$remote_addr - \$remote_user [\$time_local] "\$request_method \$uri \$server_protocol" \$status \$body_bytes_sent "\$http_referer"';
limit_req_zone \$binary_remote_addr zone=verorun_intra:10m rate=10r/s;

server {
    listen 443 ssl http2;
    server_name ${_server_name};

    ssl_certificate     ${CERT_DIR}/fullchain.pem;
    ssl_certificate_key ${CERT_DIR}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;

    server_tokens off;
    access_log /var/log/nginx/verorun-access.log verorun_intra_redact;

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header Content-Security-Policy "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; connect-src 'self'; frame-ancestors 'self'" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # ── Admin ─────────────────────────────────
    location /admin/ {
        client_max_body_size 100M;
        limit_req zone=verorun_intra burst=20 nodelay;
        proxy_pass http://127.0.0.1:8084;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$remote_addr;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
    }

    # ── Auth / subscribe ─────────────────────
    location /auth/ {
        limit_req zone=verorun_intra burst=20 nodelay;
        proxy_pass http://127.0.0.1:8083;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$remote_addr;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
    }

    location /subscribe {
        limit_req zone=verorun_intra burst=20 nodelay;
        proxy_pass http://127.0.0.1:8083;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$remote_addr;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # ── Main ──────────────────────────────────
    location / {
        proxy_pass http://127.0.0.1:8081;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$remote_addr;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
    }
}

# 审计 F-09：未知 Host 拒绝（与 write_nginx_config 的 M11 一致）——default_server 444 catch-all
server {
    listen 443 ssl http2 default_server;
    server_name _;
    ssl_certificate     ${CERT_DIR}/fullchain.pem;
    ssl_certificate_key ${CERT_DIR}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    access_log off;
    return 444;
}
NGXEOF

    if ! nginx -t; then
        fail "nginx 配置校验失败，请检查 ${NGINX_SNIPPET}（原配置未受影响，可 rm 后重试）"
    fi
    if command -v systemctl >/dev/null 2>&1; then
        systemctl reload nginx || fail "nginx reload 失败"
    else
        nginx -s reload || fail "nginx reload 失败"
    fi
    ok "nginx 已加载 443 配置"
}

# 将 .env 的 DEPLOY_PROTOCOL 置为 https（幂等）
set_env_protocol() {
    local app_home="${APP_HOME:-}"
    if [ -z "${app_home}" ]; then
        local _u="${SUDO_USER:-$(whoami)}"
        if [ "${_u}" = "root" ]; then
            app_home="/root/verorun"
        else
            app_home="/home/${_u}/verorun"
        fi
    fi
    local env_file="${app_home}/.env"
    if [ ! -f "${env_file}" ]; then
        warn ".env 未找到（${env_file}），跳过 DEPLOY_PROTOCOL；安装完成后请重跑本脚本"
        return 0
    fi
    if grep -q "^DEPLOY_PROTOCOL=" "${env_file}"; then
        sed -i "s/^DEPLOY_PROTOCOL=.*/DEPLOY_PROTOCOL=https/" "${env_file}"
    else
        echo "DEPLOY_PROTOCOL=https" >> "${env_file}"
    fi
    ok "DEPLOY_PROTOCOL=https 已写入 ${env_file}"
}

print_distribution_guide() {
    local root_pem="${CA_DIR}/rootCA.pem"
    echo ""
    echo "================================================================"
    echo "  访问地址：https://${LAN_IP}"
    if [ -n "${EXTRA_DOMAIN}" ]; then
        echo "  （含域名）https://${EXTRA_DOMAIN}  （需 DNS/hosts 解析到 ${LAN_IP}）"
    fi
    echo ""
    echo "  根CA证书（分发给每台员工电脑，一次性安装）："
    echo "    ${root_pem}"
    echo ""
    echo "  Windows 安装：双击 rootCA.pem → 安装证书 → 本地计算机"
    echo "                → 受信任的根证书颁发机构"
    echo ""
    echo "  服务器证书（nginx 使用）："
    echo "    ${CERT_DIR}/fullchain.pem"
    echo "    ${CERT_DIR}/privkey.pem"
    echo "================================================================"
    echo ""
    log "提示：若内网IP变化，请用 --ip <新IP> 重跑本脚本重签证书并刷新 nginx。"
}

main() {
    parse_args "$@"
    preflight
    detect_lan_ip
    bootstrap_root_ca
    issue_ip_cert
    write_nginx_snippet
    set_env_protocol
    print_distribution_guide
}

main "$@"
