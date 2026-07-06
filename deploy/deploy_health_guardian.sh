#!/bin/bash
# ==============================================================
# deploy_health_guardian.sh — Health Guardian 完整部署脚本
# ==============================================================
# 用途: 将本地 health_guardian.py + systemd 配置部署到服务器
# 用法:
#   bash deploy/deploy_health_guardian.sh [--dry-run]
# ==============================================================
set -euo pipefail

SSH_HOST="easykai@***REMOVED***"
PROJECT_DIR="/home/easykai/easykai-workspace/easykai.cn"
LOCAL_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
    echo "[DRY RUN] 仅模拟，不会实际执行"
fi

echo "=========================================="
echo " Health Guardian 部署脚本"
echo "=========================================="
echo "目标服务器: ${SSH_HOST}"
echo "项目目录:   ${PROJECT_DIR}"
echo ""

# ─── 1. 创建远程目录 ───
echo "[1/6] 创建远程目录..."
$DRY_RUN || ssh "${SSH_HOST}" "mkdir -p ${PROJECT_DIR}/health_service"

# ─── 2. 同步 health_guardian.py ───
echo "[2/6] 同步 health_guardian.py..."
$DRY_RUN || scp "${LOCAL_ROOT}/health_guardian.py" "${SSH_HOST}:${PROJECT_DIR}/health_guardian.py"

# ─── 3. 同步 health_service/ ───
echo "[3/6] 同步 health_service/ 目录..."
$DRY_RUN || scp -r "${LOCAL_ROOT}/health_service/" "${SSH_HOST}:${PROJECT_DIR}/health_service/"

# ─── 4. 部署环境变量文件 ───
echo "[4/6] 部署环境变量文件..."
$DRY_RUN || {
    scp "${LOCAL_ROOT}/deploy/health-guardian.env" "${SSH_HOST}:/tmp/health-guardian.env"
    ssh "${SSH_HOST}" "sudo mv /tmp/health-guardian.env /etc/default/health-guardian"
}

# ─── 5. 注册 systemd 服务 ───
echo "[5/6] 注册 systemd 服务..."
$DRY_RUN || {
    for unit in health-guardian.service health.service health-snapshot.service health-snapshot.timer; do
        scp "${LOCAL_ROOT}/deploy/${unit}" "${SSH_HOST}:/tmp/${unit}"
        ssh "${SSH_HOST}" "sudo mv /tmp/${unit} /etc/systemd/system/${unit}"
    done
    ssh "${SSH_HOST}" "sudo systemctl daemon-reload"
    ssh "${SSH_HOST}" "sudo systemctl enable health.service health-guardian.service health-snapshot.timer"
}

# ─── 6. 启动服务 ───
echo "[6/6] 启动服务..."
$DRY_RUN || {
    ssh "${SSH_HOST}" "sudo systemctl restart health.service"
    echo "  等待 3 秒让 health service 就绪..."
    sleep 3
    ssh "${SSH_HOST}" "sudo systemctl restart health-guardian.service"
    ssh "${SSH_HOST}" "sudo systemctl start health-snapshot.timer"
}

# ─── 验证 ───
echo ""
echo "=========================================="
echo " 验证"
echo "=========================================="
if $DRY_RUN; then
    echo "以下命令将用于验证部署："
    echo "  curl http://127.0.0.1:8085/health"
    echo "  curl http://127.0.0.1:8085/admin/health/api/status"
    echo "  systemctl status health-guardian"
    echo "  systemctl status health-snapshot.timer"
else
    echo "执行验证（在服务器上）..."
    ssh "${SSH_HOST}" "curl -s http://127.0.0.1:8085/health" || echo "  ⚠️ health-service 未响应"
    ssh "${SSH_HOST}" "sudo systemctl is-active health-guardian" || echo "  ⚠️ health-guardian 未运行"
    ssh "${SSH_HOST}" "sudo systemctl is-active health-snapshot.timer" || echo "  ⚠️ snapshot timer 未运行"
fi

echo ""
echo "部署完成。"
echo ""
echo "手动检查命令："
echo "  ssh ${SSH_HOST}"
echo "  curl http://127.0.0.1:8085/health"
echo "  sudo journalctl -u health-guardian -n 50 --no-pager"
