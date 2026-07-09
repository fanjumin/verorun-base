#!/bin/bash
PW=***REMOVED***

echo "=== 测试 1: 当前状态 ==="
echo $PW | sudo -S systemctl is-active health.service
echo $PW | sudo -S systemctl is-active health-guardian.service

echo ""
echo "=== 测试 2: 停掉 health.service（模拟故障）==="
echo $PW | sudo -S systemctl stop health.service
echo "health.service 已停"
echo $PW | sudo -S systemctl is-active health.service

echo ""
echo "=== 测试 3: 验证 guardian 仍然存活 ==="
echo $PW | sudo -S systemctl is-active health-guardian.service
echo "（如果输出 active 则表示独立运行成功）"

echo ""
echo "=== 测试 4: 恢复 health.service ==="
echo $PW | sudo -S systemctl start health.service
sleep 2
echo $PW | sudo -S systemctl is-active health.service
echo $PW | sudo -S curl -s http://127.0.0.1:8085/health

echo ""
echo "=== 测试 5: 最近 guardian 日志 ==="
echo $PW | sudo -S cat /var/log/health-guardian.log 2>/dev/null | tail -5

echo ""
echo "=== 测试完成 ==="
