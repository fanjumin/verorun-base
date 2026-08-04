/* ══════════════════════════════════════════════════════════════
   Vault 2.0 — Plugin JavaScript
   Dashboard health, backup CRUD, search, XSS-safe rendering.
   ══════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  // ── State ──
  var state = {
    backups: [],
    health: null,
    page: 1,
    perPage: 20,
    totalPages: 1,
  };

  // ── Toast ──
  function toast(msg, type) {
    var el = document.createElement('div');
    el.className = 'toast toast-' + (type || 'info');
    el.textContent = msg;
    document.body.appendChild(el);
    setTimeout(function () { el.remove(); }, 4000);
  }

  // ── API helper ──
  function api(url, opts) {
    opts = opts || {};
    opts.headers = opts.headers || {};
    opts.headers['X-Internal-Secret'] = 'vault-internal';
    return fetch(url, opts).then(function (r) {
      if (!r.ok) {
        return r.json().then(function (d) {
          throw new Error(d.error || 'Request failed');
        });
      }
      return r.json();
    });
  }

  // ── Health ──
  function loadHealth() {
    api('/admin/vault/api/health')
      .then(function (data) {
        state.health = data.health;
        var score = document.getElementById('healthScore');
        if (score) {
          score.textContent = data.health.score + '/100';
          score.style.color =
            data.health.score >= 80 ? 'var(--green)' :
            data.health.score >= 50 ? 'var(--gold)' : 'var(--rose)';
        }
        var storage = document.getElementById('storageUsed');
        if (storage) {
          storage.textContent = data.health.storage.used_percent + '%';
        }
        var lastBackup = document.getElementById('lastBackup');
        if (lastBackup) {
          lastBackup.textContent = data.health.last_backup || '--';
        }
        var nextSchedule = document.getElementById('nextSchedule');
        if (nextSchedule) {
          nextSchedule.textContent = data.health.next_schedule || '--';
        }
      })
      .catch(function (e) {
        toast('Health check failed: ' + e.message, 'error');
      });
  }

  // ── Backup list ──
  function loadBackups(search, type, status) {
    var params = new URLSearchParams({ page: state.page, per_page: state.perPage });
    if (search) params.set('search', search);
    if (type) params.set('type', type);
    if (status) params.set('status', status);

    api('/admin/vault/api/backup/list?' + params.toString())
      .then(function (data) {
        state.backups = data.backups;
        state.totalPages = data.total_pages;
        renderBackupTable(data.backups);
      })
      .catch(function (e) {
        toast('Failed to load backups: ' + e.message, 'error');
      });
  }

  function renderBackupTable(backups) {
    var tbody = document.getElementById('backupTbody');
    if (!tbody) return;

    if (!backups || backups.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="6" class="empty-state">No backups yet</td></tr>';
      return;
    }

    tbody.innerHTML = backups
      .map(function (b) {
        return (
          '<tr>' +
          '<td><strong>' + escHtml(b.label) + '</strong></td>' +
          '<td><span class="badge badge-' + (b.backup_type === 'full' ? 'success' : 'pending') + '">' +
          escHtml(b.backup_type) + '</span></td>' +
          '<td>' + b.size_mb + ' MB</td>' +
          '<td><span class="badge badge-' + (b.status === 'success' ? 'success' : 'failed') + '">' +
          escHtml(b.status) + '</span></td>' +
          '<td>' + escHtml(b.created_at) + '</td>' +
          '<td class="actions-col">' +
          '<a class="btn btn-outline btn-sm" href="/admin/vault/api/backup/download/' +
          encodeURIComponent(b.label) + '" download>Download</a> ' +
          '<button class="btn btn-danger btn-sm" onclick="deleteBackup(\'' +
          escAttr(b.label) + '\')">Delete</button>' +
          '</td>' +
          '</tr>'
        );
      })
      .join('');
  }

  // ── Create backup ──
  function createBackup(type) {
    var btn = document.getElementById('btnBackupNow');
    if (btn) { btn.disabled = true; btn.textContent = 'Creating...'; }

    api('/admin/vault/api/backup/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type: type || 'full', encrypt: false }),
    })
      .then(function (data) {
        if (data.success) {
          toast('Backup created: ' + data.label + ' (' + data.size_mb + ' MB)', 'success');
          loadBackups();
          loadHealth();
        } else {
          toast('Backup failed: ' + (data.error || 'unknown'), 'error');
        }
      })
      .catch(function (e) { toast('Backup error: ' + e.message, 'error'); })
      .finally(function () {
        if (btn) { btn.disabled = false; btn.textContent = '+ Backup Now'; }
      });
  }

  // ── Delete backup ──
  function deleteBackup(label) {
    if (!confirm('Delete backup ' + label + '? This cannot be undone.')) return;
    api('/admin/vault/api/backup/delete/' + encodeURIComponent(label), {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ confirm: true }),
    })
      .then(function (data) {
        toast('Backup deleted', 'success');
        loadBackups();
        loadHealth();
      })
      .catch(function (e) { toast('Delete failed: ' + e.message, 'error'); });
  }

  // ── Search (debounced) ──
  function setupSearch() {
    var input = document.getElementById('backupSearch');
    if (!input) return;
    var timer;
    input.addEventListener('input', function () {
      clearTimeout(timer);
      timer = setTimeout(function () {
        state.page = 1;
        loadBackups(input.value);
      }, 300);
    });
  }

  // ── XSS escape ──
  function escHtml(str) {
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function escAttr(str) {
    return String(str).replace(/&/g, '&amp;').replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  // ── Cleanup ──
  function cleanupBackups() {
    if (!confirm('Delete backups older than retention period?')) return;
    api('/admin/vault/api/cleanup', { method: 'DELETE' })
      .then(function (data) {
        if (data.success) {
          toast('Cleaned up ' + data.deleted + ' old backup(s)', 'success');
          loadBackups();
          loadHealth();
        } else {
          toast('Cleanup failed: ' + (data.error || 'unknown'), 'error');
        }
      })
      .catch(function (e) { toast('Cleanup error: ' + e.message, 'error'); });
  }

  // ── Expose globals for inline onclick ──
  window.createBackup = createBackup;
  window.deleteBackup = deleteBackup;
  window.cleanupBackups = cleanupBackups;

  // ── Init ──
  document.addEventListener('DOMContentLoaded', function () {
    loadHealth();
    loadBackups();
    setupSearch();

    // 30-second health poll
    setInterval(loadHealth, 30000);

    var btn = document.getElementById('btnBackupNow');
    if (btn) {
      btn.addEventListener('click', function () { createBackup('full'); });
    }
  });
})();
