#!/bin/bash
# ==========================================================================
# VeroRun — deploy/lib/common.sh
# 公共函数库：被 deploy/install.sh / install-local.sh / install-dev.sh / install-code.sh
# 通过 `source` 引用。只定义函数与幂等默认值，无任何顶层执行副作用。
# ==========================================================================
# 使用约定（各脚本必须遵守）：
#   1. 在自身 default config（GIT_REPO / GIT_BRANCH / APP_HOME / SPARSE_DIRS 等）
#      定义完成之后、调用任何公共函数之前 source 本文件。
#   2. 本文件的默认值均为 : "${VAR:=...}" 形式——脚本已设置则不覆盖。
#   3. 修改公共函数只需改本文件一处，四个脚本自动生效。
#   4. install.sh（域名版）保留 B 类函数（generate_env / write_nginx_config /
#      print_summary / do_install / do_update / detect_domain / prompt_domain /
#      do_configure_domain）；无域名三脚本保留 generate_env / write_nginx_config /
#      print_summary / do_install / do_update。
# ==========================================================================

# ── 脚本名（sudoers 声明 / 提示文案引用，参数化消除硬编码） ─────────────
: "${INSTALL_SCRIPT:=$(basename "$0")}"
[ "${INSTALL_SCRIPT}" = "bash" ] && INSTALL_SCRIPT="deploy/install.sh"

# ── 幂等默认配置（脚本已设置则不覆盖） ─────────────────────────────────
# 审计 C-2：GIT_REPO 由各入口脚本（install.sh / install-local.sh / install-code.sh /
# install-dev.sh）在 source 本文件之前自行定义 —— common.sh 不定义仓库地址，避免来源混淆。
: "${GIT_BRANCH:=master}"
: "${APP_USER:=${SUDO_USER:-$(whoami)}}"
: "${APP_HOME:=/home/${APP_USER}/verorun}"
: "${VENV_DIR:=${APP_HOME}/venv}"
: "${LOG_DIR:=/var/log/verorun}"
: "${SERVICE_DIR:=/etc/systemd/system}"
: "${REGION:=global}"                # cn | global
# 审计 H-5：Sparse-checkout 白名单（基础列表）。入口脚本可通过追加扩展，
# 如 install-code.sh 在 source 后执行 SPARSE_DIRS="${SPARSE_DIRS} plugins"。
# 审计 M-1：追加 scripts/（README 引用 scripts/dev_start.py 本地开发脚本）。
: "${SPARSE_DIRS:=admin auth-center main_site health_service veroguard plugin_manager agent_matrix orchestrator i18n captcha-service shared providers themes static deploy scripts plugins/site_domains}"
: "${FORCE_UPDATE:=0}"              # 审计 C-3：update 时强制覆盖本地修改（配合 --force）
: "${PIP_MIRROR:=}"
: "${PIP_MIRROR_DETECTED:=}"
: "${VR_ADMIN_CREDS_FILE:=/root/.verorun-creds}"

# ── Colors ────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
OK="${GREEN}[OK]${NC}"; WARN="${YELLOW}[WARN]${NC}"; FAIL="${RED}[FAIL]${NC}"; INFO="${BLUE}[i]${NC}"

# 审计 F-3：全局抑制 git 交互式凭据提示（update/rollback/configure-domain 等所有 git 调用点生效），
# 任何凭据请求立即失败而非交互挂起，杜绝 origin 指向镜像时无限卡死。
export GIT_TERMINAL_PROMPT=0

# ══════════════════════════════════════════════════════════════════════
# 日志
# ══════════════════════════════════════════════════════════════════════
step() { echo -e "\n${BLUE}═══ $1 ═══${NC}"; }
done_step() { echo -e "${OK} $1"; }
fail_step() { echo -e "${FAIL} $1"; }

# ══════════════════════════════════════════════════════════════════════
# CN Network Auto-Adaptation (v1.0)
# 中国网络环境优化：apt 镜像切换 / pip 多源竞速 / git 超时保护
# 完全向后兼容：海外环境（默认源可达）不触发任何切换。
# ══════════════════════════════════════════════════════════════════════

# 1. apt 镜像：检测默认源 3s 内不可达 → 自动切换阿里云（幂等，marker 文件控制）
_ensure_apt_mirror() {
    local _marker="/etc/apt/.verorun_mirror_applied"
    [ -f "${_marker}" ] && return 0
    if command -v curl >/dev/null 2>&1 && curl -s --connect-timeout 3 http://archive.ubuntu.com >/dev/null 2>&1; then
        touch "${_marker}"; return 0
    fi
    echo -e "${WARN} Ubuntu default mirror unreachable → switching to Aliyun"
    cp /etc/apt/sources.list "/etc/apt/sources.list.bak.$(date +%s)"
    sed -i 's|http://[^/]*archive.ubuntu.com|http://mirrors.aliyun.com|g' /etc/apt/sources.list
    sed -i 's|http://[^/]*security.ubuntu.com|http://mirrors.aliyun.com|g' /etc/apt/sources.list
    sed -i 's|http://[^/]*ports.ubuntu.com|http://mirrors.aliyun.com|g'   /etc/apt/sources.list
    touch "${_marker}"
    echo -e "${OK} apt mirror → Aliyun"
}

# 2. pip 镜像：多源竞速（阿里云 → 清华 → 官方）选响应最快，仅检测一次
_detect_pip_mirror() {
    [ -n "${PIP_MIRROR_DETECTED:-}" ] && return 0
    echo -e "${INFO} Detecting fastest pip mirror..."
    local _best="" _best_time=999
    for _t in \
        "aliyun|https://mirrors.aliyun.com/pypi/simple/pip/|-i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com" \
        "tsinghua|https://pypi.tuna.tsinghua.edu.cn/simple/pip/|-i https://pypi.tuna.tsinghua.edu.cn/simple/ --trusted-host pypi.tuna.tsinghua.edu.cn" \
        "pypi|https://pypi.org/simple/pip/|"; do
        local _name="${_t%%|*}"; local _rest="${_t#*|}"; local _url="${_rest%%|*}"; local _args="${_rest#*|}"
        local _start=$(date +%s%N)
        if command -v curl >/dev/null 2>&1 && curl -s --connect-timeout 3 --max-time 5 "${_url}" -o /dev/null 2>/dev/null; then
            local _elapsed=$(( ($(date +%s%N) - _start) / 1000000 ))
            echo -e "  ${INFO} ${_name}: ${_elapsed}ms"
            if [ "${_elapsed}" -lt "${_best_time}" ]; then
                _best_time="${_elapsed}"; _best="${_args}"
            fi
        else
            echo -e "  ${WARN} ${_name}: unreachable"
        fi
    done
    if [ -n "${_best}" ]; then PIP_MIRROR="${_best}"; fi
    PIP_MIRROR_DETECTED=1
    echo -e "${OK} pip mirror → ${PIP_MIRROR:-default}"
}

# 3. git clone 超时保护（60s）+ 浅克隆加速；失败给出明确指引
# 注意：不执行 fetch --unshallow —— sparse-checkout 不依赖完整历史，
#      补全历史反而在 CN 网络下重新下载全量数据，违背加速目的。
_clone_with_timeout() {
    local _repo=$1 _dest=$2 _branch=$3
    echo -e "${INFO} Cloning ${_repo} (timeout 60s, shallow)..."
    # 审计 M-2：--no-single-branch 让浅克隆（--depth 1）同时携带标签，git describe --tags 可正常用于版本检测
    if timeout 60 git clone --depth 1 --no-single-branch -b "${_branch}" "${_repo}" "${_dest}" 2>&1; then
        return 0
    fi
    echo -e "${FAIL} git clone failed or timed out (60s)"
    echo -e "${INFO} Possible causes:"
    echo -e "${INFO}   1. GitHub unreachable (DNS pollution / GFW)"
    echo -e "${INFO}   2. SSH key not configured (private repo)"
    echo -e "${INFO}   3. Network too slow"
    echo -e "${INFO} Workarounds:"
    echo -e "${INFO}   • Use a proxy: export https_proxy=... && re-run"
    echo -e "${INFO}   • Pre-clone manually: git clone ${_repo} ${_dest}"
    echo -e "${INFO}   • For public base: use the HTTPS installer from verorun-base"
    exit 1
}

# --prefer-binary: prefer wheels, fall back to source build
# 审计 C-4：安装失败显式报错 + 最多重试 3 次（网络抖动 / 镜像临时超时可自动恢复）
_pip_install() {
    _detect_pip_mirror
    local _attempt=1 _max=3
    while [ "${_attempt}" -le "${_max}" ]; do
        if sudo -u "${APP_USER}" "${VENV_DIR}/bin/pip" install --timeout 120 --prefer-binary ${PIP_MIRROR} "$@"; then
            return 0
        fi
        echo -e "${WARN} pip install failed (attempt ${_attempt}/${_max}): $*"
        _attempt=$((_attempt + 1))
        [ "${_attempt}" -le "${_max}" ] && sleep 5
    done
    echo -e "${FAIL} pip install failed after ${_max} attempts: $*"
    echo -e "${INFO} Check mirror reachability (${PIP_MIRROR:-default}) or dependency conflicts, then re-run."
    return 1
}

