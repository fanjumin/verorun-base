#!/usr/bin/env python3
"""
Vault — Flask API Routes
=========================
Backup management: create, list, download, delete, cleanup.

API Endpoints:
    GET   /admin/vault/                 — Admin dashboard page
    POST  /admin/vault/api/create       — Trigger manual backup
    GET   /admin/vault/api/list         — List all backups
    GET   /admin/vault/api/download/<label> — Download backup archive
    DELETE /admin/vault/api/delete/<label>  — Delete a backup
    DELETE /admin/vault/api/cleanup         — Cleanup old backups
"""

import os
import sys
import json
import glob
import shutil
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, render_template, send_file, request

vault_bp = Blueprint('vault', __name__, url_prefix='/admin/vault', template_folder='templates')


def _get_backup_dir():
    """Get absolute backup directory path."""
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, 'data', 'vault')


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
            'created_at': datetime.utcfromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
        })
    return archives


@vault_bp.route('/')
def dashboard():
    """Render vault admin dashboard page."""
    return render_template('vault.html')


@vault_bp.route('/api/create', methods=['POST'])
def api_create_backup():
    """Trigger a full backup (database + config + files)."""
    try:
        from .services.dumper import create_full_backup
        result = create_full_backup()

        # Upload to remote storage if configured
        if result.get('archive') and result.get('success'):
            from .services.uploader import upload_backup
            upload_result = upload_backup(result['archive'], result['archive_name'])
            result['remote'] = upload_result

        return jsonify(result), 200 if result.get('success') else 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@vault_bp.route('/api/list', methods=['GET'])
def api_list_backups():
    """List all backup archives."""
    try:
        archives = _list_backup_archives()
        return jsonify({'success': True, 'backups': archives, 'total': len(archives)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@vault_bp.route('/api/download/<label>', methods=['GET'])
def api_download_backup(label):
    """Download a backup archive."""
    backup_dir = _get_backup_dir()
    filepath = os.path.join(backup_dir, f'{label}.tar.gz')
    if not os.path.isfile(filepath):
        return jsonify({'success': False, 'error': 'Backup not found'}), 404
    return send_file(filepath, as_attachment=True, download_name=f'{label}.tar.gz')


@vault_bp.route('/api/delete/<label>', methods=['DELETE'])
def api_delete_backup(label):
    """Delete a backup archive."""
    backup_dir = _get_backup_dir()
    filepath = os.path.join(backup_dir, f'{label}.tar.gz')
    if not os.path.isfile(filepath):
        return jsonify({'success': False, 'error': 'Backup not found'}), 404
    try:
        os.remove(filepath)
        return jsonify({'success': True, 'message': f'Backup {label} deleted'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@vault_bp.route('/api/cleanup', methods=['DELETE'])
def api_cleanup_backups():
    """Cleanup backups older than configured keep_days."""
    try:
        # Read keep_days from plugin config
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
