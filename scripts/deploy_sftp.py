#!/usr/bin/env python3
"""
Deployment script: sync changed files to remote server via SFTP (paramiko).

Source : F:\Sites\VeroRun
Target : easykai@***REMOVED***:/home/easykai/easykai-workspace/easykai.cn/

Usage:
    python scripts/deploy_sftp.py                 # incremental — only files changed since last deploy
    python scripts/deploy_sftp.py --full          # full deploy — all git-tracked files
    python scripts/deploy_sftp.py --dry-run       # preview only, no upload
    python scripts/deploy_sftp.py --no-restart    # upload only, skip restart
"""

import os
import sys
import subprocess
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
DEPLOY_HASH_FILE = os.path.join(LOCAL_ROOT, '.trae', '.deploy-hash')

# Directories that should never be deployed to the server
EXCLUDE_DIRS = {
    'scripts',         # local deployment/dev tools only
    '.git', '__pycache__(', ')tmp', 'node_modules', '.env',
    '.trae', 'backups', '.kilo', 'venv',
    '__MACOSX', '.idea', '.vscode',
    'nginx-domains',
}

# Extensions that should never be deployed
EXCLUDE_EXTENSIONS = {'.pyc', '.pyo', '.db', '.wal', '.shm', '.log'}

# Services that run on the server
ALL_SERVICES = {'admin', 'auth-center', 'platform', 'health', 'health-guardian'}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_git(*args) -> str:
    return subprocess.check_output(['git'] + list(args), cwd=LOCAL_ROOT, text=True).strip()


def get_changed_files() -> list[tuple[str, str]]:
    """Get list of (status, rel_path) for files changed since last deploy."""
    if os.path.exists(DEPLOY_HASH_FILE):
        with open(DEPLOY_HASH_FILE) as f:
            last_sha = f.read().strip()
    else:
        last_sha = run_git('rev-parse', 'HEAD~1')

    current = run_git('rev-parse', 'HEAD')
    if last_sha == current:
        return []

    output = run_git('diff', '--name-status', '--no-renames', last_sha, 'HEAD')
    if not output:
        return []

    results = []
    for line in output.split('\n'):
        if not line:
            continue
        parts = line.split('\t')
        if len(parts) < 2:
            continue
        status, path = parts[0], parts[1]
        path = path.strip('"')
        if status in ('A', 'M', 'D'):
            results.append((status, path.replace('\\', '/')))
    # Warn about untracked files that won't be deployed
    untracked = run_git('ls-files', '--others', '--exclude-standard')
    if untracked:
        untracked_lines = [l for l in untracked.split('\n') if l]
        if untracked_lines:
            print(colored(f'  WARNING: {len(untracked_lines)} untracked file(s) will NOT be deployed:', 33))
            for f in untracked_lines[:10]:
                print(colored(f'    {f}', 33))
            if len(untracked_lines) > 10:
                print(colored(f'    ... and {len(untracked_lines) - 10} more', 33))
    return results


def get_all_tracked() -> list[str]:
    """Get all git-tracked file paths (for --full mode)."""
    output = run_git('ls-tree', '-r', 'HEAD', '--name-only')
    return [p.replace('\\', '/') for p in output.split('\n') if p]


def save_deploy_hash():
    current = run_git('rev-parse', 'HEAD')
    os.makedirs(os.path.dirname(DEPLOY_HASH_FILE), exist_ok=True)
    with open(DEPLOY_HASH_FILE, 'w') as f:
        f.write(current)


def should_skip(rel_path: str) -> bool:
    """Check if a file should be excluded from deployment."""
    parts = rel_path.replace(os.sep, '/').split('/')
    # Skip if any path component is in EXCLUDE_DIRS
    for p in parts:
        if p in EXCLUDE_DIRS:
            return True
    # Skip excluded extensions
    ext = os.path.splitext(parts[-1])[1].lower()
    if ext in EXCLUDE_EXTENSIONS:
        return True
    return False


def ensure_remote_dir(sftp, remote_dir: str):
    dirs = remote_dir.rstrip('/').split('/')
    cur = ''
    for d in dirs:
        cur += '/' + d
        try:
            sftp.stat(cur)
        except FileNotFoundError:
            sftp.mkdir(cur, mode=0o755)


def format_size(n: int) -> str:
    for unit in ('B', 'KB', 'MB', 'GB'):
        if n < 1024:
            return f'{n:.1f} {unit}'
        n /= 1024
    return f'{n:.1f} TB'


def colored(text: str, code: int) -> str:
    return f'\033[{code}m{text}\033[0m'