# ══════════════════════════════════════════════════════════════════════
# Git SSH auth setup（HTTPS 公开仓库自动跳过）
# ══════════════════════════════════════════════════════════════════════
ensure_git_auth() {
    if echo "${GIT_REPO}" | grep -q '^https://'; then
        # 审计 F-1：HTTPS 公开仓库同样校验已存在的 origin，防止被改为 ghfast.top/ghproxy 等镜像后 fetch 卡死
        if [ -d "${APP_HOME}/.git" ]; then
            local current_url
            current_url=$(git -C "${APP_HOME}" remote get-url origin 2>/dev/null || echo "")
            if [ -n "${current_url}" ] && [ "${current_url}" != "${GIT_REPO}" ]; then
                echo -e "${WARN} Git origin mismatch detected — correcting:"
                echo -e "${WARN}   was: ${current_url}"
                echo -e "${WARN}   now: ${GIT_REPO}"
                git -C "${APP_HOME}" remote set-url origin "${GIT_REPO}"
                done_step "Git remote corrected to ${GIT_REPO}"
            fi
        fi
        return 0
    fi
    local ssh_key="/root/.ssh/id_ed25519"
    if [ ! -f "${ssh_key}" ]; then
        echo -e "${INFO} Generating SSH deploy key for git operations..."
        mkdir -p /root/.ssh
        ssh-keygen -t ed25519 -N "" -f "${ssh_key}" -C "verorun-deploy-$(hostname)" >/dev/null 2>&1
        chmod 600 "${ssh_key}"
        chmod 644 "${ssh_key}.pub"
        echo -e "${YELLOW}╔══════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${YELLOW}║  ADD THIS DEPLOY KEY TO GITHUB (one-time setup):           ║${NC}"
        echo -e "${YELLOW}╠══════════════════════════════════════════════════════════════╣${NC}"
        echo -e "${YELLOW}║  URL: https://github.com/fanjumin/verorun-code/settings/keys/new${NC}"
        echo -e "${YELLOW}╠══════════════════════════════════════════════════════════════╣${NC}"
        cat "${ssh_key}.pub" | while read -r line; do
            echo -e "${GREEN}║  ${line}${NC}"
        done
        echo -e "${YELLOW}╚══════════════════════════════════════════════════════════════╝${NC}"
        echo -e "${WARN} After adding the key, re-run this script to continue."
        exit 0
    fi
    if [ ! -f /root/.ssh/known_hosts ] || ! grep -q '^github\.com' /root/.ssh/known_hosts 2>/dev/null; then
        ssh-keyscan github.com >> /root/.ssh/known_hosts 2>/dev/null || true
    fi
    if [ -d "${APP_HOME}/.git" ]; then
        local current_url
        current_url=$(git -C "${APP_HOME}" remote get-url origin 2>/dev/null || echo "")
        if echo "${current_url}" | grep -q '^https://'; then
            git -C "${APP_HOME}" remote set-url origin "${GIT_REPO}"
            done_step "Git remote switched to SSH"
        fi
    fi
}

# ══════════════════════════════════════════════════════════════════════
# Git 仓库地址自动解析（审计 Y-1：一键部署跨网络可用，不假定用户预装 git）
# - HTTPS 公开仓库（install.sh / install-local.sh）：用 curl 探测 git 智能
#   HTTP 端点（等价 git ls-remote，但仅依赖 curl），直连 GitHub 不可达时
#   自动降级到 ghfast.top / ghproxy.net 镜像（v0.45.0 的 ghproxy.com 已死，
#   此处镜像为实测可用；支持多级降级）。
# - SSH 私有仓库（install-code.sh / install-dev.sh）：自动配置 SSH over 443
#   （ssh.github.com:443），绕过国内被封锁的 22 端口；仓库地址本身不变。
# 在 do_install / do_update 拉码前调用，四个脚本经本公共函数统一生效。
# ══════════════════════════════════════════════════════════════════════
_probe_git_url() {
    # 探测 git 智能 HTTP 端点（等价 git ls-remote 的 HTTP 侧，仅用 curl）
    local _url="$1"
    if command -v curl >/dev/null 2>&1; then
        local _code
        _code=$(curl -sS -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 10 \
            "${_url}/info/refs?service=git-upload-pack" 2>/dev/null || echo "000")
        case "${_code}" in
            200|301|302|403) return 0 ;;
        esac
        return 1
    fi
    if command -v git >/dev/null 2>&1; then
        if GIT_TERMINAL_PROMPT=0 timeout 20 git ls-remote "${_url}" >/dev/null 2>&1; then
            return 0
        fi
        return 1
    fi
    # 无探测工具（极罕见）：无法判断，交给后续流程直接尝试
    return 1
}

_setup_ssh_over_443() {
    # SSH 22 端口国内常被封锁：不可达时自动改用 ssh.github.com:443
    local _ssh_conf="/root/.ssh/config"
    if grep -q "Host github.com" "${_ssh_conf}" 2>/dev/null; then
        return 0  # 已配置，幂等
    fi
    if timeout 5 bash -c "exec 3<>/dev/tcp/github.com/22" 2>/dev/null; then
        return 0  # 22 端口可达，无需改写
    fi
    mkdir -p /root/.ssh
    cat >> "${_ssh_conf}" << 'SSHCONF'

# VeroRun auto: SSH over 443 for CN networks (port 22 blocked)
Host github.com
    HostName ssh.github.com
    Port 443
    User git
SSHCONF
    chmod 600 "${_ssh_conf}" 2>/dev/null || true
    echo -e "${WARN} GitHub SSH port 22 unreachable — switched to ssh.github.com:443"
}

_resolve_git_repo() {
    # 仅 install/update 需要真实访问远端仓库，其余模式跳过
    case "${DEPLOY_MODE:-}" in
        install|update) ;;
        *) return 0 ;;
    esac

    # SSH 私有仓库（install-code.sh / install-dev.sh）：SSH over 443 规避 22 封锁
    if echo "${GIT_REPO}" | grep -q '^git@github.com:'; then
        _setup_ssh_over_443
        return 0
    fi

    # 仅处理 github.com 的 HTTPS 公开仓库；自定义镜像/Gitee 等地址不探测直接使用
    if ! echo "${GIT_REPO}" | grep -q '^https://github.com/'; then
        return 0
    fi

    local _direct="${GIT_REPO}"
    local _candidates=()
    # REGION=cn 时镜像优先（直连通常更慢/不可达）；global 直连优先，失败再降级
    if [ "${REGION:-global}" = "cn" ]; then
        _candidates=(
            "https://ghfast.top/${_direct#https://}"
            "https://ghproxy.net/${_direct#https://}"
            "${_direct}"
        )
    else
        _candidates=(
            "${_direct}"
            "https://ghfast.top/${_direct#https://}"
            "https://ghproxy.net/${_direct#https://}"
        )
    fi

    local _url
    for _url in "${_candidates[@]}"; do
        if _probe_git_url "${_url}"; then
            if [ "${_url}" != "${_direct}" ]; then
                if [ "${REGION:-global}" = "cn" ]; then
                    echo -e "${INFO} Using git mirror: ${_url}"
                else
                    echo -e "${WARN} GitHub direct unreachable — switching to mirror: ${_url}"
                fi
            fi
            GIT_REPO="${_url}"
            return 0
        fi
    done
    echo -e "${FAIL} Git repo unreachable (tried direct + mirrors)."
    echo -e "${INFO} Fix network, or run with:"
    echo -e "${INFO}   GIT_REPO=<reachable-url> sudo bash ${INSTALL_SCRIPT} ${DEPLOY_MODE}"
    exit 1
}

# ══════════════════════════════════════════════════════════════════════
# HTTPS 证书自动签发（审计 Y-2：仅 production + 域名已配置时启用）
# 流程：安装 certbot → certbot --nginx 签发（交互输入邮箱）→ 更新 .env
# DEPLOY_PROTOCOL=https → 重载 nginx。失败不阻塞安装（Let's Encrypt 有
# 频率限制；域名需已解析到本服务器）。无 TTY 时沿用脚本现有交互降级模式，
# 跳过签发并给出手动命令。
# ══════════════════════════════════════════════════════════════════════
_setup_ssl_cert() {
    if [ "${DEPLOY_TYPE:-}" != "production" ] || [ -z "${DOMAIN:-}" ]; then
        return 0  # 仅域名版 install.sh 触发；其余三脚本天然跳过
    fi
    step "HTTPS certificate (Let's Encrypt)"

    local _email="${SSL_EMAIL:-}"

    # --ssl-email flag 传入：跳过 TTY 检查和交互输入
    if [ -z "${_email}" ]; then
        if ! { exec 3<>/dev/tty; } 2>/dev/null; then
            exec 3>&-
            echo -e "${WARN} Non-interactive shell — skipping cert issuance."
            echo -e "${INFO} Run later: sudo apt-get install -y certbot python3-certbot-nginx && sudo certbot --nginx -d ${DOMAIN} -d www.${DOMAIN} -d platform.${DOMAIN} -d agent.${DOMAIN}"
            return 0
        fi
        exec 3>&-
        read -r -p "  Let's Encrypt email (for renewal notices, optional): " _email < /dev/tty
    fi

    export DEBIAN_FRONTEND=noninteractive
    if ! apt-get install -y certbot python3-certbot-nginx 2>&1; then
        echo -e "${WARN} certbot install failed — skipping SSL (run manually later)."
        return 0
    fi

    local _cert_args=()
    if [ -z "${_email}" ]; then
        _cert_args=("--register-unsafely-without-email")
    else
        _cert_args=("--agree-tos" "-m" "${_email}")
    fi

    # 签发失败不阻塞安装：证书频率限制 / 域名未解析 / 80 端口不可达等
    if certbot --nginx --non-interactive "${_cert_args[@]}" \
        -d "${DOMAIN}" -d "www.${DOMAIN}" -d "platform.${DOMAIN}" -d "agent.${DOMAIN}" \
        --redirect 2>&1; then
        if grep -q "^DEPLOY_PROTOCOL=" "${APP_HOME}/.env"; then
            sed -i "s/^DEPLOY_PROTOCOL=.*/DEPLOY_PROTOCOL=https/" "${APP_HOME}/.env"
        else
            echo "DEPLOY_PROTOCOL=https" >> "${APP_HOME}/.env"
        fi
        nginx -t && systemctl reload nginx 2>/dev/null || true
        done_step "HTTPS certificate issued — DEPLOY_PROTOCOL=https"
    else
        echo -e "${WARN} certbot failed (domain must resolve to this server). SSL skipped — run manually:"
        echo -e "${INFO}   sudo certbot --nginx -d ${DOMAIN} -d www.${DOMAIN} -d platform.${DOMAIN} -d agent.${DOMAIN}"
    fi
}

