#!/usr/bin/env python3
"""Upload a file to remote server via plink stdin, preserving UTF-8."""
import subprocess
import sys

local_path = sys.argv[1]
remote_path = sys.argv[2]

with open(local_path, 'rb') as f:
    data = f.read()

cmd = ['plink', '-batch', '-ssh', 'easykai@***REMOVED***', '-pw', '***REMOVED***',
       f'cat > {remote_path}']

proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
stdout, stderr = proc.communicate(data)

if proc.returncode != 0:
    print(f'Upload failed: {stderr.decode()}')
    sys.exit(1)
print(f'Uploaded {local_path} ({len(data)} bytes) -> {remote_path}')
