#!/usr/bin/env python3
"""
Deployment script: sync local files to remote server via SFTP (paramiko).

Source : F:\Sites\VeroRun
Target : easykai@***REMOVED***:/home/easykai/easykai-workspace/easykai.cn/

Usage:
    python scripts/deploy_sftp.py              # full sync + restart
    python scripts/deploy_sftp.py --dry-run     # preview only, no upload
    python scripts/deploy_sftp.py --no-restart  # upload only, skip restart

NOTE on "module 'platform' has no attribute 'architecture'":
    If you see this error, it's because the local file
    F:\Sites\VeroRun\platform\__init__.py (empty) shadows the stdlib
    `platform` module. Delete that empty file, or ensure your working
    directory does not include the project root when running scripts
    that need stdlib platform.
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

LOCAL_ROOT = r'F:\Sites\VeroRun'
REMOTE_ROOT = '/home/easykai/easykai-workspace/easykai.cn/'

# Directories to skip entirely (relative names, not paths)
EXCLUDE_DIRS = {
    '.git', '__pycache__', 'tmp', 'node_modules', '.env',
    'VeroRun', '__MACOSX', '.idea', '.vscode', 'venv',
}

# File patterns to skip (exact filenames or extension checks)
EXCLUDE_FILES = {
    '.DS_Store', 'Thumbs.db',
}

EXCLUDE_EXTENSIONS = {'.pyc', '.pyo'}

# Remote command to restart services
RESTART_CMD = 'supervisorctl restart all'

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def should_skip(rel_path: str) -> bool:
    """Check whether a relative path should be excluded."""
    parts = rel_path.replace(os.sep, '/').split('/')
    # Skip if any path component is an excluded directory
    if any(p in EXCLUDE_DIRS for p in parts):
        return True
    # File-level exclusions
    fname = parts[-1]
    if fname in EXCLUDE_FILES:
        return True
    ext = os.path.splitext(fname)[1].lower()
    if ext in EXCLUDE_EXTENSIONS:
        return True
    return False


def ensure_remote_dir(sftp, remote_dir: str):
    """Recursively create remote directories if they don't exist."""
    dirs = remote_dir.rstrip('/').split('/')
    cur = ''
    for d in dirs:
        cur += '/' + d
        try:
            sftp.stat(cur)
        except FileNotFoundError:
            sftp.mkdir(cur, mode=0o755)


def format_size(n: int) -> str:
    """Human-readable file size."""
    for unit in ('B', 'KB', 'MB', 'GB'):
        if n < 1024:
            return f'{n:.1f} {unit}'
        n /= 1024
    return f'{n:.1f} TB'


def colored(text: str, code: int) -> str:
    """Simple terminal colour helper."""
    return f'\033[{code}m{text}\033[0m'


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def collect_files(dry_run: bool = False):
    """Walk local root and return list of (local_path, relative_path)."""
    files = []
    for dirpath, dirnames, filenames in os.walk(LOCAL_ROOT):
        # Prune excluded directories in-place so os.walk skips them
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]

        for fname in filenames:
            local_path = os.path.join(dirpath, fname)
            rel_path = os.path.relpath(local_path, LOCAL_ROOT)
            if should_skip(rel_path):
                continue
            files.append((local_path, rel_path.replace(os.sep, '/')))

    return files


def do_sync(sftp, files, dry_run: bool = False):
    """Upload all files via SFTP, creating remote directories as needed."""
    total = len(files)
    ok = 0
    errors = []
    total_bytes = 0

    print(f'\n{"─" * 60}')
    print(f'  Files to sync: {total}')
    print(f'{"─" * 60}\n')

    for idx, (local_path, rel_path) in enumerate(files, 1):
        local_size = os.path.getsize(local_path)
        remote_path = os.path.join(REMOTE_ROOT, rel_path).replace(os.sep, '/')
        remote_dir = os.path.dirname(remote_path)

        prefix = f'[{idx:>{len(str(total))}}/{total}]'
        size_str = format_size(local_size).rjust(9)
        line = f'  {prefix} {size_str}  {rel_path}'

        if dry_run:
            print(line)
            total_bytes += local_size
            ok += 1
            continue

        # Upload
        try:
            ensure_remote_dir(sftp, remote_dir)

            # Check remote mtime for a cheap skip
            try:
                attrs = sftp.stat(remote_path)
                if attrs.st_size == local_size:
                    local_mtime = os.path.getmtime(local_path)
                    # SFTP has second granularity, so floor to int
                    if int(local_mtime) <= attrs.st_mtime:
                        print(f'  {prefix} {"─":>9}  {rel_path}  (unchanged, skip)')
                        ok += 1
                        continue
            except FileNotFoundError:
                pass

            sftp.put(local_path, remote_path)
            total_bytes += local_size
            ok += 1
            print(colored(line, 32))  # green
        except Exception as e:
            errors.append((rel_path, str(e)))
            print(colored(f'  {prefix} {"ERR":>9}  {rel_path}  → {e}', 31))  # red

    # Summary
    print(f'\n{"─" * 60}')
    print(f'  Synced: {ok} / {total} files, {format_size(total_bytes)}')
    if errors:
        print(f'  Errors: {len(errors)}')
        for f, e in errors[:10]:
            print(f'    ✗ {f}: {e}')
    print(f'{"─" * 60}\n')
    return ok == total


def do_restart(ssh):
    """SSH in to restart services."""
    print('  Restarting services via supervisorctl...')
    stdin, stdout, stderr = ssh.exec_command(RESTART_CMD)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()

    if out:
        for line in out.split('\n'):
            print(f'    {line}')
    if err:
        for line in err.split('\n'):
            print(f'    {colored(line, 33)}')  # yellow

    if exit_code == 0:
        print(colored('  ✓ Services restarted successfully.', 32))
    else:
        print(colored(f'  ✗ supervisorctl exited with code {exit_code}', 31))
    return exit_code == 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    dry_run = '--dry-run' in sys.argv
    skip_restart = '--no-restart' in sys.argv

    if dry_run:
        print(colored('  *** DRY RUN MODE — no files will be uploaded ***\n', 33))

    start = datetime.now()

    # 1. Collect files
    print('  Scanning local files...')
    files = collect_files(dry_run)
    if not files:
        print('  No files to sync.')
        return

    if dry_run:
        do_sync(None, files, dry_run=True)
        return

    # 2. Connect
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

    # 3. Sync
    success = False
    try:
        success = do_sync(sftp, files)
    finally:
        sftp.close()

    # 4. Restart
    if success and not skip_restart:
        if not do_restart(ssh):
            print(colored('  ⚠  Sync succeeded but restart had issues.', 33))
    elif success and skip_restart:
        print(colored('  ⚠  --no-restart: services were NOT restarted.', 33))
    elif not success:
        print(colored('  ✗ Sync had errors — not restarting services.', 31))

    ssh.close()

    elapsed = datetime.now() - start
    total_sec = int(elapsed.total_seconds())
    print(f'\n  Done in {total_sec}s.')

    if not success:
        sys.exit(1)


if __name__ == '__main__':
    main()