# ══════════════════════════════════════════════════════════════════════
# 目录冲突处理（文档 verorun-deploy-guide.html §6.3：备份/删除/中止）
# ══════════════════════════════════════════════════════════════════════
resolve_directory_conflict() {
    local target_dir="$1"

    # 目录不存在 → 正常流程
    if [ ! -d "${target_dir}" ]; then
        return 0
    fi

    # 已是 git 仓库 → 可以安全更新
    if [ -d "${target_dir}/.git" ]; then
        echo -e "${OK} Existing VeroRun installation detected at ${target_dir}"
        return 0
    fi

    # 目录存在但不是 git 仓库 → 交互式选择
    echo ""
    echo -e "${WARN} ═══════════════════════════════════════════════════════"
    echo -e "${WARN}  Directory conflict detected:"
    echo -e "${WARN}    ${target_dir}"
    echo -e "${WARN}"
    echo -e "${WARN}  This directory exists but is NOT a VeroRun installation."

    # 无 TTY（如 curl|sudo bash 管道）：自动删除，无需交互
    if ! { exec 3<>/dev/tty; } 2>/dev/null; then
        exec 3>&-
        echo -e "${WARN}  Non-interactive mode — auto-removing and proceeding."
        echo -e "${WARN} ═══════════════════════════════════════════════════════"
        if [ -z "${target_dir}" ] || [ "${target_dir}" = "/" ] || [ "${target_dir}" = "${HOME}" ]; then
            echo -e "${FAIL} Refusing to remove dangerous path: ${target_dir}"
            exit 1
        fi
        rm -rf "${target_dir}"
        echo -e "${OK} Removed. Proceeding with installation."
        return 0
    fi
    exec 3>&-

    echo -e "${WARN}  What would you like to do?"
    echo -e "${WARN}"
    echo -e "${INFO}  [1] Backup and reinstall"
    echo -e "${INFO}      → Move to ${target_dir}.bak.$(date +%Y%m%d%H%M%S) and proceed"
    echo -e "${INFO}  [2] Delete and reinstall"
    echo -e "${INFO}      → Remove ${target_dir} completely and proceed"
    echo -e "${INFO}  [3] Abort installation"
    echo -e "${INFO}      → Exit now. You can manually resolve and re-run."
    echo -e "${WARN} ═══════════════════════════════════════════════════════"

    while true; do
        read -r -p "  Your choice [1/2/3]: " _choice </dev/tty

        case "${_choice}" in
            1)
                local _bak="${target_dir}.bak.$(date +%Y%m%d%H%M%S)"
                echo -e "${INFO} Backing up to ${_bak} ..."
                mv "${target_dir}" "${_bak}"
                echo -e "${OK} Backup complete. Proceeding with installation."
                return 0
                ;;
            2)
                # 安全防护：拒绝删除危险路径
                if [ -z "${target_dir}" ] || [ "${target_dir}" = "/" ] || [ "${target_dir}" = "${HOME}" ]; then
                    echo -e "${FAIL} Refusing to remove dangerous path: ${target_dir}"
                    exit 1
                fi
                echo -e "${INFO} Removing ${target_dir} ..."
                rm -rf "${target_dir}"
                echo -e "${OK} Removed. Proceeding with installation."
                return 0
                ;;
            3)
                echo -e "${INFO} Installation aborted by user."
                exit 0
                ;;
            *)
                echo -e "${WARN} Please enter 1, 2, or 3"
                ;;
        esac
    done
}

# ══════════════════════════════════════════════════════════════════════
# DEBUG 强制禁用（生产门禁：install/update 前必须 APP_DEBUG=false 且 FLASK_DEBUG=0）
# ══════════════════════════════════════════════════════════════════════
assert_debug_disabled() {
    local _dbg
    # Check APP_DEBUG
    _dbg=$(grep -E '^APP_DEBUG=' "${APP_HOME}/.env" 2>/dev/null | tail -1 | cut -d= -f2)
    case "${_dbg}" in
        1|true|TRUE|True|on|yes)
            echo -e "${FAIL} Production install aborted: APP_DEBUG is enabled in .env"
            echo -e "${INFO} Set APP_DEBUG=false in ${APP_HOME}/.env and re-run"
            exit 1 ;;
    esac
    # Check FLASK_DEBUG
    _dbg=$(grep -E '^FLASK_DEBUG=' "${APP_HOME}/.env" 2>/dev/null | tail -1 | cut -d= -f2)
    case "${_dbg}" in
        1|true|TRUE|True|on|yes)
            echo -e "${FAIL} Production install aborted: FLASK_DEBUG is enabled in .env"
            echo -e "${INFO} Set FLASK_DEBUG=0 in ${APP_HOME}/.env and re-run"
            exit 1 ;;
    esac
}

