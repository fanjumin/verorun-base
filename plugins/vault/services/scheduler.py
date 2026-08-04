#!/usr/bin/env python3
"""
Vault Scheduler — Cron expression scheduling with backup window + pre/post hooks.

Manages backup schedules, computes next run times, and triggers backup jobs.
"""

import subprocess
import os
import glob as _glob
from datetime import datetime, time
from croniter import croniter
from plugins._base.db import get_raw_connection


class VaultScheduler:
    """Manage backup schedules, compute next run times, trigger backup jobs."""

    def __init__(self):
        self._engine = None  # lazy init

    def get_all_schedules(self) -> list:
        """Get all enabled schedules."""
        conn = get_raw_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, name, cron_expression, backup_type, retention_days,
                   retention_count, storage_targets, backup_window,
                   pre_hook, post_hook, enabled, last_run_at, next_run_at
            FROM vault_schedules
            WHERE enabled = TRUE
            ORDER BY next_run_at ASC
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [self._row_to_dict(row) for row in rows]

    def get_due_schedules(self) -> list:
        """Get all schedules that are due for execution."""
        now = datetime.utcnow()
        schedules = self.get_all_schedules()
        return [s for s in schedules
                if s['next_run_at'] and s['next_run_at'] <= now]

    def compute_next_run(self, cron_expr: str,
                         backup_window: dict = None) -> datetime:
        """Compute next execution time, respecting backup window."""
        base_time = datetime.utcnow()
        cron = croniter(cron_expr, base_time)
        next_run = cron.get_next(datetime)

        if backup_window:
            window_start = self._parse_time(backup_window.get('start', '00:00'))
            window_end = self._parse_time(backup_window.get('end', '23:59'))
            if not (window_start <= next_run.time() <= window_end):
                next_run = next_run.replace(
                    hour=window_start.hour,
                    minute=window_start.minute,
                    second=0, microsecond=0,
                )
                if next_run <= base_time:
                    next_run = cron.get_next(datetime)
                    next_run = next_run.replace(
                        hour=window_start.hour,
                        minute=window_start.minute,
                    )

        return next_run

    def execute_schedule(self, schedule: dict) -> dict:
        """Execute a schedule: run pre-hook → backup → post-hook → cleanup → update status."""
        from .backup_engine import BackupEngine

        result = {'schedule_id': schedule['id'], 'success': False}

        # 1. Pre-hook
        if schedule.get('pre_hook'):
            hook_result = self._run_hook(schedule['pre_hook'])
            if not hook_result['success']:
                result['error'] = f"pre_hook failed: {hook_result['error']}"
                return result

        # 2. Execute backup
        engine = BackupEngine()
        backup_result = engine.create_backup(backup_type=schedule['backup_type'])
        result['backup'] = backup_result

        # 3. Post-hook
        if schedule.get('post_hook') and backup_result['success']:
            self._run_hook(schedule['post_hook'])

        # 4. Cleanup expired backups
        if schedule.get('retention_days') or schedule.get('retention_count'):
            self._cleanup_old_backups(
                schedule['retention_days'],
                schedule['retention_count'],
            )

        # 5. Update schedule status
        self._update_schedule_status(schedule['id'])

        result['success'] = backup_result['success']
        return result

    def run_all_due(self) -> list:
        """Execute all due schedules, return result list."""
        due = self.get_due_schedules()
        results = []
        for sched in due:
            try:
                result = self.execute_schedule(sched)
                results.append(result)
            except Exception as e:
                results.append({
                    'schedule_id': sched['id'],
                    'success': False,
                    'error': str(e),
                })
        return results

    def _run_hook(self, hook_command: str) -> dict:
        try:
            proc = subprocess.run(
                hook_command, shell=True, capture_output=True,
                text=True, timeout=300,
            )
            return {
                'success': proc.returncode == 0,
                'stdout': proc.stdout.strip(),
                'stderr': proc.stderr.strip(),
                'error': proc.stderr.strip() if proc.returncode != 0 else None,
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _cleanup_old_backups(self, retention_days: int, retention_count: int):
        """Remove old backups based on retention policy."""
        if not retention_days and not retention_count:
            return
        backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  '..', '..', '..', 'data', 'vault')
        if not os.path.isdir(backup_dir):
            return
        archives = sorted(
            _glob.glob(os.path.join(backup_dir, 'vault_*.tar.gz')),
            key=os.path.getmtime, reverse=True,
        )
        cutoff_time = (datetime.utcnow().timestamp() - retention_days * 86400
                       if retention_days else 0)
        for archive in archives:
            if retention_count and archives.index(archive) < retention_count:
                continue
            if retention_days and os.path.getmtime(archive) >= cutoff_time:
                continue
            if retention_days or retention_count:
                try:
                    os.remove(archive)
                    print(f'[Vault] Cleaned up: {os.path.basename(archive)}')
                except OSError as e:
                    print(f'[Vault] Cleanup failed for {archive}: {e}')

    def _update_schedule_status(self, schedule_id: int):
        conn = get_raw_connection()
        cur = conn.cursor()
        now = datetime.utcnow()
        cron_expr = self._get_schedule_cron(schedule_id)
        next_run = self.compute_next_run(cron_expr) if cron_expr else None
        cur.execute("""
            UPDATE vault_schedules
            SET last_run_at = %s, next_run_at = %s
            WHERE id = %s
        """, (now, next_run, schedule_id))
        conn.commit()
        cur.close()
        conn.close()

    def _get_schedule_cron(self, schedule_id: int) -> str:
        conn = get_raw_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT cron_expression FROM vault_schedules WHERE id = %s",
            (schedule_id,),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        return row[0] if row else ''

    @staticmethod
    def _parse_time(time_str: str) -> time:
        parts = time_str.strip().split(':')
        return time(hour=int(parts[0]), minute=int(parts[1]))

    @staticmethod
    def _row_to_dict(row) -> dict:
        cols = ['id', 'name', 'cron_expression', 'backup_type', 'retention_days',
                'retention_count', 'storage_targets', 'backup_window',
                'pre_hook', 'post_hook', 'enabled', 'last_run_at', 'next_run_at']
        return dict(zip(cols, row))
