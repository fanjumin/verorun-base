#!/bin/bash
# ==========================================================================
# setup_private_ca.sh — VeroRun 企业内网自建私域CA / 证书签发脚本（自定义域名模式）
#
# 功能：
#   - 自建私域根CA（幂等：已存在则复用，绝不重新生成——否则客户端已装根证书全部失效）
#   - 为内网域名签发服务器证书（SANs: <domain> www/platform/agent + localhost + 127.0.0.1）
#   - 证书放入 /etc/letsencrypt/live/<domain>/（官方 write_nginx_config 自动识别路径，443 自动生效）
#   - 导出 rootCA.pem 供员工客户端一次性安装
#
# 用法：
#   sudo bash setup_private_ca.sh <domain>              # Flow A'：install 之前先放证书
#   sudo bash setup_private_ca.sh <domain> --configure  # Flow B：install 之后补激活 443（仅公共版 install.sh；官方版无此命令）
#   sudo bash setup_private_ca.sh <domain> --days 730   # 自定义服务器证书有效期（默认 3650 天）
#   sudo bash setup_private_ca.sh <domain> --force      # 强制重签服务器证书（不触碰已存在根CA）
#
# 约定：
#   - 不修改任何官方脚本（install.sh / install-official.sh / common.sh）
#   - 幂等、非交互、无 TTY 依赖、外部命令失败即退出
# ==========================================================================
set -euo pipefail

# ── 常量 ────────────────────────────────────────────────
CA_DIR="/etc/verorun/ca"
LE_BASE="/etc/letsencrypt/live"
DEFAULT_DAYS=3650                        # 根CA/服务器证书默认有效期（天）
RENEW_THRESHOLD_SECONDS=2592000          # 30天；剩余有效期低于此值则自动重签
FQDN_RE='^([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'

# ── 全局变量 ────────────────────────────────────────────
DOMAIN=""
DO_CONFIGURE=0
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
用法：sudo bash $0 <domain> [选项]
选项：
  --configure   放好证书后自动执行官方 configure-domain，立即激活 443
                （仅公共版 install.sh；官方版 VR_EDITION=official 无此命令，须用 Flow A'）
  --days N      服务器证书有效期天数（默认 ${DEFAULT_DAYS}）
  --ca-name X   根CA CN（默认 "${CA_NAME}"）
  --ca-org X    根CA O（默认 "${CA_ORG}"）
  --force       强制重签服务器证书（不触碰已存在的根CA）
EOF
}

# 与官方脚本 _is_valid_fqdn 保持一致的 FQDN 校验
is_valid_fqdn() {
    local d="$1"
    case "${d}" in
        *://*|*/*|*:*|*" "*|*..*|.*|*.-*|*-.*) return 1 ;;
    esac
    echo "${d}" | grep -qE "${FQDN_RE}"
}

parse_args() {
    [ $# -ge 1 ] || { usage; exit 1; }
    DOMAIN="$1"
    shift
    while [ $# -gt 0 ]; do
        case "$1" in
            --configure) DO_CONFIGURE=1 ;;
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
    [ "$(id -u)" -eq 0 ] || fail "必须以 root 运行：sudo bash $0 <domain>"
    command -v openssl >/dev/null 2>&1 || fail "未找到 openssl，请先安装：sudo apt-get install -y openssl"
    is_valid_fqdn "${DOMAIN}" || fail "非法域名：${DOMAIN}（需为合法 FQDN，如 verorun.intra）"
    case "${CERT_DAYS}" in
        ''|*[!0-9]*) fail "证书有效期必须是正整数（--days）" ;;
    esac
    mkdir -p "${CA_DIR}"
    umask 077
}

# ── 根CA引导（幂等；Audit F-04：根私钥 AES-256 加密） ────────────────────────────────────
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

# 服务器证书已存在且剩余有效期足够 → 返回0（幂等跳过）
cert_is_valid() {
    local fullchain="$1"
    local privkey="$2"
    [ -f "${fullchain}" ] && [ -f "${privkey}" ] || return 1
    openssl x509 -in "${fullchain}" -noout -checkend "${RENEW_THRESHOLD_SECONDS}" 2>/dev/null
}