# ══════════════════════════════════════════════════════════════════════
# .env 补齐缺失密钥（幂等）
# ══════════════════════════════════════════════════════════════════════
update_env() {
    local env_file="${APP_HOME}/.env"
    if [ ! -f "${env_file}" ]; then
        generate_env
        return
    fi

    local missing=()

    # ── 必需的密钥（缺失则随机生成） ──
    for key in PLUGIN_LICENSE_SECRET CAPTCHA_SECRET_KEY DEV_ACCOUNTS_ENCRYPTION_KEY LICENSE_SERVER_SECRET PROBE_SECRET INTERNAL_SERVICE_TOKEN; do
        if ! grep -q "^${key}=" "${env_file}" 2>/dev/null; then
            local val
            val=$(python3 -c "import secrets; print(secrets.token_hex(32))")
            echo "${key}=${val}" >> "${env_file}"
            missing+=("${key}")
        fi
    done

    # ── 审计 H-2：必需的配置项（缺失则用默认值补齐，绝不覆盖已有值） ──
    # 早期版本升级后可能缺少 DEPLOY_PROTOCOL / APP_REGION / DEPLOY_MARKET 等，
    # 缺失会导致服务启动失败或运行时行为不一致，此处统一补齐。
    local _dom
    # 取最后一行 DEPLOY_DOMAIN，避免历史重复行导致多行变量污染
    _dom=$(grep "^DEPLOY_DOMAIN=" "${env_file}" 2>/dev/null | tail -1 | cut -d= -f2)
    # 审计 NEW-H3：DEPLOY_PROTOCOL 不做自动推断（有域名 ≠ 已配 HTTPS 证书）。
    # 缺失时默认 http，由用户根据实际 TLS 配置自行修改 .env。
    while read -r _k _v; do
        if ! grep -q "^${_k}=" "${env_file}" 2>/dev/null; then
            echo "${_k}=${_v}" >> "${env_file}"
            missing+=("${_k}")
        fi
    done << EOF
DEPLOY_MARKET cn
DEPLOY_DOMAIN ${_dom}
DEPLOY_PROTOCOL http
DB_PATH ${APP_HOME}/data/x7k2m9a4.db
PG_HOST localhost
PG_PORT 5432
PG_DB appdb
PG_USER app
APP_MODE main
PLUGIN_AUTO_INSTALL 0
APP_REGION ${REGION:-global}
DASHSCOPE_TEXT_KEY 
OPENAI_API_KEY 
DEEPSEEK_API_KEY 
EOF

    for key in APP_DEBUG:false FLASK_DEBUG:0; do
        local k="${key%%:*}" v="${key##*:}"
        if ! grep -q "^${k}=" "${env_file}" 2>/dev/null; then
            echo "${k}=${v}" >> "${env_file}"
            missing+=("${k}")
        fi
    done

    if [ ${#missing[@]} -gt 0 ]; then
        echo -e "${OK} Filled missing keys: ${missing[*]}"
        chmod 600 "${env_file}"
    else
        echo -e "${OK} All keys are present in .env"
    fi
}

# ══════════════════════════════════════════════════════════════════════
# systemd 服务（四服务 + guardian 守护进程）
# ══════════════════════════════════════════════════════════════════════
write_systemd_services() {
    local env_file="${APP_HOME}/.env"
    # 审计 H-4 修复：gunicorn worker 数不再硬编码 -w 2。
    # 默认保持 2（向后兼容，不改变现有部署资源占用）；
    # 高并发场景可用 VR_WORKERS 环境变量覆盖，例如：
    #   VR_WORKERS=4 sudo bash deploy/install.sh update
    local _workers="${VR_WORKERS:-2}"
    write_one_service() {
        local name=$1 port=$2 module=$3 extra_args="${4:-}" runner="${5:-}" runtime_dir="${6:-}"
        local file="${SERVICE_DIR}/${name}.service"
        if [ -n "${runner}" ]; then
            local exec_cmd="${VENV_DIR}/bin/python ${APP_HOME}/${runner} -w ${_workers} -b 127.0.0.1:${port} ${extra_args} ${module}:app"
        else
            local exec_cmd="${VENV_DIR}/bin/gunicorn -w ${_workers} -b 127.0.0.1:${port} ${extra_args} ${module}:app"
        fi
        local rt_block=""
        if [ -n "${runtime_dir}" ]; then
            rt_block="RuntimeDirectory=${runtime_dir}
RuntimeDirectoryMode=0755"
        fi
        cat > "${file}" << SVCEOF
[Unit]
Description=VeroRun ${name}
After=network.target postgresql.service

[Service]
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_HOME}
EnvironmentFile=${env_file}
ExecStart=${exec_cmd}
Restart=always
RestartSec=5
KillSignal=SIGTERM
TimeoutStopSec=30
TimeoutStartSec=300
# Startup health check: /health must return 200, otherwise systemd marks startup failed
ExecStartPost=${APP_HOME}/deploy/health_check.sh ${port}
StandardOutput=append:${LOG_DIR}/${name}.log
StandardError=append:${LOG_DIR}/${name}.log
${rt_block}

[Install]
WantedBy=multi-user.target
SVCEOF
        systemctl daemon-reload
        systemctl enable "${name}"
    }
    # 8081 — Main site (homepage public_home.html)
    write_one_service "verorun-main" 8081 "auth_server" "--timeout 120 --log-level warning"
    # 8083 — Platform / User Console
    write_one_service "verorun-auth" 8083 "main_site" "--timeout 120 --log-level warning"
    # 8084 — Admin (uses run_gunicorn.py to avoid platform/ shadowing stdlib)
    # RuntimeDirectory=verorun → systemd creates /run/verorun/ owned by APP_USER on service start.
    write_one_service "verorun-admin" 8084 "admin.app" "--timeout 300 --max-requests=1000 --graceful-timeout=30 --log-level warning --config admin/gunicorn_config.py" "admin/run_gunicorn.py" "verorun"
    # 8085 — Health Check
    write_one_service "verorun-health" 8085 "health_service.app" "--timeout 30 --graceful-timeout=30 --log-level warning"
    # ── verorun-guardian (standalone daemon, no HTTP port) ──
    write_guardian_service
    write_guardian_env
}

write_guardian_service() {
    local file="${SERVICE_DIR}/verorun-guardian.service"
    cat > "${file}" << 'GDEVEOF'
[Unit]
Description=VeroGuard — Unified Guardian Daemon (Health + Integrity + Heartbeat)
After=network.target postgresql.service
Wants=verorun-health.service verorun-main.service verorun-admin.service verorun-auth.service

[Service]
Type=simple
# Guardian runs as root to access system integrity checks (file hashes,
# process monitoring, and systemd journal) that require elevated privileges.
User=root
WorkingDirectory=GDEVDIR
EnvironmentFile=-/etc/default/verorun-guardian
ExecStart=GDEVDIR/venv/bin/python GDEVDIR/veroguard/guardian.py
Restart=always
RestartSec=5
RuntimeDirectory=verorun-guardian
RuntimeDirectoryMode=0755
KillSignal=SIGTERM
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
GDEVEOF
    sed -i "s|GDEVDIR|${APP_HOME}|g" "${file}"
    systemctl daemon-reload
    systemctl enable verorun-guardian
}

write_guardian_env() {
    local env_file="/etc/default/verorun-guardian"
    local probe_secret=""
    if [ -f "${APP_HOME}/.env" ]; then
        probe_secret=$(grep "^PROBE_SECRET=" "${APP_HOME}/.env" 2>/dev/null | cut -d= -f2) || true
        [ -n "${probe_secret}" ] && probe_secret="PROBE_SECRET=${probe_secret}"
    fi
    cat > "${env_file}" << GENVEOF
# VeroGuard Guardian environment config — generated by ${INSTALL_SCRIPT}
GUARDIAN_PROJECT_DIR=${APP_HOME}
GUARDIAN_LOG_FILE=${LOG_DIR}/verorun-guardian.log
GUARDIAN_CHECK_INTERVAL=30
GUARDIAN_MAX_FAILURES=3
GUARDIAN_COOLDOWN=300
GUARDIAN_INTEGRITY_INTERVAL=300
GUARDIAN_HEARTBEAT_INTERVAL=300
GUARDIAN_WEBHOOK_URL=
GUARDIAN_REMOTE_URL=https://api.verorun.com
${probe_secret}
DEPLOYMENT_CODE=
GENVEOF
    chmod 600 "${env_file}"
}

# ══════════════════════════════════════════════════════════════════════
# sudoers — 一键更新权限（声明式、幂等）
# ══════════════════════════════════════════════════════════════════════
write_sudoers() {
    local sudoers_file="/etc/sudoers.d/verorun"
    cat > "${sudoers_file}" << SUEOF
# Managed by VeroRun ${INSTALL_SCRIPT} — regenerated on every install/update
# Grants ${APP_USER} passwordless one-click update for VeroRun services
${APP_USER} ALL=(root) NOPASSWD: /bin/bash ${APP_HOME}/deploy/${INSTALL_SCRIPT} update
${APP_USER} ALL=(root) NOPASSWD: /bin/bash ${APP_HOME}/deploy/${INSTALL_SCRIPT} restart
${APP_USER} ALL=(root) NOPASSWD: /usr/bin/systemctl restart verorun-main
${APP_USER} ALL=(root) NOPASSWD: /usr/bin/systemctl restart verorun-auth
${APP_USER} ALL=(root) NOPASSWD: /usr/bin/systemctl restart verorun-admin
${APP_USER} ALL=(root) NOPASSWD: /usr/bin/systemctl restart verorun-health
${APP_USER} ALL=(root) NOPASSWD: /usr/bin/systemctl restart verorun-guardian
${APP_USER} ALL=(root) NOPASSWD: /usr/bin/systemctl restart nginx
SUEOF
    chmod 440 "${sudoers_file}"
    visudo -c -f "${sudoers_file}" || {
        echo -e "${FAIL} Invalid sudoers file — restoring previous state"
        rm -f "${sudoers_file}"
        exit 1
    }
}

# ══════════════════════════════════════════════════════════════════════
# 服务重启（含启动等待轮询 + nginx）
# ══════════════════════════════════════════════════════════════════════
restart_services() {
    local services=("verorun-admin" "verorun-auth" "verorun-main" "verorun-health" "verorun-guardian")
    for svc in "${services[@]}"; do
        if systemctl is-enabled --quiet "${svc}" 2>/dev/null; then
            systemctl restart "${svc}"
            local _waited=0
            while [ $_waited -lt 60 ]; do
                if systemctl is-active --quiet "${svc}" 2>/dev/null; then
                    echo -e "${OK} ${svc} is running"
                    break
                fi
                sleep 2
                _waited=$((_waited + 2))
            done
            if [ $_waited -ge 60 ]; then
                echo -e "${FAIL} ${svc} failed to start — check: journalctl -u ${svc} -n 20"
            fi
        else
            echo -e "${WARN} ${svc} not configured, skipping"
        fi
    done
    if systemctl is-enabled --quiet nginx 2>/dev/null; then
        systemctl restart nginx
        echo -e "${OK} nginx restarted"
    fi
}

# ══════════════════════════════════════════════════════════════════════
# 依赖扫描
# ══════════════════════════════════════════════════════════════════════
check_system_deps() {
    local pkg
    for pkg in python3 python3-venv python3-pip python3-dev nginx git curl wget \
        build-essential libpq-dev libssl-dev postgresql postgresql-client; do
        if ! dpkg -s "${pkg}" >/dev/null 2>&1; then
            return 1
        fi
    done
    return 0
}

check_python_deps() {
    [ -x "${VENV_DIR}/bin/python" ] || return 1
    [ -f "${APP_HOME}/requirements.txt" ] || return 1
    local freeze line pkg
    freeze=$("${VENV_DIR}/bin/pip" list --format=freeze 2>/dev/null) || return 1
    while read -r line; do
        [ -z "${line}" ] && continue
        # 审计 H-6：跳过注释 / pip 选项 / -e 可编辑安装 / git+ / http(s) / file: 等非普通包行
        case "${line}" in
            \#*|--*|-e*|git+*|http://*|https://*|file:*|[-!+]*|.) continue ;;
        esac
        pkg="${line%%[<>=!~;@]*}"
        pkg="${pkg%%\[*}"   # 去掉 extras（如 flask[async]）
        pkg=$(printf '%s' "${pkg}" | tr 'A-Z' 'a-z' | tr '_' '-')
        # 精确匹配已安装包名（^ 锚定行首，避免前缀误匹配如 discord.py 命中 discord）
        printf '%s\n' "${freeze}" | grep -qi "^${pkg}==\|^${pkg} @ " || return 1
    done < "${APP_HOME}/requirements.txt"
    return 0
}

# ══════════════════════════════════════════════════════════════════════
# 模式检测
# ══════════════════════════════════════════════════════════════════════
detect_mode() {
    local mode="${1:-}"
    if [ -n "$mode" ]; then
        DEPLOY_MODE="$mode"
    elif [ -f "${APP_HOME}/.env" ]; then
        DEPLOY_MODE="update"
    else
        DEPLOY_MODE="install"
    fi
    echo -e "${INFO} Deploy mode: ${DEPLOY_MODE}"
}

# ══════════════════════════════════════════════════════════════════════
# 管理员凭据交互创建（install 模式、TTY 存活时调用）
# ══════════════════════════════════════════════════════════════════════
prompt_admin_creds() {
    case "${DEPLOY_MODE}" in install) ;; *) return 0 ;; esac
    [ -f "${VR_ADMIN_CREDS_FILE}" ] && return 0

    # --admin-user / --admin-pass flag 传入：直接写入凭据文件，跳过交互
    if [ -n "${VR_ADMIN_USERNAME:-}" ] && [ -n "${VR_ADMIN_PASSWORD:-}" ]; then
        printf 'VR_ADMIN_USERNAME="%s"\nVR_ADMIN_PASSWORD="%s"\n' "${VR_ADMIN_USERNAME}" "${VR_ADMIN_PASSWORD}" > "${VR_ADMIN_CREDS_FILE}"
        chmod 600 "${VR_ADMIN_CREDS_FILE}"
        trap 'rm -f "${VR_ADMIN_CREDS_FILE}"' EXIT
        echo -e "${OK} Admin credentials set via flag"
        return 0
    fi

    # 非交互管道（curl | sudo bash 无 TTY）：自动降级，凭据由 seed_data.py 生成
    if ! { exec 3<>/dev/tty; } 2>/dev/null; then
        echo -e "${INFO} Non-interactive shell — admin credentials auto-generated"
        return 0
    fi
    exec 3>&-

    echo "" > /dev/tty
    echo -e "${INFO} Create the administrator account for VeroRun" > /dev/tty

    local _user="" _pass="" _pass2=""
    echo -n "  Admin username: " > /dev/tty
    read -r _user < /dev/tty
    _user="${_user//[^a-zA-Z0-9._-]/}"
    while [ -z "${_user}" ]; do
        echo -e "${WARN} Username cannot be empty" > /dev/tty
        echo -n "  Admin username: " > /dev/tty
    read -r _user < /dev/tty
    done

    echo -n "  Admin password: " > /dev/tty
    read -r -s _pass < /dev/tty
    echo "" > /dev/tty
    while [ -z "${_pass}" ]; do
        echo -e "${WARN} Password cannot be empty" > /dev/tty
        echo -n "  Admin password: " > /dev/tty
    read -r -s _pass < /dev/tty
        echo "" > /dev/tty
    done

    echo -n "  Confirm password: " > /dev/tty
    read -r -s _pass2 < /dev/tty
    echo "" > /dev/tty
    while [ "${_pass}" != "${_pass2}" ]; do
        echo -e "${WARN} Passwords do not match, try again" > /dev/tty
        echo -n "  Admin password: " > /dev/tty
    read -r -s _pass < /dev/tty
        echo "" > /dev/tty
        echo -n "  Confirm password: " > /dev/tty
    read -r -s _pass2 < /dev/tty
        echo "" > /dev/tty
    done

    printf 'VR_ADMIN_USERNAME="%s"\nVR_ADMIN_PASSWORD="%s"\n' "${_user}" "${_pass}" > "${VR_ADMIN_CREDS_FILE}"
    chmod 600 "${VR_ADMIN_CREDS_FILE}"
    # 审计 C2 加固：脚本异常退出时清理凭据文件（prompt 仅在 install 模式调用，无 EXIT trap 冲突）
    trap 'rm -f "${VR_ADMIN_CREDS_FILE}"' EXIT
    echo -e "${OK} Admin credentials saved"
}

