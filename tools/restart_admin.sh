#!/bin/bash
# Kill all gunicorn processes on port 8084
pkill -f 'gunicorn.*8084'
sleep 2
# Start admin service
cd /home/easykai/easykai-workspace/easykai.cn/admin
nohup python3 -m gunicorn -w 2 -b 0.0.0.0:8084 app:app --timeout 60 --graceful-timeout 30 --log-level warning --access-logfile - --error-logfile - > /dev/null 2>&1 &
sleep 3
ps aux | grep 'gunicorn.*8084' | grep -v grep
