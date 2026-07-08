#!/usr/bin/env python3
"""Fix admin service: find venv, install deps, restart"""
import paramiko, os, time

HOST = '***REMOVED***'
USER = 'easykai'
PASS = '***REMOVED***'
ROOT = '/home/easykai/easykai-workspace/easykai.cn'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, look_for_keys=False, allow_agent=False)

# Find existing venv or pip env
cmds = [
    f'ls -d {ROOT}/venv/bin/python3 2>/dev/null || ls -d {ROOT}/.venv/bin/python3 2>/dev/null || echo NO_VENV',
    'which pip3 2>/dev/null',
    'python3 -m pip --version 2>/dev/null',
    f'find {ROOT} -name "activate" -path "*/bin/activate" 2>/dev/null | head -5',
    'pip3 list 2>/dev/null | grep -i flask | head -5 || echo NO_FLASK',
    'pip3 list 2>/dev/null | head -3 || echo NO_PIP',
    'which python3 2>/dev/null',
]
for c in cmds:
    stdin, stdout, stderr = ssh.exec_command(c)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    print(f'$ {c}')
    if out: print(f'  {out}')
    if err and 'No such file' not in err: print(f'  ERR: {err[:200]}')

ssh.close()