# ══════════════════════════════════════════════════════════════════════
# 健康检查
# ══════════════════════════════════════════════════════════════════════
health_check() {
    echo ""
    local all_ok=true

    check_port() {
        local port=$1 name=$2
        local code
        # 审计 H-7：--max-time 10 防止服务接受连接但永不响应时 curl 挂起导致健康检查卡死
        code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 10 "http://127.0.0.1:${port}/" 2>/dev/null || echo "000")
        if [ "$code" != "000" ]; then
            echo -e "  ${OK} ${name} (:${port}) -> HTTP ${code}"
        else
            echo -e "  ${FAIL} ${name} (:${port}) -> no response"
            all_ok=false
        fi
    }

    check_port 8081 "verorun-main"
    check_port 8083 "verorun-auth"
    check_port 8084 "verorun-admin"
    check_port 8085 "verorun-health"

    if systemctl is-active --quiet verorun-guardian 2>/dev/null; then
        echo -e "  ${OK} verorun-guardian (systemd)"
    else
        echo -e "  ${FAIL} verorun-guardian (inactive)"
        all_ok=false
    fi

    echo ""
    echo -e "${INFO} Migration log check:"
    for svc in verorun-admin verorun-auth verorun-main; do
        journalctl -u "${svc}" --since "1 min ago" 2>/dev/null | grep -i "\[Migration\]" | tail -2 || true
    done

    if $all_ok; then
        echo -e "\n${OK} All services healthy"
    else
        echo -e "\n${FAIL} Some services are unhealthy — check logs"
        UPDATE_FAILED=1
    fi
}

# ══════════════════════════════════════════════════════════════════════
# VeroGuard 完整性清单构建（审计 NEW-H1：四种部署模式统一调用）
# ══════════════════════════════════════════════════════════════════════
build_veroguard_manifest() {
    step "Build integrity manifest (VeroGuard)"
    # 用 .env 中的 PROBE_SECRET 生成守护进程完整性基准清单。
    # 官方端依赖该清单校验客户端文件完整性；文件缺失时降级跳过（不中断安装）。
    if [ -f "${APP_HOME}/veroguard/tools/build_manifest.py" ]; then
        sudo -u "${APP_USER}" bash -c "set -a; source ${APP_HOME}/.env; set +a; cd ${APP_HOME} && PYTHONPATH=${APP_HOME} ${VENV_DIR}/bin/python veroguard/tools/build_manifest.py --project-dir ${APP_HOME} --output ${APP_HOME}/veroguard/data/manifest.json.enc --secret \"\${PROBE_SECRET}\"" \
            || echo -e "${WARN} Manifest build failed — VeroGuard integrity check unavailable"
    else
        echo -e "${WARN} build_manifest.py not found — VeroGuard integrity check unavailable"
    fi
    done_step "Integrity manifest built"
}

# ══════════════════════════════════════════════════════════════════════
# 种子数据
# ══════════════════════════════════════════════════════════════════════
do_seed() {
    step "Seed initial data"
    if [ ! -f "${VENV_DIR}/bin/python" ]; then
        echo -e "${FAIL} Python venv not found at ${VENV_DIR}"
        echo -e "${INFO} Run '${INSTALL_SCRIPT}' first"
        exit 1
    fi

    # Seed mode explicitly requested via command-line → always execute (overrides --approve-migrate gate)
    if [ "${DEPLOY_MODE}" = "seed" ]; then
        APPROVE_MIGRATE=1
    fi

    # Seed is grouped under the same manual gate as DB migration
    if [ "${APPROVE_MIGRATE:-0}" != "1" ]; then
        echo -e "${WARN} Skipped seed data — admin account NOT created, admin panel inaccessible"
        echo -e "${WARN} To create admin account now, run: sudo bash deploy/install.sh seed"
        return 0
    fi

    # Read credentials from temp file (set by prompt_admin_creds)
    VR_ADMIN_USERNAME=""
    VR_ADMIN_PASSWORD=""
    if [ -f "${VR_ADMIN_CREDS_FILE}" ]; then
        # shellcheck disable=SC1090
        source "${VR_ADMIN_CREDS_FILE}"
        rm -f "${VR_ADMIN_CREDS_FILE}"
    fi

    # 审计 NEW-M1：凭据在此处统一确定，保证 print_summary 展示与 seed_data.py 实际写入的密码一致。
    # 无凭据时生成默认管理员（administrator + 随机密码），并始终经环境变量传入 seed_data.py。
    if [ -z "${VR_ADMIN_USERNAME}" ]; then
        VR_ADMIN_USERNAME="administrator"
    fi
    if [ -z "${VR_ADMIN_PASSWORD}" ]; then
        VR_ADMIN_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(8))")
    fi

    # 审计 C1：管理员凭据经环境变量传入 seed_data.py，避免出现在进程命令行
    sudo -u "${APP_USER}" env VR_ADMIN_USERNAME="${VR_ADMIN_USERNAME}" VR_ADMIN_PASSWORD="${VR_ADMIN_PASSWORD}" \
        "${VENV_DIR}/bin/python" "${APP_HOME}/deploy/seed_data.py"
    echo -e "${OK} Seed data injected"
}

# ══════════════════════════════════════════════════════════════════════
# 回滚（统一使用 before_commit 保存点，缺失时 fallback HEAD~1）
# ══════════════════════════════════════════════════════════════════════
do_rollback() {
    step "Rollback to previous version"
    cd "${APP_HOME}"
    git reflog --oneline -5 | head -5
    local target_commit
    if [ -f "${APP_HOME}/.rollback/before_commit" ]; then
        target_commit=$(head -1 "${APP_HOME}/.rollback/before_commit" | awk '{print $1}')
        echo -e "${INFO} Rolling back to saved commit: ${target_commit}"
    else
        target_commit="HEAD~1"
        echo -e "${WARN} No saved commit found, falling back to HEAD~1"
    fi
    if git reset --hard "${target_commit}"; then
        systemctl restart verorun-admin verorun-auth verorun-main verorun-health verorun-guardian
        echo -e "${OK} Rolled back to $(git log --oneline -1)"
    else
        echo -e "${FAIL} Rollback failed"
    fi
}

# ══════════════════════════════════════════════════════════════════════
# C-1 统一部署函数（审计 R4 激活：四入口脚本共用，DEPLOY_TYPE 驱动）
# DEPLOY_TYPE: production | lan | code | dev
# 由各入口脚本在 source 本文件前定义（install.sh=production, install-local=lan,
# install-code=code, install-dev=dev）。四个入口脚本不再各自定义同名函数，
# Bash 不再发生"后定义覆盖先定义"，此处统一版本直接生效。
# ══════════════════════════════════════════════════════════════════════

# ── .env 生成：注释头 / DEPLOY_DOMAIN / DEPLOY_PROTOCOL 由 DEPLOY_TYPE 驱动 ──
generate_env() {
    local env_file="${APP_HOME}/.env"
    local force="${1:-}"

    if [ -f "${env_file}" ] && [ "${force}" != "force" ]; then
        echo -e "${WARN} .env already exists, skipping"
        return
    fi

    if [ -f "${env_file}" ] && [ "${force}" = "force" ]; then
        cp "${env_file}" "${env_file}.bak.$(date +%s)" 2>/dev/null || true
        if [ "${DEPLOY_TYPE}" = "production" ]; then
            echo -e "${INFO} Existing .env backed up"
        fi
    fi

    if [ -z "${PG_PASSWORD:-}" ]; then
        PG_PASSWORD=$(python3 -c "import secrets; print(secrets.token_hex(16))")
    fi
    JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    FLASK_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    ENCRYPTION_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    PLUGIN_LICENSE_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    CAPTCHA_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    DEV_ACCOUNTS_ENCRYPTION_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    LICENSE_SERVER_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    PROBE_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    INTERNAL_SERVICE_TOKEN=$(python3 -c "import secrets; print(secrets.token_hex(32))")

    # ── DEPLOY_TYPE 驱动：注释头 / DOMAIN / PROTOCOL ──
    local _env_header="VeroRun config — auto-generated by ${INSTALL_SCRIPT} (no-domain / LAN mode)"
    local _deploy_domain=""
    local _deploy_protocol="http"
    case "${DEPLOY_TYPE}" in
        production)
            _env_header="VeroRun production config — auto-generated by ${INSTALL_SCRIPT}"
            _deploy_domain="${DOMAIN:-}"
            _deploy_protocol="https"
            ;;
        code)
            _env_header="VeroRun config — auto-generated by ${INSTALL_SCRIPT} (no-domain / LAN mode, full plugins)"
            ;;
    esac

    cat > "${env_file}" << ENVEOF
# ${_env_header}
DEPLOY_MARKET=cn
DEPLOY_DOMAIN=${_deploy_domain}
DEPLOY_PROTOCOL=${_deploy_protocol}
DB_PATH=${APP_HOME}/data/x7k2m9a4.db
PG_HOST=localhost
PG_PORT=5432
PG_DB=appdb
PG_USER=app
PG_PASSWORD=${PG_PASSWORD}
JWT_SECRET=${JWT_SECRET}
FLASK_SECRET_KEY=${FLASK_SECRET}
ENCRYPTION_KEY=${ENCRYPTION_KEY}
APP_MODE=main

# v2.1.0 — 内部服务令牌
INTERNAL_SERVICE_TOKEN=${INTERNAL_SERVICE_TOKEN}

# Production defaults: DEBUG must stay disabled (assert_debug_disabled enforces on install/update)
APP_DEBUG=false
FLASK_DEBUG=0

# Phase 1 — Security hardening keys (2026-07-28)
PLUGIN_LICENSE_SECRET=${PLUGIN_LICENSE_SECRET}
CAPTCHA_SECRET_KEY=${CAPTCHA_SECRET_KEY}
DEV_ACCOUNTS_ENCRYPTION_KEY=${DEV_ACCOUNTS_ENCRYPTION_KEY}
LICENSE_SERVER_SECRET=${LICENSE_SERVER_SECRET}

# Deployments do not auto-install/enable plugins by default (install manually in admin)
PLUGIN_AUTO_INSTALL=0

# VeroGuard — daemon encrypted communication key (official side and client must match)
PROBE_SECRET=${PROBE_SECRET}

# API Keys (intentionally empty — set real values before enabling AI features)
DASHSCOPE_TEXT_KEY=
OPENAI_API_KEY=
DEEPSEEK_API_KEY=

# Region routing (VeroRun 0.43.0+)
APP_REGION=${REGION}
ENVEOF

    chown "${APP_USER}:${APP_USER}" "${env_file}"
    chmod 600 "${env_file}"
}

