#!/usr/bin/env python3
"""
Backup remote databases before deployment.

Connects to remote server via SSH/SFTP, creates a timestamped backup
of all .db files in the data/ directory, and downloads a local copy.

Usage:
    python scripts/backup_remote_db.py
"""

import os
import sys
from datetime import datetime

import paramiko

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
HOST = '***REMOVED***'
PORT = 22
USER = 'easykai'
PASS = '***REMOVED***'

REMOTE_DATA_DIR = '/home/easykai/easykai-workspace/easykai.cn/data/'
LOCAL_BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backups')

DB_EXTENSIONS = {'.db', '.db-wal', '.db-shm'}


def colored(text: str, code: int) -> str:
    return f'\033[{code}m{text}\033[0m'


def main():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    remote_backup_dir = f'/home/easykai/backups/data_{timestamp}/'
    local_backup_dir = os.path.join(LOCAL_BACKUP_DIR, f'data_{timestamp}')

    print('  Connecting to server...')
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(HOST, port=PORT, username=USER, password=PASS,
                    look_for_keys=False, allow_agent=False)
        sftp = ssh.open_sftp()
        print(colored(f'  ✓ Connected to {USER}@{HOST}:{PORT}\n', 32))
    except Exception as e:
        print(colored(f'  ✗ Connection failed: {e}', 31))
        sys.exit(1)

    # 1. Create remote backup directory
    print(f'  Creating remote backup: {remote_backup_dir}')
    try:
        ssh.exec_command(f'mkdir -p {remote_backup_dir}')
        print(colored('  ✓ Remote backup directory created', 32))
    except Exception as e:
        print(colored(f'  ✗ Failed to create remote backup dir: {e}', 31))
        sftp.close()
        ssh.close()
        sys.exit(1)

    # 2. List remote data/ directory
    print(f'\n  Listing remote {REMOTE_DATA_DIR}...')
    try:
        remote_files = sftp.listdir(REMOTE_DATA_DIR)
    except FileNotFoundError:
        print(f'  Remote data/ directory not found, creating...')
        sftp.mkdir(REMOTE_DATA_DIR, mode=0o755)
        remote_files = []

    db_files = []
    for fname in remote_files:
        ext = os.path.splitext(fname)[1].lower()
        if ext in DB_EXTENSIONS or fname.endswith('.db'):
            remote_path = os.path.join(REMOTE_DATA_DIR, fname).replace(os.sep, '/')
            try:
                attrs = sftp.stat(remote_path)
                size_mb = attrs.st_size / (1024 * 1024)
                db_files.append((fname, remote_path, attrs.st_size))
                print(f'    {fname:30s}  {size_mb:>8.1f} MB  {datetime.fromtimestamp(attrs.st_mtime).strftime("%Y-%m-%d %H:%M:%S")}')
            except Exception:
                pass

    if not db_files:
        print(colored('\n  No database files found on remote, safe to proceed.', 33))
    else:
        print(f'\n  Found {len(db_files)} database file(s), starting backup...')

        # 3. Copy to remote backup via SSH cp
        for fname, remote_path, size in db_files:
            dest = os.path.join(remote_backup_dir, fname).replace(os.sep, '/')
            print(f'    Copying {fname} to remote backup...')
            stdin, stdout, stderr = ssh.exec_command(f'cp {remote_path} {dest}')
            stdout.channel.recv_exit_status()
            print(colored(f'    ✓ {fname} backed up remotely', 32))

        # 4. Download to local backup
        os.makedirs(local_backup_dir, exist_ok=True)
        print(f'\n  Downloading to local backup: {local_backup_dir}')
        for fname, remote_path, size in db_files:
            local_path = os.path.join(local_backup_dir, fname)
            print(f'    Downloading {fname} ({size / 1024 / 1024:.1f} MB)...')
            try:
                sftp.get(remote_path, local_path)
                print(colored(f'    ✓ {fname} downloaded', 32))
            except Exception as e:
                print(colored(f'    ✗ {fname} download failed: {e}', 31))

        print(colored(f'\n  ✓ Remote backup: {remote_backup_dir}', 32))
        print(colored(f'  ✓ Local backup:  {local_backup_dir}', 32))

    sftp.close()
    ssh.close()
    print(colored('\n  Backup complete.', 32))


if __name__ == '__main__':
    main()
