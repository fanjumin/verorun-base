#!/bin/bash
PW=***REMOVED***
echo "=== Guardian 日志文件 ==="
echo $PW | sudo -S ls -la /var/log/health-guardian.log 2>&1
echo ""
echo "=== Guardian 日志内容 ==="
echo $PW | sudo -S cat /var/log/health-guardian.log 2>&1 | tail -30
echo ""
echo "=== Guardian systemd 最近日志 ==="
echo $PW | sudo -S journalctl -u health-guardian --no-pager -n 20 2>&1