# ── Nginx：DOMAIN 非空→域名多 server；空→LAN 单 server ──
write_nginx_config() {
    local nginx_conf="/etc/nginx/sites-available/verorun.conf"
    local nginx_enabled="/etc/nginx/sites-enabled/verorun.conf"

    if [ -n "${DOMAIN:-}" ]; then
        # ── 域名模式：主域 / platform / agent 三 server ──
        cat > "${nginx_conf}" << NGXEOF
# VeroRun Nginx — auto-generated by ${INSTALL_SCRIPT}

# ── Main domain ────────────────────────────────
server {
    listen 80;
    server_name ${DOMAIN} www.${DOMAIN};
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # ── Admin ─────────────────────────────────
    location /admin/ {
        client_max_body_size 100M;
        proxy_pass http://127.0.0.1:8084;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
    }

    # ── Auth / subscribe ─────────────────────
    location /auth/ {
        proxy_pass http://127.0.0.1:8083;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /subscribe {
        proxy_pass http://127.0.0.1:8083;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # ── Main site ───────────────────────────────
    location / {
        proxy_pass http://127.0.0.1:8081;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
    }
}

# ── Platform subdomain ─────────────────────────
server {
    listen 80;
    server_name platform.${DOMAIN};
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    location / {
        proxy_pass http://127.0.0.1:8083;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}

# ── Agent subdomain ────────────────────────────
server {
    listen 80;
    server_name agent.${DOMAIN};
    client_max_body_size 100M;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    location / {
        proxy_pass http://127.0.0.1:8084;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
NGXEOF
    else
        # ── 无域名模式：default_server 单 server（/admin/ 统一含 client_max_body_size 100M，审计 R4 L-B） ──
        cat > "${nginx_conf}" << NGXEOF
# VeroRun Nginx — no-domain mode (auto-generated by ${INSTALL_SCRIPT})

server {
    listen 80 default_server;
    # No server_name: match every Host (localhost / LAN IP)
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # ── Admin panel ─────────────────────────
    location /admin/ {
        client_max_body_size 100M;
        proxy_pass http://127.0.0.1:8084;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
    }

    # ── User console / auth ─────────────────
    location /auth/ {
        proxy_pass http://127.0.0.1:8083;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /subscribe {
        proxy_pass http://127.0.0.1:8083;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # ── Main site (default route) ───────────
    location / {
        proxy_pass http://127.0.0.1:8081;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
    }
}
NGXEOF
    fi

    # 审计 M-2 修复：删除 default 站点前先备份（幂等——已有备份不覆盖），
    # 避免同机运行的其他 Web 服务（phpMyAdmin/Grafana 等）依赖 default 配置时被误伤。
    if [ -f /etc/nginx/sites-available/default ] && [ ! -f /etc/nginx/sites-available/default.bak.verorun ]; then
        cp /etc/nginx/sites-available/default /etc/nginx/sites-available/default.bak.verorun
    fi
    rm -f /etc/nginx/sites-enabled/default
    ln -sf "${nginx_conf}" "${nginx_enabled}"
}

# ── Fresh install：DEPLOY_TYPE 驱动域名询问 / 拉取文案 / 清理 / 服务启动 ──
do_install() {
    step "Dependency check"
    if [ "${SKIP_DEPS:-0}" = "1" ]; then
        echo -e "${WARN} --skip-deps: skipping dependency installation"
    elif check_system_deps && check_python_deps; then
        echo -e "${OK} All dependencies already installed — skipping"
        SKIP_DEPS=1
    else
        echo -e "${WARN} Some dependencies are missing (system or Python packages)"
        # 审计 H-2 修复：curl | sudo bash 管道执行时 stdin 已被脚本内容占用，
        # 必须 < /dev/tty 从终端读取，否则 read 会吞掉后续脚本内容。
        # 提示符改用 echo -n > /dev/tty 输出——read -p 提示走 stderr，
        # 在 2>&1 | tail 管道下会被缓冲吞掉导致"看似卡死"。
        echo -n "Install dependencies now? [Y/n] " > /dev/tty
        read -r _ans < /dev/tty || _ans=""
        case "${_ans}" in
            n|N) echo -e "${WARN} Skipping dependency installation"; SKIP_DEPS=1 ;;
            *)   echo -e "${OK} Will install missing dependencies" ;;
        esac
    fi
    done_step "Dependency check complete"

    step "System dependencies"
    export DEBIAN_FRONTEND=noninteractive
    if [ "${SKIP_DEPS:-0}" != "1" ]; then
        _ensure_apt_mirror
        apt-get update
        apt-get install -y python3 python3-venv python3-pip python3-dev \
            nginx git curl wget build-essential libpq-dev libssl-dev
    else
        if [ "${DEPLOY_TYPE}" = "production" ]; then
            echo -e "${WARN} --skip-deps: skipping system dependency installation"
        else
            echo -e "${WARN} Skipped (deps already present or --skip-deps)"
        fi
    fi
    done_step "System dependencies installed"

    : "${PG_PASSWORD:=$(python3 -c "import secrets; print(secrets.token_hex(16))")}"

    step "PostgreSQL"
    if ! systemctl is-active --quiet postgresql 2>/dev/null; then
        if [ "${SKIP_DEPS:-0}" = "1" ]; then
            echo -e "${FAIL} postgresql not running, but dependency installation was skipped"
            exit 1
        fi
        apt-get install -y postgresql postgresql-client
        systemctl enable --now postgresql
    fi
    # 审计 C1 达标：密码经管道(stdin)传入 psql，不进入进程命令行（psql argv 仅 "-q"）
    # 审计 Y-4 修复：服务器 fs.protected_regular=2（sticky 全局可写目录内禁止写他人
    # 文件，连 root 也不例外）导致 mktemp→chown postgres→printf 写文件被内核 EACCES
    # 拒绝。改用 stdin 管道，无文件、无属主、无 /tmp，与内核防护完全解耦。
    local _pwd="${PG_PASSWORD//\'/\'\'}"
    if sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='app'" 2>/dev/null | grep -qE '^\s*1\s*$'; then
        printf "ALTER ROLE app WITH LOGIN PASSWORD '%s';\n" "${_pwd}" | sudo -u postgres psql -q 2>/dev/null || true
    else
        printf "CREATE ROLE app WITH LOGIN PASSWORD '%s';\n" "${_pwd}" | sudo -u postgres psql -q 2>/dev/null || true
    fi
    # 审计 H-3：显式验证角色与数据库是否创建成功，失败立即中止（不再被静默吞掉）
    if ! sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='app'" 2>/dev/null | grep -qE '^\s*1\s*$'; then
        echo -e "${FAIL} FATAL: PostgreSQL role 'app' not created. Check pg_hba.conf auth method (md5/scram requires password auth)."
        exit 1
    fi
    # 审计 Y-3 修复：R4 重构时 CREATE DATABASE 被丢弃，全新服务器必然在此处失败——
    # 补回建库逻辑（createdb -O app appdb，不存在才建），再复查，失败才报错退出。
    if ! sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='appdb'" 2>/dev/null | grep -qE '^\s*1\s*$'; then
        sudo -u postgres createdb -O app appdb 2>/dev/null || true
    fi
    if ! sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='appdb'" 2>/dev/null | grep -qE '^\s*1\s*$'; then
        echo -e "${FAIL} FATAL: PostgreSQL database 'appdb' not created."
        exit 1
    fi
    # 铁律：安装脚本只允许创建系统库，插件数据库一律不建
    done_step "PostgreSQL is running"

    step "Create directories"
    mkdir -p "${APP_HOME}" "${APP_HOME}/data" "${LOG_DIR}"
    mkdir -p "${APP_HOME}/.cache/llm" \
             "${APP_HOME}/.cache/sessions" \
             "${APP_HOME}/.cache/agents"
    chown -R "${APP_USER}:${APP_USER}" "${APP_HOME}" 2>/dev/null || true
    chown -R "${APP_USER}:${APP_USER}" "${LOG_DIR}" 2>/dev/null || true
    done_step "Directories ready"

    # Git 仓库自动解析（审计 Y-1）：HTTPS 直连不可达时自动切镜像；SSH 走 443
    _resolve_git_repo

    ensure_git_auth

    # ── DEPLOY_TYPE 驱动：Pull code 步骤标签（commit hash 在拉取完成后动态求值） ──
    local _pull_step="Pull code"
    local _pull_suffix=""           # 审计 R5 BUG-1：仅存格式后缀，此处不做命令替换
    case "${DEPLOY_TYPE}" in
        code)
            _pull_step="Pull code (full — includes all plugins)"
            _pull_suffix=" (full, all plugins)"
            ;;
        dev)
            _pull_step="Pull code (plugins excluded — clone ~50% smaller)"
            _pull_suffix=" (plugins excluded)"
            ;;
    esac
    step "${_pull_step}"
    # 审计 H3 修复：目录冲突时交互式三选一（备份/删除/中止），不再直接 rm -rf
    resolve_directory_conflict "${APP_HOME}"
    if [ -d "${APP_HOME}/.git" ]; then
        git config --global --add safe.directory "${APP_HOME}" 2>/dev/null || true
        cd "${APP_HOME}"
        # 审计 F-2：抑制 git 交互式凭据提示 + 超时保护，避免 origin 指向镜像时无限卡死
        git remote set-url origin "${GIT_REPO}"
        export GIT_TERMINAL_PROMPT=0
        if ! timeout 60 git fetch origin "${GIT_BRANCH}" 2>&1; then
            echo -e "${FAIL} Git fetch failed or timed out (60s) — aborting"
            echo -e "${INFO} Check origin remote: git -C ${APP_HOME} remote -v"
            echo -e "${INFO} If it points to a mirror (ghfast.top/ghproxy), reset it:"
            echo -e "${INFO}   git -C ${APP_HOME} remote set-url origin ${GIT_REPO}"
            exit 1
        fi
        git reset --hard "origin/${GIT_BRANCH}"
    else
        _clone_with_timeout "${GIT_REPO}" "${APP_HOME}" "${GIT_BRANCH}"
    fi
    # 应用 sparse-checkout 白名单（幂等；拉取后立即收窄工作区，仅保留运行时目录）
    if ! git -C "${APP_HOME}" sparse-checkout set ${SPARSE_DIRS} 2>/dev/null; then
        git -C "${APP_HOME}" sparse-checkout init --cone 2>/dev/null || true
        if ! git -C "${APP_HOME}" sparse-checkout set ${SPARSE_DIRS} 2>/dev/null; then
            echo -e "${WARN} sparse-checkout failed — working tree may include non-runtime files"
        fi
    fi
    # 审计 NEW-H2：仅 production 统一清理三个无域名脚本
    if [ "${DEPLOY_TYPE}" = "production" ]; then
        rm -f "${APP_HOME}/deploy/install-local.sh" "${APP_HOME}/deploy/install-code.sh" "${APP_HOME}/deploy/install-dev.sh"
    fi
    # Clean stale __pycache__ before chown (avoids race-condition failures)
    find "${APP_HOME}" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
    chown -R "${APP_USER}:${APP_USER}" "${APP_HOME}" 2>/dev/null || true
    done_step "Code pulled${_pull_suffix}: $(git -C "${APP_HOME}" log --oneline -1)"

    step "Python virtual environment"
    if [ "${SKIP_DEPS:-0}" != "1" ]; then
        if [ ! -f "${VENV_DIR}/bin/python" ]; then
            sudo -u "${APP_USER}" python3 -m venv "${VENV_DIR}"
        fi
        _pip_install --upgrade pip
        _pip_install -r "${APP_HOME}/requirements.txt"
    else
        echo -e "${WARN} Skipped (deps already present or --skip-deps)"
    fi
    done_step "Python dependencies installed"

    # 仅 production 需要域名
    if [ "${DEPLOY_TYPE}" = "production" ]; then
        prompt_domain
    fi

    step "Generate .env"
    generate_env force
    if [ "${DEPLOY_TYPE}" = "production" ]; then
        done_step ".env generated"
    else
        done_step ".env generated (DEPLOY_DOMAIN empty, DEPLOY_PROTOCOL=http)"
    fi

    # 审计 NEW-H1：与四脚本一致的 VeroGuard 完整性清单构建
    build_veroguard_manifest

    # Production gate: refuse to continue if DEBUG got enabled in .env
    assert_debug_disabled

    # 仅 production：DOMAIN 未配置时不启动 systemd / nginx
    if [ "${DEPLOY_TYPE}" = "production" ] && [ -z "${DOMAIN}" ]; then
        echo -e "${WARN} Domain not configured. System and nginx not started."
        echo -e "${INFO} After install, run:"
        echo -e "${INFO}   sudo bash deploy/${INSTALL_SCRIPT} configure-domain <your-domain>"
    else
        step "systemd services"
        write_systemd_services
        done_step "systemd services configured"

        if [ "${DEPLOY_TYPE}" = "production" ]; then
            step "Nginx"
        else
            step "Nginx (path routing)"
        fi
        write_nginx_config
        nginx -t && systemctl restart nginx
        done_step "Nginx configured"

        step "Start services"
        restart_services
        done_step "Services started"

        # Wait for backends to be ready before SSL cert (avoid 502 on HTTP challenge)
        _wait=0
        _max_wait=30
        while [ $_wait -lt $_max_wait ]; do
            if curl -s --max-time 2 http://127.0.0.1:8081/ > /dev/null 2>&1 \
               && curl -s --max-time 2 http://127.0.0.1:8083/ > /dev/null 2>&1; then
                echo -e "${OK} Backend services ready"
                break
            fi
            sleep 1
            _wait=$((_wait + 1))
        done
        if [ $_wait -ge $_max_wait ]; then
            echo -e "${WARN} Backends did not respond within ${_max_wait}s — SSL may fail"
        fi
    fi

    # HTTPS 证书自动签发（审计 Y-2）：仅 production + 域名已配置时启用
    _setup_ssl_cert

    step "Configure sudoers (one-click update permissions)"
    write_sudoers
    done_step "Sudoers configured"

    step "Database migration"
    if [ "${APPROVE_MIGRATE:-0}" = "1" ]; then
        sudo -u "${APP_USER}" bash -c "set -a; source ${APP_HOME}/.env; cd ${APP_HOME} && PYTHONPATH=${APP_HOME}:${APP_HOME}/auth-center ${VENV_DIR}/bin/python -c 'from models.database import init_db; init_db()'"
        done_step "Database migrated"
    else
        echo -e "${WARN} Skipped database migration (pass --approve-migrate to apply schema changes)"
        echo -e "${INFO} Services may fail to start if code references columns not yet in the DB"
    fi

    step "Seed data"
    # 审计 NEW-M1：凭据由 common.sh do_seed 统一生成并回显（此处不再用全局变量传递）
    do_seed
    done_step "Seed data injected"

    print_summary
}

# ── Incremental update：production 从 .env 读域名；.git 缺失按模式处理；self-update 用 ${INSTALL_SCRIPT} ──
do_update() {
    # ── Trap: write failure status on any early exit ──
    # /run/verorun/ is tmpfs managed by systemd RuntimeDirectory (verorun-admin.service).
    # Owned by APP_USER, no root-permission conflicts. Cleared on reboot (intended).
    local _status_file="/run/verorun/update_status.json"
    mkdir -p /run/verorun 2>/dev/null || true
    chown "${APP_USER}:${APP_USER}" /run/verorun 2>/dev/null || true
    trap 'echo "{\"status\":\"failed\",\"progress\":100,\"message\":\"Update failed\",\"error\":\"Script exited unexpectedly\"}" > '"${_status_file}" EXIT

    # Self-update tracking: md5 of currently-running ${INSTALL_SCRIPT}
    UPDATE_MD5=$(md5sum "${APP_HOME}/deploy/${INSTALL_SCRIPT}" 2>/dev/null | awk '{print $1}') || UPDATE_MD5=""

    # 仅 production 从 .env 读取域名；无域名模式保持 DOMAIN 为空（write_nginx_config 走 default_server）
    if [ "${DEPLOY_TYPE}" = "production" ]; then
        DOMAIN=$(grep "^DEPLOY_DOMAIN=" "${APP_HOME}/.env" 2>/dev/null | tail -1 | cut -d= -f2) || true
    fi

    local before_commit
    before_commit=$(git -C "${APP_HOME}" log --oneline -1 2>/dev/null || echo "unknown")

    step "Backup current version"
    mkdir -p "${APP_HOME}/.rollback"
    cp "${APP_HOME}/.env" "${APP_HOME}/.rollback/.env.bak" 2>/dev/null || true
    echo "${before_commit}" > "${APP_HOME}/.rollback/before_commit"
    done_step "Environment backed up"

    step "Restore locally modified files"
    # 审计 C-3：默认拒绝覆盖本地修改（防止销毁用户定制/热修复）；--force 时先备份 diff 再恢复
    if [ -d "${APP_HOME}/.git" ]; then
        if ! git -C "${APP_HOME}" diff --quiet; then
            if [ "${FORCE_UPDATE:-0}" != "1" ]; then
                echo -e "${FAIL} Local modifications detected — refusing to overwrite them."
                echo -e "${INFO} To review:  git -C ${APP_HOME} diff"
                echo -e "${INFO} To backup:  git -C ${APP_HOME} diff > ${APP_HOME}/.rollback/local-patch-$(date +%s).diff"
                echo -e "${INFO} Re-run with '--force' to auto-restore (a backup diff is saved first)."
                exit 1
            fi
            mkdir -p "${APP_HOME}/.rollback"
            git -C "${APP_HOME}" diff > "${APP_HOME}/.rollback/local-patch-$(date +%s).diff"
            echo -e "${WARN} Local modifications detected (backed up to .rollback/local-patch-*.diff), restoring to git version..."
            git -C "${APP_HOME}" diff --name-only -z | xargs -0 git -C "${APP_HOME}" checkout --
            done_step "Locally modified files restored (diff saved)"
        else
            done_step "No local modifications"
        fi
    else
        done_step "Skipped (no .git directory)"
    fi

    # Git 仓库自动解析（审计 Y-1）：HTTPS 直连不可达时自动切镜像；SSH 走 443
    _resolve_git_repo

    ensure_git_auth

    step "Pull latest code"
    if [ ! -d "${APP_HOME}/.git" ]; then
        if [ "${DEPLOY_TYPE}" = "production" ]; then
            echo -e "${WARN} .git missing — re-cloning repository"
            # 审计 H3 修复：复用交互式冲突处理，禁止直接 rm -rf
            resolve_directory_conflict "${APP_HOME}"
            _clone_with_timeout "${GIT_REPO}" "${APP_HOME}" "${GIT_BRANCH}"
        else
            # 审计 R4 L-A：错误消息使用 ${INSTALL_SCRIPT}，不再硬编码脚本名
            echo -e "${FAIL} .git missing — cannot update. Re-install with ${INSTALL_SCRIPT}."
            exit 1
        fi
    else
        git config --global --add safe.directory "${APP_HOME}" 2>/dev/null || true
        cd "${APP_HOME}"
        git remote set-url origin "${GIT_REPO}"
        export GIT_TERMINAL_PROMPT=0
        if ! timeout 60 git fetch origin "${GIT_BRANCH}" 2>&1; then
            echo -e "${FAIL} Git fetch failed or timed out (60s) — aborting"
            echo -e "${INFO} Check origin remote: git -C ${APP_HOME} remote -v"
            echo -e "${INFO} If it points to a mirror (ghfast.top/ghproxy), reset it:"
            echo -e "${INFO}   git -C ${APP_HOME} remote set-url origin ${GIT_REPO}"
            exit 1
        fi
        git merge "origin/${GIT_BRANCH}" --ff-only 2>/dev/null || {
            echo -e "${WARN} Fast-forward merge failed, falling back to reset"
            git reset --hard "origin/${GIT_BRANCH}" || {
                echo -e "${FAIL} Git reset failed."
                exit 1
            }
        }
    fi
    # 应用 sparse-checkout 白名单：老仓库立即移除 .github/CHANGELOG/docs 等非运行时文件
    if ! git -C "${APP_HOME}" sparse-checkout set ${SPARSE_DIRS} 2>/dev/null; then
        git -C "${APP_HOME}" sparse-checkout init --cone 2>/dev/null || true
        if ! git -C "${APP_HOME}" sparse-checkout set ${SPARSE_DIRS} 2>/dev/null; then
            echo -e "${WARN} sparse-checkout failed — working tree may include non-runtime files"
        fi
    fi
    # 审计 NEW-H2：仅 production 统一清理三个无域名脚本
    if [ "${DEPLOY_TYPE}" = "production" ]; then
        rm -f "${APP_HOME}/deploy/install-local.sh" "${APP_HOME}/deploy/install-code.sh" "${APP_HOME}/deploy/install-dev.sh"
    fi
    local after_commit
    after_commit=$(git log --oneline -1)
    done_step "Code updated: ${before_commit:0:7} -> ${after_commit:0:7}"

    # Self-update: if the entry script itself changed, re-run update with new version
    local script_md5
    script_md5=$(md5sum "${APP_HOME}/deploy/${INSTALL_SCRIPT}" | awk '{print $1}')
    if [ "${UPDATE_MD5}" != "${script_md5}" ]; then
        echo -e "${INFO} ${INSTALL_SCRIPT} updated, re-running with new version..."
        exec sudo APP_USER="${APP_USER}" APP_HOME="${APP_HOME}" VENV_DIR="${VENV_DIR}" REGION="${REGION}" FORCE_UPDATE="${FORCE_UPDATE:-0}" bash "${APP_HOME}/deploy/${INSTALL_SCRIPT}" update
        exit
    fi

    step "Update .env (fill missing keys)"
    update_env
    done_step ".env synced"

    # 审计 R3-M2：代码更新后重建 VeroGuard 完整性清单，避免基准过时触发误报
    build_veroguard_manifest

    # Production gate: refuse to continue if DEBUG got enabled in .env
    assert_debug_disabled

    step "Update Python dependencies"
    req_hash=$(md5sum "${APP_HOME}/requirements.txt" | awk '{print $1}')
    cached_hash=$(cat "${APP_HOME}/.requirements_hash" 2>/dev/null || echo "")
    if [ "${req_hash}" != "${cached_hash}" ]; then
        _pip_install -r "${APP_HOME}/requirements.txt"
        echo "${req_hash}" > "${APP_HOME}/.requirements_hash"
    else
        echo -e "${INFO} requirements.txt unchanged, skipping pip install"
    fi
    done_step "Dependencies updated"

    step "Update systemd services"
    chmod +x "${APP_HOME}/deploy/health_check.sh" 2>/dev/null || true
    write_systemd_services
    done_step "Systemd services updated"

    step "Update sudoers (one-click update permissions)"
    write_sudoers
    done_step "Sudoers updated"

    step "Update Nginx config"
    write_nginx_config
    nginx -t && systemctl restart nginx
    done_step "Nginx config updated"

    step "Pre-flight check"
    # 验证数据库可连接（直接 psycopg2 连接，不依赖 plugins 包）
    if ! sudo -u "${APP_USER}" bash -c "set -a; source ${APP_HOME}/.env; ${VENV_DIR}/bin/python -c \"
import os, psycopg2
conn = psycopg2.connect(
    host=os.getenv('PG_HOST', 'localhost'),
    port=os.getenv('PG_PORT', '5432'),
    dbname=os.getenv('PG_DB', 'appdb'),
    user=os.getenv('PG_USER', 'app'),
    password=os.getenv('PG_PASSWORD', ''),
)
conn.close()
print('DB OK')
\""; then
        echo -e "${FAIL} Database not accessible — aborting update"
        exit 1
    fi
    # 验证 Python 语法无致命错误
    if ! sudo -u "${APP_USER}" bash -c "${VENV_DIR}/bin/python -m py_compile ${APP_HOME}/admin/app.py"; then
        echo -e "${FAIL} Syntax error in new code — aborting update"
        exit 1
    fi
    done_step "Pre-flight passed"

    step "Restart services"
    restart_services
    done_step "Services restarted"

    step "Health check"
    health_check

    # ── Write final update status for admin UI polling ──
    trap - EXIT  # Clear the failure trap before writing success
    local _status_file="/run/verorun/update_status.json"
    mkdir -p /run/verorun 2>/dev/null || true
    chown "${APP_USER}:${APP_USER}" /run/verorun 2>/dev/null || true
    if [ "${UPDATE_FAILED:-0}" -eq 0 ]; then
        echo '{"status":"success","progress":100,"message":"Update completed successfully","error":null}' > "${_status_file}"
    else
        echo '{"status":"failed","progress":100,"message":"Update completed with errors","error":"Some services are unhealthy"}' > "${_status_file}"
    fi
}

# ── Summary：按 DEPLOY_TYPE 条件渲染 ──
print_summary() {
    local PUBLIC_IP
    case "${DEPLOY_TYPE}" in
        production)
            PUBLIC_IP=$(curl -s --connect-timeout 5 --max-time 10 ifconfig.me 2>/dev/null || echo "unknown")

            echo ""
            echo "  ╔══════════════════════════════════════════════════════════════╗"
            echo "  ║              Deployment Complete!                             ║"
            if [ -n "${DOMAIN}" ]; then
            echo "  ╠══════════════════════════════════════════════════════════════╣"
            echo "  ║  Main site:  https://${DOMAIN}                                 ║"
            echo "  ║  Platform:   https://platform.${DOMAIN}                        ║"
            echo "  ║  Admin:      https://agent.${DOMAIN}/admin/                    ║"
            fi
            if [ "${APPROVE_MIGRATE:-0}" != "1" ]; then
            echo "  ╠══════════════════════════════════════════════════════════════╣"
            echo "  ║  WARNING: Admin account NOT created — admin panel inaccessible"
            echo "  ║  To fix: sudo bash deploy/${INSTALL_SCRIPT} seed                      ║"
            fi
            # 审计 R3-M3：与 install-local.sh 一致，展示管理员凭据
            if [ "${APPROVE_MIGRATE:-0}" = "1" ]; then
            echo "  ╠══════════════════════════════════════════════════════════════╣"
            echo "  ║  Admin login: ${VR_ADMIN_USERNAME:-administrator} / ***HIDDEN***"
            fi
            echo "  ╠══════════════════════════════════════════════════════════════╣"
            echo "  ║  Useful commands:                                            ║"
            echo "  ║    systemctl status verorun-{main,auth,admin,guardian}       ║"
            echo "  ║    journalctl -u verorun-guardian -f                         ║"
            echo "  ║    bash deploy/${INSTALL_SCRIPT} update                              ║"
            echo "  ║    bash deploy/${INSTALL_SCRIPT} rollback                            ║"
            echo "  ╚══════════════════════════════════════════════════════════════╝"
            echo ""
            ;;
        lan)
            echo ""
            echo "  ╔══════════════════════════════════════════════════════════════╗"
            echo "  ║         No-domain / LAN Deployment Complete!                  ║"
            echo "  ╠══════════════════════════════════════════════════════════════╣"
            echo "  ║  Main site:   http://localhost/                               ║"
            echo "  ║  Admin:       http://localhost/admin/                         ║"
            echo "  ║  Console:     http://localhost/auth/                          ║"
            PUBLIC_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
            if [ -n "${PUBLIC_IP}" ]; then
            echo "  ║  LAN access:  http://${PUBLIC_IP}/  (same paths)              ║"
            fi
            echo "  ╠══════════════════════════════════════════════════════════════╣"
            echo "  ║  Useful commands:                                            ║"
            echo "  ║    systemctl status verorun-{main,auth,admin,guardian}       ║"
            echo "  ║    bash deploy/${INSTALL_SCRIPT} update                        ║"
            echo "  ╠══════════════════════════════════════════════════════════════╣"
            echo "  ║  AI API keys are empty by default — set real values in:      ║"
            echo "  ║    ${APP_HOME}/.env  (DASHSCOPE_TEXT_KEY / OPENAI_API_KEY /   ║"
            echo "  ║    DEEPSEEK_API_KEY) before enabling AI features             ║"
            if [ "${APPROVE_MIGRATE:-0}" = "1" ]; then
            echo "  ╠══════════════════════════════════════════════════════════════╣"
            echo "  ║  Admin login: ${VR_ADMIN_USERNAME:-administrator} / ***HIDDEN***"
            fi
            echo "  ╚══════════════════════════════════════════════════════════════╝"
            echo ""
            ;;
        code)
            PUBLIC_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
            echo ""
            echo "  ╔══════════════════════════════════════════════════════════════╗"
            echo "  ║      Team Intranet Deployment Complete (Full Plugins)!        ║"
            echo "  ╠══════════════════════════════════════════════════════════════╣"
            echo "  ║  Main site:   http://localhost/                               ║"
            echo "  ║  Admin:       http://localhost/admin/                         ║"
            echo "  ║  Console:     http://localhost/auth/                          ║"
            if [ -n "${PUBLIC_IP}" ]; then
            echo "  ║  LAN access:  http://${PUBLIC_IP}/  (same paths)              ║"
            fi
            echo "  ║  Plugins:     $(ls -d ${APP_HOME}/plugins/*/ 2>/dev/null | wc -l) directories installed                    ║"
            echo "  ║  Code size:   $(du -sh ${APP_HOME} 2>/dev/null | cut -f1)                              ║"
            # 审计 R3-M3：与 install-local.sh 一致，展示管理员凭据
            if [ "${APPROVE_MIGRATE:-0}" = "1" ]; then
            echo "  ╠══════════════════════════════════════════════════════════════╣"
            echo "  ║  Admin login: ${VR_ADMIN_USERNAME:-administrator} / ***HIDDEN***"
            fi
            echo "  ╠══════════════════════════════════════════════════════════════╣"
            echo "  ║  Useful commands:                                            ║"
            echo "  ║    systemctl status verorun-{main,auth,admin,guardian}       ║"
            echo "  ║    bash deploy/${INSTALL_SCRIPT} update                         ║"
            echo "  ╚══════════════════════════════════════════════════════════════╝"
            echo ""
            ;;
        dev)
            echo ""
            echo "  ╔══════════════════════════════════════════════════════════════╗"
            echo "  ║         Developer Deployment Complete!                        ║"
            echo "  ╠══════════════════════════════════════════════════════════════╣"
            echo "  ║  Main site:   http://localhost/                               ║"
            echo "  ║  Admin:       http://localhost/admin/                         ║"
            echo "  ║  Console:     http://localhost/auth/                          ║"
            PUBLIC_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
            if [ -n "${PUBLIC_IP}" ]; then
            echo "  ║  LAN access:  http://${PUBLIC_IP}/  (same paths)              ║"
            fi
            echo "  ║  Plugins:     NOT installed (install via Admin panel)          ║"
            # 审计 R3-M3：与 install-local.sh 一致，展示管理员凭据
            if [ "${APPROVE_MIGRATE:-0}" = "1" ]; then
            echo "  ╠══════════════════════════════════════════════════════════════╣"
            echo "  ║  Admin login: ${VR_ADMIN_USERNAME:-administrator} / ***HIDDEN***"
            fi
            echo "  ╠══════════════════════════════════════════════════════════════╣"
            echo "  ║  Useful commands:                                            ║"
            echo "  ║    systemctl status verorun-{main,auth,admin,guardian}       ║"
            echo "  ║    bash deploy/${INSTALL_SCRIPT} update                          ║"
            echo "  ╚══════════════════════════════════════════════════════════════╝"
            echo ""
            ;;
        *)
            echo -e "${WARN} print_summary: unknown DEPLOY_TYPE '${DEPLOY_TYPE}'"
            ;;
    esac
}