issue_server_cert() {
    local cert_dir="${LE_BASE}/${DOMAIN}"
    local fullchain="${cert_dir}/fullchain.pem"
    local privkey="${cert_dir}/privkey.pem"

    if [ "${FORCE}" != "1" ] && cert_is_valid "${fullchain}" "${privkey}"; then
        ok "服务器证书已存在且有效，跳过签发：${fullchain}"
        chmod 600 "${privkey}"
        chmod 644 "${fullchain}"
        return 0
    fi

    _TMP="$(mktemp -d)"
    log "为 ${DOMAIN} 签发服务器证书（有效期 ${CERT_DAYS} 天）..."

    openssl genrsa -out "${_TMP}/server.key" 2048
    openssl req -new -key "${_TMP}/server.key" \
        -subj "/CN=${DOMAIN}/O=${CA_ORG}" -out "${_TMP}/server.csr"
    cat > "${_TMP}/server.ext" <<EXT
subjectAltName=DNS:${DOMAIN},DNS:www.${DOMAIN},DNS:platform.${DOMAIN},DNS:agent.${DOMAIN},DNS:localhost,IP:127.0.0.1
basicConstraints=CA:FALSE
keyUsage=digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
EXT
    openssl x509 -req -in "${_TMP}/server.csr" \
        -CA "${CA_DIR}/rootCA.pem" -CAkey "${CA_DIR}/rootCA.key" -passin file:"${CA_DIR}/rootCA.key.pass" -CAcreateserial \
        -out "${_TMP}/server.crt" -days "${CERT_DAYS}" -sha256 \
        -extfile "${_TMP}/server.ext"
    cat "${_TMP}/server.crt" "${CA_DIR}/rootCA.pem" > "${_TMP}/fullchain.pem"

    mkdir -p "${cert_dir}"
    # 覆盖前备份旧证书（可安全回滚）
    if [ -f "${fullchain}" ]; then
        cp "${fullchain}" "${fullchain}.bak.$(date +%s)"
        cp "${privkey}"  "${privkey}.bak.$(date +%s)"
    fi
    install -m 600 "${_TMP}/server.key" "${privkey}"
    install -m 644 "${_TMP}/fullchain.pem" "${fullchain}"
    ok "服务器证书已安装：${fullchain}"
}

print_distribution_guide() {
    local root_pem="${CA_DIR}/rootCA.pem"
    echo ""
    echo "================================================================"
    echo "  根CA证书（分发给每台员工电脑，一次性安装）："
    echo "    ${root_pem}"
    echo ""
    echo "  Windows 安装：双击 rootCA.pem → 安装证书 → 本地计算机"
    echo "                → 受信任的根证书颁发机构"
    echo ""
    echo "  服务器证书（nginx 使用）："
    echo "    ${LE_BASE}/${DOMAIN}/fullchain.pem"
    echo "    ${LE_BASE}/${DOMAIN}/privkey.pem"
    echo "================================================================"
}

# 探测 APP_HOME（与官方脚本一致的推导规则）
default_app_home() {
    local _u="${SUDO_USER:-$(whoami)}"
    if [ "${_u}" = "root" ]; then
        echo "/root/verorun"
    else
        echo "/home/${_u}/verorun"
    fi
}

# 将 .env 的 DEPLOY_PROTOCOL 置为 https（幂等；审计 F-07：与 setup_private_ca_ip.sh 保持一致）
set_env_protocol() {
    local app_home="${APP_HOME:-$(default_app_home)}"
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

main() {
    parse_args "$@"
    preflight
    bootstrap_root_ca
    issue_server_cert
    set_env_protocol
    print_distribution_guide

    if [ "${DO_CONFIGURE}" = "1" ]; then
        local app_home="${APP_HOME:-$(default_app_home)}"
        if [ -f "${app_home}/.env" ] && grep -q "^VR_EDITION=official" "${app_home}/.env"; then
            fail "检测到官方版（VR_EDITION=official）：install-official.sh 无 configure-domain。请改用 Flow A'：先签证书，再 install-official.sh install --domain=<domain>"
        fi
        local script_dir
        script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
        local install_script="${script_dir}/install.sh"
        [ -f "${install_script}" ] || fail "未找到官方脚本：${install_script}"
        log "调用官方 configure-domain 激活 HTTPS..."
        bash "${install_script}" configure-domain "${DOMAIN}"
    else
        log "证书已就绪。下一步："
        log "  1) 公共版 install.sh → 直接运行：sudo bash deploy/install.sh install"
        log "  2) 官方版 install-official.sh → 直接运行：sudo bash deploy/install-official.sh install --domain=${DOMAIN}"
        log "  3) 已安装完毕 → 运行：sudo bash deploy/intranet/setup_private_ca.sh ${DOMAIN} --configure"
    fi
}

main "$@"
