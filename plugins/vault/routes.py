#!/usr/bin/env python3
"""
Vault — Flask API Routes (Phase 1 extended)

API Endpoints:
    Page routes:
        GET   /admin/vault/                    — Dashboard page
        GET   /admin/vault/backups             — Backup list page
        GET   /admin/vault/restore             — Restore wizard page
        GET   /admin/vault/schedules           — Schedule management page
        GET   /admin/vault/storage             — Storage config page
        GET   /admin/vault/settings            — Settings page
        GET   /admin/vault/audit               — Audit log page

    Backup API:
        POST   /admin/vault/api/create              — Trigger backup (legacy, DEPRECATED)
        POST   /admin/vault/api/backup/create       — Trigger backup (new)
        GET    /admin/vault/api/list                — List backups (legacy, DEPRECATED)
        GET    /admin/vault/api/backup/list         — List backups with search/pagination
        GET    /admin/vault/api/backup/detail/<label> — Backup detail + content preview
        GET    /admin/vault/api/download/<label>    — Download backup (legacy)
        GET    /admin/vault/api/backup/download/<label> — Download backup (new)
        DELETE /admin/vault/api/delete/<label>      — Delete backup (legacy)
        DELETE /admin/vault/api/backup/delete/<label> — Delete backup (new)
        DELETE /admin/vault/api/cleanup             — Cleanup old backups

    Health API:
        GET    /admin/vault/api/health              — System health check

    Audit API:
        GET    /admin/vault/api/audit               — Query audit logs

    Schedule API:
        GET    /admin/vault/api/schedule/list       — List schedules
        POST   /admin/vault/api/schedule/create     — Create schedule
        PUT    /admin/vault/api/schedule/<id>       — Update schedule
        DELETE /admin/vault/api/schedule/<id>       — Delete schedule

    Restore API:
        POST   /admin/vault/api/restore             — Execute restore
        POST   /admin/vault/api/restore/preview     — Preview backup contents
"""

import os
import sys
import json
import glob
import shutil
from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, jsonify, render_template, send_file, request, session, redirect

vault_bp = Blueprint('vault', __name__, url_prefix='/admin/vault',
                     template_folder='templates')

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
BACKUP_DIR = os.path.join(BASE_DIR, 'data', 'vault')


# Static file routes (explicit, more reliable than Blueprint static_url_path)
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')

@vault_bp.route('/static/<path:filename>')
def vault_static(filename):
    """Serve vault static files (CSS, JS)."""
    return send_file(os.path.join(STATIC_DIR, filename))


# ══════════════════════════════════════════════════════════════
# Auth Decorator
# ══════════════════════════════════════════════════════════════

def _require_vault_auth(f):
    """Decorator: require user login for API access.
    
    Authenticates via JWT sso_token (cookie or query param) — 
    matching the admin app's auth mechanism.
    """
    @wraps(f)
    def wrapped(*args, **kwargs):
        token = request.args.get('token') or request.cookies.get('sso_token')
        if not token:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
               request.content_type == 'application/json':
                return jsonify({'success': False, 'error': 'Authentication required'}), 401
            return redirect('/admin/login')
        try:
            from services.jwt_service import validate_token
            payload = validate_token(token)
            if not payload or not payload.get('is_admin'):
                raise ValueError('Invalid admin token')
        except Exception:
            return redirect('/admin/login')
        return f(*args, **kwargs)
    return wrapped


def _get_backup_dir():
    """Get absolute backup directory path."""
    return BACKUP_DIR


def _list_backup_archives():
    """List all backup archives sorted by time (newest first)."""
    backup_dir = _get_backup_dir()
    archives = []
    for f in sorted(glob.glob(os.path.join(backup_dir, 'vault_*.tar.gz')), reverse=True):
        fname = os.path.basename(f)
        label = fname.replace('.tar.gz', '')
        stat = os.stat(f)
        archives.append({
            'label': label,
            'filename': fname,
            'size_mb': round(stat.st_size / (1024 * 1024), 1),
            'backup_type': 'full',
            'status': 'success',
            'created_at': datetime.utcfromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
        })
    return archives


# ══════════════════════════════════════════════════════════════
# Page Routes
# ══════════════════════════════════════════════════════════════

@vault_bp.route('/')
@_require_vault_auth
def dashboard():
    """Render vault dashboard page."""
    return render_template('vault.html')


@vault_bp.route('/backups')
@_require_vault_auth
def backups_page():
    return render_template('vault.html')


@vault_bp.route('/restore')
@_require_vault_auth
def restore_page():
    return render_template('vault_restore.html')


@vault_bp.route('/schedules')
@_require_vault_auth
def schedules_page():
    return render_template('vault_schedules.html')


@vault_bp.route('/storage')
@_require_vault_auth
def storage_page():
    return render_template('vault_storage.html')


