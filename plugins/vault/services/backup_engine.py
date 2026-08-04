#!/usr/bin/env python3
"""
Vault Backup Engine — Full / Incremental / Differential backup entry point.

Supports:
  - Full backup: pg_dump + tar.gz of database and files
  - Incremental backup: WAL archive collection since last backup
  - Differential backup: changes since last full backup
  - Selective backup: specific tables, plugins, directories
"""

import os
import subprocess
import tarfile
import hashlib
import shutil
from datetime import datetime
from typing import Optional, Dict, List

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')
BACKUP_DIR = os.path.join(BASE_DIR, 'data', 'vault')


class BackupEngine:
    """Unified backup engine supporting full, incremental, and differential modes."""

    def __init__(self, backup_root: str = None):
        self.backup_root = backup_root or BACKUP_DIR
        os.makedirs(self.backup_root, exist_ok=True)

    def create_backup(self, backup_type: str = 'full',
                      base_label: str = None,
                      scope: Dict = None) -> Dict:
        """
        Execute a backup.

        Args:
            backup_type: 'full' | 'incremental' | 'differential'
            base_label: base backup label for incremental/differential
            scope: selective backup scope, e.g. {'tables': ['users','orders'], 'plugins': ['vault']}

        Returns:
            {'label': str, 'archive': str, 'size_mb': float, 'success': bool, 'error': str|None}
        """
        label = f"vault_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        work_dir = os.path.join(self.backup_root, label)
        os.makedirs(work_dir, exist_ok=True)

        errors = []
        files = []

        # ── 1. Database backup ──
        if not scope or scope.get('include_db', True):
            if backup_type == 'full':
                db_result = self._dump_full(work_dir, label, scope)
            elif backup_type == 'incremental':
                db_result = self._dump_incremental(work_dir, label, base_label, scope)
            else:
                db_result = self._dump_differential(work_dir, label, base_label, scope)
            if db_result:
                files.append(db_result)
            else:
                errors.append('database dump failed')

        # ── 2. File archive ──
        if not scope or scope.get('include_files', True):
            file_result = self._archive_files(work_dir, label, scope)
            if file_result:
                files.append(file_result)
            else:
                errors.append('file archive failed')

        # ── 3. Package + checksum ──
        final_archive = os.path.join(self.backup_root, f'{label}.tar.gz')
        try:
            with tarfile.open(final_archive, 'w:gz') as tar:
                tar.add(work_dir, arcname=label)
            shutil.rmtree(work_dir, ignore_errors=True)

            size_mb = os.path.getsize(final_archive) / (1024 * 1024)
            sha256 = self._compute_sha256(final_archive)

            return {
                'label': label,
                'archive': final_archive,
                'backup_type': backup_type,
                'base_label': base_label,
                'size_mb': round(size_mb, 1),
                'checksum_sha256': sha256,
                'files': files,
                'success': len(errors) == 0,
                'error': '; '.join(errors) if errors else None,
            }
        except Exception as e:
            return {
                'label': label, 'archive': None, 'backup_type': backup_type,
                'success': False, 'error': f'Archive creation failed: {e}',
            }

    # ── Full backup ──
    def _dump_full(self, work_dir: str, label: str, scope: Dict) -> Optional[Dict]:
        """pg_dump complete database export."""
        env = self._get_pg_env()
        out_file = os.path.join(work_dir, f'{label}_db.sql')
        tables = scope.get('tables') if scope else None
        try:
            env_override = os.environ.copy()
            env_override['PGPASSWORD'] = env.get('PG_PASSWORD', '')
            cmd = [
                'pg_dump', '-h', env.get('PG_HOST', 'localhost'),
                '-p', env.get('PG_PORT', '5432'),
                '-U', env.get('PG_USER', 'verorun'),
                '-d', env.get('PG_DB', 'verorun'),
                '--no-owner', '--no-acl', '-f', out_file,
            ]
            if tables:
                for t in tables:
                    cmd.extend(['-t', t])
            proc = subprocess.run(cmd, env=env_override, capture_output=True,
                                  text=True, timeout=600)
            if proc.returncode != 0:
                print(f'[Vault] pg_dump failed: {proc.stderr.strip()}')
                return None
            return {'type': 'database', 'path': out_file, 'name': os.path.basename(out_file)}
        except Exception as e:
            print(f'[Vault] pg_dump error: {e}')
            return None

    # ── Incremental backup (WAL-based) ──
    def _dump_incremental(self, work_dir: str, label: str,
                          base_label: str, scope: Dict) -> Optional[Dict]:
        """Collect WAL log files since last backup."""
        pg_env = self._get_pg_env()
        archive_dir = pg_env.get('WAL_ARCHIVE_DIR', '/var/lib/postgresql/wal_archive')
        try:
            base_time = self._get_backup_time(base_label) if base_label else 0
            wal_files = []
            if os.path.isdir(archive_dir):
                for f in sorted(os.listdir(archive_dir)):
                    fpath = os.path.join(archive_dir, f)
                    if os.path.isfile(fpath) and os.path.getmtime(fpath) >= base_time:
                        wal_files.append(fpath)
            if not wal_files:
                print('[Vault] No WAL files found since base backup')
                return {'type': 'wal', 'path': None, 'name': 'wal_empty', 'count': 0}

            wal_archive = os.path.join(work_dir, f'{label}_wal.tar.gz')
            with tarfile.open(wal_archive, 'w:gz') as tar:
                for wf in wal_files:
                    tar.add(wf, arcname=os.path.basename(wf))
            return {
                'type': 'wal', 'path': wal_archive,
                'name': os.path.basename(wal_archive), 'count': len(wal_files),
            }
        except Exception as e:
            print(f'[Vault] WAL backup error: {e}')
            return None

    # ── Differential backup ──
    def _dump_differential(self, work_dir: str, label: str,
                           base_label: str, scope: Dict) -> Optional[Dict]:
        """Changes since last full backup."""
        return self._dump_incremental(work_dir, label, base_label, scope)

    def _archive_files(self, work_dir: str, label: str, scope: Dict) -> Optional[Dict]:
        """Package user files (supports selective plugin/directory scope)."""
        out_file = os.path.join(work_dir, f'{label}_files.tar.gz')
        try:
            with tarfile.open(out_file, 'w:gz') as tar:
                plugins = scope.get('plugins') if scope else None
                dirs = scope.get('directories') if scope else None

                if not plugins and not dirs:
                    for root in ['admin/static', 'main_site/static', 'images']:
                        path = os.path.join(BASE_DIR, root)
                        if os.path.isdir(path):
                            tar.add(path, arcname=root)
                    self._add_plugin_data(tar, None)
                else:
                    if dirs:
                        for d in dirs:
                            path = os.path.join(BASE_DIR, d)
                            if os.path.isdir(path):
                                tar.add(path, arcname=d)
                    self._add_plugin_data(tar, plugins)

            return {'type': 'files', 'path': out_file, 'name': os.path.basename(out_file)}
        except Exception as e:
            print(f'[Vault] File archive error: {e}')
            return None

    def _add_plugin_data(self, tar: tarfile.TarFile, plugin_filter: List[str] = None):
        """Add plugin data/ directories to tar."""
        plugins_dir = os.path.join(BASE_DIR, 'plugins')
        if not os.path.isdir(plugins_dir):
            return
        for name in sorted(os.listdir(plugins_dir)):
            if name.startswith('_'):
                continue
            if plugin_filter and name not in plugin_filter:
                continue
            plugin_path = os.path.join(plugins_dir, name)
            if not os.path.isdir(plugin_path):
                continue
            data_path = os.path.join(plugin_path, 'data')
            if os.path.isdir(data_path):
                tar.add(data_path, arcname=f'plugins/{name}/data')
            json_path = os.path.join(plugin_path, 'plugin.json')
            if os.path.isfile(json_path):
                tar.add(json_path, arcname=f'plugins/{name}/plugin.json')

    def _get_pg_env(self) -> Dict[str, str]:
        """Read .env for PostgreSQL connection info."""
        env = {}
        env_path = os.path.join(BASE_DIR, '.env')
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        env[k.strip()] = v.strip().strip('"').strip("'")
        return env

    def _get_backup_time(self, label: str) -> float:
        """Get creation timestamp of a backup."""
        archive = os.path.join(self.backup_root, f'{label}.tar.gz')
        if os.path.isfile(archive):
            return os.path.getmtime(archive)
        return 0.0

    @staticmethod
    def _compute_sha256(file_path: str) -> str:
        sha = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha.update(chunk)
        return sha.hexdigest()


# ── Convenience factory functions ──
def create_full_backup(scope: Dict = None) -> Dict:
    return BackupEngine().create_backup('full', scope=scope)


def create_incremental_backup(base_label: str, scope: Dict = None) -> Dict:
    return BackupEngine().create_backup('incremental', base_label=base_label, scope=scope)
