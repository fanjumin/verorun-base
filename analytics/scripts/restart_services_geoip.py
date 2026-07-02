#!/usr/bin/env python3
"""Restart all Flask services so they reload GeoIP"""
import paramiko

HOST = '100.124.0.103'
USER = 'easykai'
PASS = '***REMOVED***'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, look_for_keys=False, allow_agent=False)

# 1. Clear __pycache__ first
print("=== 清理 __pycache__ ===")
stdin, stdout, stderr = ssh.exec_command(
    'find /path/to/deployment -name __pycache__ -exec rm -rf {} + 2>/dev/null; echo "done"'
)
print(stdout.read().decode().strip())

# 2. Restart admin (tmux admin-8084)
print("\n=== 重启 admin (tmux admin-8084) ===")
stdin, stdout, stderr = ssh.exec_command(
    'tmux send-keys -t admin-8084 C-c; sleep 1; '
    'tmux send-keys -t admin-8084 "python3 -B app.py 8084" Enter; sleep 2; '
    'curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:8084/'
)
print(stdout.read().decode().strip())

# 3. Restart platform (tmux platform)
print("\n=== 重启 platform (tmux platform) ===")
stdin, stdout, stderr = ssh.exec_command(
    'tmux send-keys -t platform C-c; sleep 1; '
    'tmux send-keys -t platform "python3 -B app.py" Enter; sleep 2; '
    'curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:8083/'
)
print(stdout.read().decode().strip())

# 4. Restart community (tmux community)
print("\n=== 重启 community (tmux community) ===")
stdin, stdout, stderr = ssh.exec_command(
    'tmux send-keys -t community C-c; sleep 1; '
    'tmux send-keys -t community "python3 -B app.py" Enter; sleep 2; '
    'curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:8082/'
)
print(stdout.read().decode().strip())

# 5. Restart trademind (systemd)
print("\n=== 重启 trademind (systemd trademind-api.service) ===")
stdin, stdout, stderr = ssh.exec_command('sudo systemctl restart trademind-api.service 2>&1')
stdin, stdout, stderr = ssh.exec_command(
    'sleep 3; curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:8081/'
)
print(stdout.read().decode().strip())

# 6. Resart analytics processor
print("\n=== 重启 analytics processor (tmux) ===")
stdin, stdout, stderr = ssh.exec_command(
    'tmux send-keys -t analytics-processor C-c; sleep 1; '
    'tmux send-keys -t analytics-processor "python3 -B -m analytics.cli daemon 60" Enter; sleep 1; '
    'tmux capture-pane -t analytics-processor -p -S -5'
)
print(stdout.read().decode().strip())

# Wait a bit then verify geoip loaded
import time
time.sleep(4)
print("\n=== 验证 GeoIP 状态 ===")
stdin, stdout, stderr = ssh.exec_command(
    'cd /path/to/deployment && python3 -B -c \'from analytics.geoip import init_geoip, _find_db; print("DB:",_find_db()); init_geoip()\' 2>&1'
)
print(stdout.read().decode().strip())

ssh.close()
