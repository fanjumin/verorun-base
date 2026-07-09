#!/bin/bash
# 测试 Health Guardian 的自动恢复能力
set -e

echo "=== 测试 1: 基础健康检查 ==="
echo -n "health endpoint: "
curl -s http://127.0.0.1:8085/health
echo ""

echo -n "status api: "
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8085/admin/health/api/status
echo " (401 是正常)"

echo ""
echo "=== 测试 2: 模拟故障 - 关闭 health.service ==="
echo ***REMOVED*** | sudo -S systemctl stop health.service
echo "health.service 已停止"
sleep 5

echo -n "验证 8085 已不可用: "
curl -s --connect-timeout 2 http://127.0.0.1:8085/health || echo "timeout (预期)"

echo ""
echo "=== 测试 3: 模拟故障 - 恢复 health.service ==="
echo ***REMOVED*** | sudo -S systemctl start health.service
sleep 3

echo -n "验证 8085 已恢复: "
curl -s http://127.0.0.1:8085/health

echo ""
echo "=== 测试 4: 检查快照 timer ==="
echo ***REMOVED*** | sudo -S systemctl is-active health-snapshot.timer

echo ""
echo "=== 测试完成 ==="