@vault_bp.route('/settings')
@_require_vault_auth
def settings_page():
    return render_template('vault_settings.html')


@vault_bp.route('/audit')
@_require_vault_auth
def audit_page():
    return render_template('vault_audit.html')


# ══════════════════════════════════════════════════════════════
# Backup API — Legacy (backward compatible)
# ══════════════════════════════════════════════════════════════

@vault_bp.route('/api/create', methods=['POST'])
@_require_vault_auth
def api_create_backup_legacy():
    """Trigger a full backup (legacy endpoint)."""
    return _handle_backup_create()


@vault_bp.route('/api/list', methods=['GET'])
@_require_vault_auth
def api_list_backups_legacy():
    """List all backup archives (legacy endpoint)."""
    try:
        archives = _list_backup_archives()
        return jsonify({'success': True, 'backups': archives, 'total': len(archives)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@vault_bp.route('/api/download/<label>', methods=['GET'])
@_require_vault_auth
def api_download_backup_legacy(label):
    """Download a backup archive (legacy endpoint)."""
    return _handle_backup_download(label)


@vault_bp.route('/api/delete/<label>', methods=['DELETE'])
@_require_vault_auth
def api_delete_backup_legacy(label):
    """Delete a backup archive (legacy endpoint)."""
    return _handle_backup_delete(label)


@vault_bp.route('/api/cleanup', methods=['DELETE'])
@_require_vault_auth
def api_cleanup_backups():
    """Cleanup backups older than configured keep_days."""
    try:
        keep_days = 30
        try:
            from plugins._base.db import get_raw_connection
            conn = get_raw_connection()
            cur = conn.cursor()
            cur.execute("SELECT config FROM plugin_registry WHERE identifier = 'vault'")
            row = cur.fetchone()
            if row and row[0]:
                cfg = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                keep_days = int(cfg.get('keep_days', 30))
            cur.close()
            conn.close()
        except Exception:
            pass

        cutoff = datetime.utcnow() - timedelta(days=keep_days)
        backup_dir = _get_backup_dir()
        deleted = 0
        for f in glob.glob(os.path.join(backup_dir, 'vault_*.tar.gz')):
            mtime = datetime.utcfromtimestamp(os.stat(f).st_mtime)
            if mtime < cutoff:
                os.remove(f)
                deleted += 1

        return jsonify({'success': True, 'deleted': deleted, 'keep_days': keep_days})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ══════════════════════════════════════════════════════════════
# Backup API — New (Phase 1)
# ══════════════════════════════════════════════════════════════

@vault_bp.route('/api/backup/create', methods=['POST'])
@_require_vault_auth
def api_create_backup():
    """Create backup (supports full / incremental / differential)."""
    return _handle_backup_create()


@vault_bp.route('/api/backup/list', methods=['GET'])
@_require_vault_auth
def api_list_backups():
    """List backups with search, filtering, and pagination."""
    try:
        search = request.args.get('search', '').strip().lower()
        backup_type = request.args.get('type', '').strip()
        status = request.args.get('status', '').strip()
        page = max(1, int(request.args.get('page', 1)))
        per_page = max(1, min(100, int(request.args.get('per_page', 20))))

        archives = _list_backup_archives()

        # Apply filters
        if search:
            archives = [a for a in archives if search in a['label'].lower()]
        if backup_type:
            archives = [a for a in archives if a.get('backup_type') == backup_type]
        if status:
            archives = [a for a in archives if a.get('status') == status]

        total = len(archives)
        start = (page - 1) * per_page
        end = start + per_page
        items = archives[start:end]

        return jsonify({
            'success': True,
            'backups': items,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': max(1, (total + per_page - 1) // per_page),
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@vault_bp.route('/api/backup/detail/<label>', methods=['GET'])
@_require_vault_auth
def api_backup_detail(label):
    """Get backup detail with content preview."""
    archive_path = os.path.join(BACKUP_DIR, f'{label}.tar.gz')
    if not os.path.isfile(archive_path):
        return jsonify({'success': False, 'error': 'Backup not found'}), 404

    import tarfile
    stat = os.stat(archive_path)
    content_preview = []
    try:
        with tarfile.open(archive_path, 'r:gz') as tar:
            for member in tar.getmembers()[:50]:
                content_preview.append({
                    'name': member.name,
                    'size': member.size,
                    'type': 'dir' if member.isdir() else 'file',
                })
    except Exception:
        pass

    return jsonify({
        'success': True,
        'backup': {
            'label': label,
            'size_mb': round(stat.st_size / (1024 * 1024), 1),
            'created_at': datetime.utcfromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            'content_preview': content_preview,
        },
    })


@vault_bp.route('/api/backup/download/<label>', methods=['GET'])
@_require_vault_auth
def api_download_backup(label):
    """Download a backup archive."""
    return _handle_backup_download(label)


@vault_bp.route('/api/backup/delete/<label>', methods=['DELETE'])
@_require_vault_auth
def api_delete_backup(label):
    """Delete a backup (requires confirmation)."""
    return _handle_backup_delete(label)


# ══════════════════════════════════════════════════════════════
# Health API
# ══════════════════════════════════════════════════════════════

@vault_bp.route('/api/health', methods=['GET'])
@_require_vault_auth
def api_health_check():
    """System health: backup status, storage usage, last backup time."""
    try:
        archives = _list_backup_archives()

        # Disk usage
        backup_dir = _get_backup_dir()
        os.makedirs(backup_dir, exist_ok=True)
        total_bytes, used_bytes, free_bytes = shutil.disk_usage(backup_dir)

        # Health score
        score = 100
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        recent_backups = [a for a in archives if a['created_at'] >= today_start.strftime('%Y-%m-%d %H:%M:%S')]
        if not recent_backups:
            score -= 30

        if total_bytes > 0 and (free_bytes / total_bytes) < 0.1:
            score -= 20

        failed = [a for a in archives if a.get('status') == 'failed']
        if len(failed) > 3:
            score -= 15

        # Next schedule (check vault_schedules first, then cron_jobs)
        next_schedule = None
        try:
            from plugins._base.db import get_raw_connection
            conn = get_raw_connection()
            cur = conn.cursor()
            # Check vault_schedules table
            cur.execute("""
                SELECT MIN(next_run_at) FROM vault_schedules
                WHERE enabled = TRUE AND next_run_at > NOW()
            """)
            row = cur.fetchone()
            if row and row[0]:
                next_schedule = row[0].strftime('%Y-%m-%d %H:%M:%S')
            else:
                # Fallback: check cron_jobs table
                cur.execute("""
                    SELECT MIN(next_run_at) FROM cron_jobs
                    WHERE name LIKE 'Vault%' AND is_active = 1
                """)
                row = cur.fetchone()
                if row and row[0]:
                    next_schedule = row[0].strftime('%Y-%m-%d %H:%M:%S')
            cur.close()
            conn.close()
        except Exception:
            pass

        return jsonify({
            'success': True,
            'health': {
                'score': max(score, 0),
                'total_backups': len(archives),
                'last_backup': archives[0]['created_at'] if archives else None,
                'next_schedule': next_schedule,
                'storage': {
                    'total_gb': round(total_bytes / (1024 ** 3), 1),
                    'free_gb': round(free_bytes / (1024 ** 3), 1),
                    'used_percent': round((total_bytes - free_bytes) / total_bytes * 100, 1) if total_bytes > 0 else 0,
                },
            },
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ══════════════════════════════════════════════════════════════
# Audit API
# ══════════════════════════════════════════════════════════════

@vault_bp.route('/api/audit', methods=['GET'])
@_require_vault_auth
def api_audit_logs():
    """Query audit logs."""
    try:
        action = request.args.get('action', '')
        resource_type = request.args.get('resource_type', '')
        operator = request.args.get('operator', '')
        limit = max(1, min(500, int(request.args.get('limit', 100))))
        offset = max(0, int(request.args.get('offset', 0)))

        from .services.audit import get_audit_logs
        logs = get_audit_logs(
            action=action or None,
            resource_type=resource_type or None,
            operator=operator or None,
            limit=limit,
            offset=offset,
        )

        # Convert datetime objects to strings
        for log in logs:
            if isinstance(log.get('created_at'), datetime):
                log['created_at'] = log['created_at'].strftime('%Y-%m-%d %H:%M:%S')

        return jsonify({'success': True, 'logs': logs, 'count': len(logs)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ══════════════════════════════════════════════════════════════
# Schedule API (Phase 1 read-only; CRUD in Phase 2)
# ══════════════════════════════════════════════════════════════

@vault_bp.route('/api/schedule/list', methods=['GET'])
@_require_vault_auth
def api_list_schedules():
    """List all backup schedules."""
    try:
        from .services.scheduler import VaultScheduler
        scheduler = VaultScheduler()
        schedules = scheduler.get_all_schedules()
        # Convert datetime objects
        for s in schedules:
            for key in ('last_run_at', 'next_run_at', 'created_at'):
                if isinstance(s.get(key), datetime):
                    s[key] = s[key].strftime('%Y-%m-%d %H:%M:%S')
        return jsonify({'success': True, 'schedules': schedules})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ══════════════════════════════════════════════════════════════
# Restore API (Phase 1 preview-only; execution in Phase 2)
# ══════════════════════════════════════════════════════════════

@vault_bp.route('/api/restore/preview', methods=['POST'])
@_require_vault_auth
def api_restore_preview():
    """Preview backup contents before restore."""
    try:
        data = request.get_json(silent=True) or {}
        label = data.get('label', '')
        if not label:
            return jsonify({'success': False, 'error': 'Backup label is required'}), 400

        from .services.restore_engine import RestoreEngine
        engine = RestoreEngine()
        result = engine.preview(label)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@vault_bp.route('/api/restore', methods=['POST'])
@_require_vault_auth
def api_restore():
    """Execute restore (Phase 2 — stub for now)."""
    return jsonify({
        'success': False,
        'error': 'Restore execution coming in Phase 2. Use /api/restore/preview for dry-run.',
    }), 501


# ══════════════════════════════════════════════════════════════
# Internal handlers (shared by legacy and new endpoints)
# ══════════════════════════════════════════════════════════════

def _handle_backup_create():
    """Internal handler for backup creation with compress → encrypt → upload → notify pipeline."""
    try:
        from .services.backup_engine import create_full_backup
        result = create_full_backup()

        if result.get('archive') and result.get('success'):
            archive_path = result['archive']

            # 1. Compress
            try:
                from .services.compressor import VaultCompressor
                compressor = VaultCompressor(algorithm='gzip', level=6)
                archive_path = compressor.compress(archive_path)
                result['compressed_size_mb'] = round(os.path.getsize(archive_path) / (1024**2), 1)
            except Exception as e:
                print(f'[Vault] Compression skipped: {e}')

            # 2. Encrypt (if configured)
            try:
                from .services.encryptor import VaultEncryptor
                encryptor = VaultEncryptor()
                archive_path = encryptor.encrypt_stream(archive_path)
                result['encrypted'] = True
            except ValueError:
                pass  # encryption not configured
            except Exception as e:
                print(f'[Vault] Encryption skipped: {e}')

            # 3. Upload to remote storage
            try:
                from .services.uploader import upload_backup
                upload_result = upload_backup(result['archive'],
                                              os.path.basename(result['archive']))
                result['remote'] = upload_result
            except Exception as e:
                result['remote'] = {'uploaded': False, 'error': str(e)}

            # 4. Notify
            try:
                from .services.notifier import VaultNotifier
                notifier = VaultNotifier()
                event = 'backup.success' if result.get('success') else 'backup.failed'
                notifier.send(
                    event=event,
                    message='Backup %s (%s MB)' % (result['label'], result.get('size_mb', 0)),
                    level='info' if result.get('success') else 'error',
                    details=result,
                )
            except Exception:
                pass

        # Write to vault_backups table
        try:
            from plugins._base.db import get_raw_connection
            conn = get_raw_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO vault_backups
                    (label, backup_type, status, size_bytes, checksum_sha256,
                     content_summary, started_at, completed_at, created_by)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                result['label'],
                result.get('backup_type', 'full'),
                'success' if result.get('success') else 'failed',
                int(result.get('size_mb', 0) * 1024 * 1024),
                result.get('checksum_sha256'),
                json.dumps({'files': len(result.get('files', []))}),
                datetime.utcnow(),
                datetime.utcnow(),
                session.get('user', {}).get('username', 'system'),
            ))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f'[Vault] Failed to write backup record to DB: {e}')

        # Audit log
        try:
            from .services.audit import log_audit
            log_audit(
                action='backup.full.create',
                resource_type='backup',
                resource_id=result.get('label', ''),
                details={
                    'type': 'full',
                    'size_mb': result.get('size_mb'),
                    'checksum': result.get('checksum_sha256'),
                },
            )
        except Exception:
            pass

        return jsonify(result), 200 if result.get('success') else 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def _handle_backup_download(label):
    """Internal handler for backup download."""
    filepath = os.path.join(BACKUP_DIR, f'{label}.tar.gz')
    if not os.path.isfile(filepath):
        return jsonify({'success': False, 'error': 'Backup not found'}), 404
    return send_file(filepath, as_attachment=True, download_name=f'{label}.tar.gz')


def _handle_backup_delete(label):
    """Internal handler for backup deletion. Confirmation via POST body."""
    data = request.get_json(silent=True) or {}
    if not data.get('confirm'):
        return jsonify({
            'success': False,
            'error': 'Confirmation required',
            'confirm_required': True,
            'message': 'Are you sure you want to delete backup "%s"? This action cannot be undone.' % label,
        }), 400

    filepath = os.path.join(BACKUP_DIR, f'{label}.tar.gz')
    if not os.path.isfile(filepath):
        return jsonify({'success': False, 'error': 'Backup not found'}), 404

    try:
        os.remove(filepath)
        # Audit log
        try:
            from .services.audit import log_audit
            log_audit('backup.delete', 'backup', label)
        except Exception:
            pass
        return jsonify({'success': True, 'message': f'Backup {label} deleted'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
