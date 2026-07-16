#!/usr/bin/env python3
"""Get admin log via SSH with proper handling."""
import paramiko, time

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('***REMOVED***', username='easykai', password='***REMOVED***', timeout=15)

# Read admin log to see full error
stdin, stdout, stderr = c.exec_command("cat /tmp/admin_8084.log")
time.sleep(3)
full_log = stdout.read().decode(errors='replace')
lines = full_log.split('\n')
print(f"Total lines: {len(lines)}")
# Show last 30 lines
print('\n'.join(lines[-30:]))

c.close()