def affected_services(changed_files: list) -> set:
    """Determine which services need restart based on changed file paths."""
    needs = set()
    for _, path in changed_files:
        if path.startswith('auth-center/'):
            needs.add('auth-center')
        if path.startswith('admin/') or path.startswith('admin_plugins/'):
            needs.add('admin')
        if path.startswith('platform/'):
            needs.add('platform')
        if path.startswith('site/'):
            needs.add('platform')
        if path.startswith('health_check/') or path.startswith('health_service/'):
            needs.add('health')
            needs.add('health-guardian')
        if path.startswith('captcha-service/') or path.startswith('captcha/'):
            needs.add('admin')
        if path.startswith('plugins/') or path.startswith('plugin_manager/'):
            needs.add('admin')
        if path.startswith('agent_matrix/') or path.startswith('orchestrator/'):
            needs.add('admin')
        if path.startswith('analytics/'):
            needs.add('admin')
        if path.startswith('i18n/'):
            needs.update({'admin', 'platform', 'auth-center'})
    return needs or ALL_SERVICES


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def do_sync(sftp, files, dry_run: bool = False, header: str = ''):
    """Upload changed files, delete removed files."""
    # Filter out excluded files
    effective = [(s, p) for s, p in files if s == 'D' or not should_skip(p)]
    skipped = len(files) - len(effective)
    n_upload = len([f for f in effective if f[0] in ('A', 'M')])
    n_delete = len([f for f in effective if f[0] == 'D'])

    print(f'\n{"─" * 60}')
    print(f'  {header}: {n_upload} changed + {n_delete} deleted')
    if skipped:
        print(f'  ({skipped} local-only files skipped)')
    print(f'{"─" * 60}\n')

    ok = 0
    errors = []
    total_bytes = 0
    total = len(effective)

    for idx, (status, rel_path) in enumerate(effective, 1):
        prefix = f'[{idx:>{len(str(total))}}/{total}]'

        # ── Deleted file → remove from remote ──
        if status == 'D':
            remote_path = os.path.join(REMOTE_ROOT, rel_path).replace(os.sep, '/')
            try:
                sftp.remove(remote_path)
                print(f'  {prefix} {"DEL":>9}  {rel_path}')
                ok += 1
            except FileNotFoundError:
                ok += 1
            except Exception as e:
                errors.append((rel_path, str(e)))
                print(colored(f'  {prefix} {"ERR":>9}  {rel_path}  → {e}', 31))
            continue

        # ── Added/Modified file → upload ──
        local_path = os.path.join(LOCAL_ROOT, rel_path)
        if not os.path.isfile(local_path):
            continue

        local_size = os.path.getsize(local_path)
        remote_path = os.path.join(REMOTE_ROOT, rel_path).replace(os.sep, '/')
        size_str = format_size(local_size).rjust(9)
        tag = ' [new]' if status == 'A' else ''

        if dry_run:
            print(f'  {prefix} {size_str}  {rel_path}{tag}')
            total_bytes += local_size
            ok += 1
            continue

        try:
            ensure_remote_dir(sftp, os.path.dirname(remote_path))
            sftp.put(local_path, remote_path)
            total_bytes += local_size
            ok += 1
            print(colored(f'  {prefix} {size_str}  {rel_path}{tag}', 32))
        except Exception as e:
            errors.append((rel_path, str(e)))
            print(colored(f'  {prefix} {"ERR":>9}  {rel_path}  → {e}', 31))

    print(f'\n{"─" * 60}')
    print(f'  Synced: {ok} / {total} files, {format_size(total_bytes)}')
    if errors:
        print(f'  Errors: {len(errors)}')
        for f, e in errors[:10]:
            print(f'    ✗ {f}: {e}')
    print(f'{"─" * 60}\n')
    return ok == total


def do_restart(ssh, services: set):
    """SSH in to restart specified services."""
    svc_list = ' '.join(sorted(services))
    print(f'  Restarting: {svc_list}')
    stdin, stdout, stderr = ssh.exec_command(
        f'echo {PASS} | sudo -S systemctl restart {svc_list} 2>&1'
    )
    exit_code = stdout.channel.recv_exit_status()
    err = stderr.read().decode().strip()

    if err:
        # Only show real errors (ignore password prompt echo)
        for line in err.split('\n'):
            if 'password' not in line.lower():
                print(f'    {colored(line, 33)}')

    if exit_code == 0:
        print(colored('  ✓ Services restarted successfully.', 32))
    else:
        print(colored(f'  ✗ Restart exited with code {exit_code}', 31))
        print(colored(f'    {err}', 33))
    return exit_code == 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    dry_run = '--dry-run' in sys.argv
    skip_restart = '--no-restart' in sys.argv
    full_mode = '--full' in sys.argv

    start = datetime.now()

    # 1. Collect files
    if full_mode:
        tracked = get_all_tracked()
        files = [(p, p) for p in tracked if not should_skip(p)]
        effective = [('M', p) for p in tracked if not should_skip(p)]
        n = len(effective)
        header = f'Full deploy — {n} tracked files'
    else:
        raw_files = get_changed_files()
        if not raw_files:
            print('  ✓ No changed files — nothing to deploy.')
            return
        effective = [(s, p) for s, p in raw_files if s == 'D' or not should_skip(p)]
        n_upload = len([f for f in effective if f[0] in ('A', 'M')])
        n_delete = len([f for f in effective if f[0] == 'D'])
        header = f'Incremental deploy — {n_upload} changed + {n_delete} deleted'
        files = raw_files

    if dry_run:
        print(colored('  *** DRY RUN MODE — no files will be uploaded ***\n', 33))
        do_sync(None, files, dry_run=True, header=header)
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
        success = do_sync(sftp, files, header=header)
    finally:
        sftp.close()

    # 4. Restart — only affected services
    if success and not skip_restart:
        affected = affected_services(files)
        do_restart(ssh, affected)
    elif success and skip_restart:
        print(colored('  ⚠ --no-restart: services were NOT restarted.', 33))
    elif not success:
        print(colored('  ✗ Sync had errors — not restarting services.', 31))

    ssh.close()

    # 5. Save deploy hash for next incremental run
    if success:
        save_deploy_hash()
        print('  ✓ Deploy hash updated.')

    elapsed = datetime.now() - start
    print(f'\n  Done in {int(elapsed.total_seconds())}s.')

    if not success:
        sys.exit(1)


if __name__ == '__main__':
    main()
