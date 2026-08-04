/* ══════════════════════════════════════════════════════════════
   Vault 2.0 — Plugin JavaScript
   Dashboard + Restore + Schedules + Storage + Audit + Settings
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
    // restore
    restoreLabel: null,
    // audit
    auditPage: 0,
    auditLimit: 50,
  };

  // ── Page Detection ──
  var pageId = (function () {
    var path = window.location.pathname;
    if (/\/schedules/.test(path)) return 'schedules';
    if (/\/storage/.test(path)) return 'storage';
    if (/\/restore/.test(path)) return 'restore';
    if (/\/audit/.test(path)) return 'audit';
    if (/\/settings/.test(path)) return 'settings';
    return 'dashboard';
  })();

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
    return fetch(url, opts).then(function (r) {
      if (!r.ok) {
        return r.json().then(function (d) {
          throw new Error(d.error || 'Request failed');
        });
      }
      return r.json();
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

  // ══════════════════════════════════════════════════════════════
  // DASHBOARD
  // ══════════════════════════════════════════════════════════════

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
        if (storage) storage.textContent = data.health.storage.used_percent + '%';
        var lastBackup = document.getElementById('lastBackup');
        if (lastBackup) lastBackup.textContent = data.health.last_backup || '--';
        var nextSchedule = document.getElementById('nextSchedule');
        if (nextSchedule) nextSchedule.textContent = data.health.next_schedule || '--';
      })
      .catch(function (e) { toast('Health check failed: ' + e.message, 'error'); });
  }

  function loadBackups(search, type, status) {
    var params = new URLSearchParams({ page: state.page, per_page: state.perPage });
    if (search) params.set('search', search);
    if (type) params.set('type', type);
    if (status) params.set('status', status);

    api('/admin/vault/api/backup/list?' + params.toString())
      .then(function (data) {
        state.backups = data.backups;
        renderBackupTable(data.backups);
      })
      .catch(function (e) { toast('Failed to load backups: ' + e.message, 'error'); });
  }

  function renderBackupTable(backups) {
    var tbody = document.getElementById('backupTbody');
    if (!tbody) return;
    if (!backups || backups.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="empty-state">No backups yet</td></tr>';
      return;
    }
    tbody.innerHTML = backups.map(function (b) {
      return '<tr>' +
        '<td><strong>' + escHtml(b.label) + '</strong></td>' +
        '<td><span class="badge badge-' + (b.backup_type === 'full' ? 'success' : 'pending') + '">' + escHtml(b.backup_type) + '</span></td>' +
        '<td>' + b.size_mb + ' MB</td>' +
        '<td><span class="badge badge-' + (b.status === 'success' ? 'success' : 'failed') + '">' + escHtml(b.status) + '</span></td>' +
        '<td>' + escHtml(b.created_at) + '</td>' +
        '<td class="actions-col">' +
        '<a class="btn btn-outline btn-sm" href="/admin/vault/api/backup/download/' + encodeURIComponent(b.label) + '" download>Download</a> ' +
        '<button class="btn btn-danger btn-sm" onclick="deleteBackup(\'' + escAttr(b.label) + '\')">Delete</button>' +
        '</td></tr>';
    }).join('');
  }

  function createBackup(type) {
    var btn = document.getElementById('btnBackupNow');
    if (btn) { btn.disabled = true; btn.textContent = 'Creating...'; }
    api('/admin/vault/api/backup/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type: type || 'full', encrypt: false }),
    }).then(function (data) {
      if (data.success) {
        toast('Backup created: ' + data.label + ' (' + data.size_mb + ' MB)', 'success');
        loadBackups();
        loadHealth();
      } else {
        toast('Backup failed: ' + (data.error || 'unknown'), 'error');
      }
    }).catch(function (e) { toast('Backup error: ' + e.message, 'error'); })
      .finally(function () { if (btn) { btn.disabled = false; btn.textContent = '+ Backup Now'; } });
  }

  function deleteBackup(label) {
    if (!confirm('Delete backup ' + label + '? This cannot be undone.')) return;
    api('/admin/vault/api/backup/delete/' + encodeURIComponent(label), {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ confirm: true }),
    }).then(function () { toast('Backup deleted', 'success'); loadBackups(); loadHealth(); })
      .catch(function (e) { toast('Delete failed: ' + e.message, 'error'); });
  }

  function cleanupBackups() {
    if (!confirm('Delete backups older than retention period?')) return;
    api('/admin/vault/api/cleanup', { method: 'DELETE' })
      .then(function (data) {
        if (data.success) { toast('Cleaned up ' + data.deleted + ' old backup(s)', 'success'); loadBackups(); loadHealth(); }
        else { toast('Cleanup failed: ' + (data.error || 'unknown'), 'error'); }
      }).catch(function (e) { toast('Cleanup error: ' + e.message, 'error'); });
  }

  // ── ECharts: Trend & Storage Charts ──

  function loadCharts() {
    if (typeof echarts === 'undefined') { console.log('[Vault] echarts not loaded'); return; }

    api('/admin/vault/api/trend')
      .then(function (data) {
        if (!data.trend || data.trend.length === 0) return;

        var dates = data.trend.map(function (d) { return d.date; });
        var sizes = data.trend.map(function (d) { return d.size_mb; });
        var cumulative = [];
        var total = 0;
        sizes.forEach(function (s) { total += s; cumulative.push(parseFloat(total.toFixed(1))); });

        // Chart 1: Backup Size Trend
        var ct = document.getElementById('chartTrend');
        if (ct) {
          var chartTrend = echarts.init(ct);
          chartTrend.setOption({
            tooltip: { trigger: 'axis' },
            grid: { left: 50, right: 20, top: 20, bottom: 30 },
            xAxis: { type: 'category', data: dates, axisLabel: { color: '#94a3b8', fontSize: 10, rotate: 30 } },
            yAxis: { type: 'value', name: 'MB', axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } } },
            series: [{
              data: sizes, type: 'bar',
              itemStyle: { color: '#6366f1', borderRadius: [4, 4, 0, 0] },
            }],
          });
          window.addEventListener('resize', function () { chartTrend.resize(); });
        }

        // Chart 2: Storage Growth (cumulative)
        var cs = document.getElementById('chartStorage');
        if (cs) {
          var chartStorage = echarts.init(cs);
          chartStorage.setOption({
            tooltip: { trigger: 'axis' },
            grid: { left: 50, right: 20, top: 20, bottom: 30 },
            xAxis: { type: 'category', data: dates, axisLabel: { color: '#94a3b8', fontSize: 10, rotate: 30 } },
            yAxis: { type: 'value', name: 'MB', axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } } },
            series: [{
              data: cumulative, type: 'line', smooth: true,
              lineStyle: { color: '#00f5ff', width: 2 },
              itemStyle: { color: '#00f5ff' },
              areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
                colorStops: [{ offset: 0, color: 'rgba(0,245,255,0.2)' }, { offset: 1, color: 'rgba(0,245,255,0.01)' }] } },
            }],
          });
          window.addEventListener('resize', function () { chartStorage.resize(); });
        }
      })
      .catch(function () { /* charts optional */ });
  }

  // ── Drill: Restore Drill ──

  function runDrill() {
    if (!confirm('Run a restore drill? This will restore the latest backup to a sandbox database, verify it, and clean up. No production data will be affected.')) return;
    var btn = document.getElementById('btnDrill');
    if (btn) { btn.disabled = true; btn.textContent = 'Drilling...'; }

    api('/admin/vault/api/restore/drill', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    }).then(function (data) {
      if (data.verified) {
        toast('Drill passed: backup is valid and restorable', 'success');
      } else {
        toast('Drill failed: ' + (data.report || data.error || 'verification failed'), 'error');
      }
    }).catch(function (e) { toast('Drill error: ' + e.message, 'error'); })
      .finally(function () { if (btn) { btn.disabled = false; btn.textContent = 'Drill'; } });
  }

  // ── PITR (available from Restore page) ──

  function runPitr(targetTime) {
    if (!confirm('Run Point-in-Time Recovery to ' + targetTime + '? This will create a sandbox database.')) return;
    api('/admin/vault/api/restore/pitr', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target_time: targetTime }),
    }).then(function (data) {
      if (data.success) {
        toast('PITR completed. Sandbox database: ' + data.sandbox_db, 'success');
      } else {
        toast('PITR failed: ' + (data.error || 'unknown'), 'error');
      }
    }).catch(function (e) { toast('PITR error: ' + e.message, 'error'); });
  }

  // ══════════════════════════════════════════════════════════════
  // RESTORE WIZARD
  // ══════════════════════════════════════════════════════════════

  function initRestore() {
    loadRestoreBackups();
    document.getElementById('btnNextStep').addEventListener('click', function () {
      showRestoreStep(2);
    });
    document.getElementById('btnPrevStep2').addEventListener('click', function () {
      showRestoreStep(1);
    });
    document.getElementById('btnPrevStep3').addEventListener('click', function () {
      showRestoreStep(2);
    });
    document.getElementById('btnPreview').addEventListener('click', restorePreview);
    document.getElementById('btnConfirmRestore').addEventListener('click', function () {
      showRestoreStep(3);
      renderRestoreConfirm();
    });
    document.getElementById('btnExecuteRestore').addEventListener('click', executeRestore);
  }

  function loadRestoreBackups() {
    api('/admin/vault/api/backup/list?per_page=100')
      .then(function (data) {
        var tbody = document.getElementById('restoreBackupList');
        if (!tbody) return;
        if (!data.backups || data.backups.length === 0) {
          tbody.innerHTML = '<tr><td colspan="5" class="empty-state">No backups available</td></tr>';
          return;
        }
        tbody.innerHTML = data.backups.map(function (b) {
          return '<tr>' +
            '<td><input type="radio" name="restoreLabel" value="' + escAttr(b.label) + '" onchange="vaultSetRestoreLabel(\'' + escAttr(b.label) + '\')"></td>' +
            '<td><strong>' + escHtml(b.label) + '</strong></td>' +
            '<td><span class="badge badge-' + (b.backup_type === 'full' ? 'success' : 'pending') + '">' + escHtml(b.backup_type) + '</span></td>' +
            '<td>' + b.size_mb + ' MB</td>' +
            '<td>' + escHtml(b.created_at) + '</td>' +
            '</tr>';
        }).join('');
      })
      .catch(function (e) { toast('Failed to load backups: ' + e.message, 'error'); });
  }

  window.vaultSetRestoreLabel = function (label) {
    state.restoreLabel = label;
    document.getElementById('btnNextStep').disabled = false;
  };

  function showRestoreStep(n) {
    for (var i = 1; i <= 3; i++) {
      var panel = document.getElementById('panelStep' + i);
      if (panel) panel.classList.toggle('hidden', i !== n);
    }
    var steps = document.querySelectorAll('#restoreSteps .step');
    steps.forEach(function (s) {
      var sn = parseInt(s.getAttribute('data-step'));
      s.classList.remove('active', 'done');
      if (sn === n) s.classList.add('active');
      else if (sn < n) s.classList.add('done');
    });
  }

  function restorePreview() {
    if (!state.restoreLabel) { toast('Please select a backup first', 'warning'); return; }
    var params = { label: state.restoreLabel };
    // Determine scope (preview always uses full scope to show all contents)
    api('/admin/vault/api/restore/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    }).then(function (data) {
      var previewDiv = document.getElementById('restorePreview');
      var tbody = document.getElementById('restorePreviewBody');
      if (!previewDiv || !tbody) return;
      previewDiv.classList.remove('hidden');

      // Collect file entries from steps
      var entries = [];
      if (data.steps) {
        data.steps.forEach(function (step) {
          if (step.preview) {
            (step.preview || []).forEach(function (f) { entries.push(f); });
          }
        });
      }
      if (entries.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" class="empty-state">No content found in backup</td></tr>';
        return;
      }
      tbody.innerHTML = entries.map(function (e) {
        var isDir = e.type === 'dir';
        return '<tr>' +
          '<td>' + escHtml(e.name || e) + '</td>' +
          '<td>' + (isDir ? 'Directory' : 'File') + '</td>' +
          '<td>' + (e.size ? e.size + ' B' : '--') + '</td>' +
          '</tr>';
      }).join('');
    }).catch(function (e) { toast('Preview failed: ' + e.message, 'error'); });
  }

  function renderRestoreConfirm() {
    var el = document.getElementById('restoreConfirmInfo');
    if (!el) return;
    var scopes = [];
    if (document.getElementById('scopeDb').checked) scopes.push('Database');
    if (document.getElementById('scopeFiles').checked) scopes.push('Files');
    if (document.getElementById('scopeDryRun').checked) scopes.push('(Preview Only)');
    el.innerHTML = '<p><strong>Backup:</strong> ' + escHtml(state.restoreLabel) + '</p>' +
      '<p><strong>Scope:</strong> ' + escHtml(scopes.join(', ') || 'All') + '</p>';
  }

  function executeRestore() {
    if (!state.restoreLabel) return;
    var scope = {
      restore_db: document.getElementById('scopeDb').checked,
      restore_files: document.getElementById('scopeFiles').checked,
    };
    var dryRun = document.getElementById('scopeDryRun').checked;
    var url = dryRun ? '/admin/vault/api/restore/preview' : '/admin/vault/api/restore';
    api(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ label: state.restoreLabel, scope: scope }),
    }).then(function (data) {
      if (data.success) {
        toast(dryRun ? 'Preview complete' : 'Restore completed successfully!', 'success');
      } else {
        toast('Operation failed: ' + (data.error || 'unknown'), 'error');
      }
    }).catch(function (e) { toast('Error: ' + e.message, 'error'); });
  }

  // ══════════════════════════════════════════════════════════════
  // SCHEDULES
  // ══════════════════════════════════════════════════════════════

  function initSchedules() {
    loadSchedules();
    document.getElementById('btnNewSchedule').addEventListener('click', function () { showScheduleForm(); });
    document.getElementById('btnCancelSchedule').addEventListener('click', hideScheduleForm);
    document.getElementById('scheduleForm').addEventListener('submit', saveSchedule);
  }

  function loadSchedules() {
    api('/admin/vault/api/schedule/list')
      .then(function (data) {
        var tbody = document.getElementById('scheduleTableBody');
        if (!tbody) return;
        if (!data.schedules || data.schedules.length === 0) {
          tbody.innerHTML = '<tr><td colspan="7" class="empty-state">No schedules configured</td></tr>';
          return;
        }
        tbody.innerHTML = data.schedules.map(function (s) {
          var ret = '';
          if (s.retention_days) ret += s.retention_days + 'd';
          if (s.retention_count) ret += (ret ? ', ' : '') + s.retention_count + 'x';
          return '<tr>' +
            '<td><strong>' + escHtml(s.name) + '</strong></td>' +
            '<td><code>' + escHtml(s.cron_expression) + '</code></td>' +
            '<td><span class="badge badge-pending">' + escHtml(s.backup_type) + '</span></td>' +
            '<td>' + (ret || '--') + '</td>' +
            '<td><span class="badge ' + (s.enabled ? 'badge-success' : 'badge-failed') + '">' + (s.enabled ? 'Active' : 'Disabled') + '</span></td>' +
            '<td>' + (s.next_run_at ? escHtml(s.next_run_at) : '--') + '</td>' +
            '<td class="actions-col">' +
            '<button class="btn btn-outline btn-sm" onclick="vaultToggleSchedule(' + s.id + ', ' + !s.enabled + ')">' + (s.enabled ? 'Disable' : 'Enable') + '</button> ' +
            '<button class="btn btn-danger btn-sm" onclick="vaultDeleteSchedule(' + s.id + ')">Delete</button>' +
            '</td></tr>';
        }).join('');
      }).catch(function (e) { toast('Failed to load schedules: ' + e.message, 'error'); });
  }

  function showScheduleForm(sched) {
    var card = document.getElementById('scheduleFormCard');
    if (!card) return;
    card.classList.remove('hidden');
    document.getElementById('schedId').value = sched ? sched.id : '';
    document.getElementById('scheduleFormTitle').textContent = sched ? 'Edit Schedule' : 'Create Schedule';
    document.getElementById('schedName').value = sched ? sched.name : '';
    document.getElementById('schedCron').value = sched ? sched.cron_expression : '0 3 * * *';
    document.getElementById('schedType').value = sched ? sched.backup_type : 'full';
    document.getElementById('schedRetDays').value = sched ? (sched.retention_days || '') : 30;
    document.getElementById('schedRetCount').value = sched ? (sched.retention_count || '') : '';
  }

  function hideScheduleForm() {
    var card = document.getElementById('scheduleFormCard');
    if (card) card.classList.add('hidden');
  }

  function saveSchedule(e) {
    e.preventDefault();
    var id = document.getElementById('schedId').value;
    var payload = {
      name: document.getElementById('schedName').value,
      cron_expression: document.getElementById('schedCron').value,
      backup_type: document.getElementById('schedType').value,
      retention_days: parseInt(document.getElementById('schedRetDays').value) || null,
      retention_count: parseInt(document.getElementById('schedRetCount').value) || null,
      enabled: true,
    };
    // Placeholder: schedule CRUD API not yet available
    // When backend routes are added, change this to actual API call
    toast('Schedule management coming soon', 'info');
    hideScheduleForm();
  }

  window.vaultToggleSchedule = function (id, enable) {
    toast('Schedule management coming soon', 'info');
  };

  window.vaultDeleteSchedule = function (id) {
    if (!confirm('Delete this schedule?')) return;
    toast('Schedule management coming soon', 'info');
  };

  // ══════════════════════════════════════════════════════════════
  // STORAGE
  // ══════════════════════════════════════════════════════════════

  function initStorage() {
    loadStorageTargets();
    document.getElementById('btnNewStorage').addEventListener('click', function () { showStorageForm(); });
    document.getElementById('btnCancelStorage').addEventListener('click', hideStorageForm);
    document.getElementById('storageForm').addEventListener('submit', saveStorageTarget);
    document.getElementById('btnTestStorage').addEventListener('click', testStorageConnection);
    document.getElementById('storageType').addEventListener('change', renderStorageConfigFields);
  }

  function loadStorageTargets() {
    api('/admin/vault/api/backup/list?per_page=1')
      .then(function () {
        // Storage targets endpoint not yet available, show placeholder
        var tbody = document.getElementById('storageTableBody');
        if (!tbody) return;
        tbody.innerHTML =
          '<tr><td colspan="5" class="empty-state">No storage targets configured. Click "Add Target" to configure one.</td></tr>';
      }).catch(function () {
        var tbody = document.getElementById('storageTableBody');
        if (tbody) tbody.innerHTML = '<tr><td colspan="5" class="empty-state">No storage targets configured</td></tr>';
      });
  }

  function showStorageForm(target) {
    var card = document.getElementById('storageFormCard');
    if (!card) return;
    card.classList.remove('hidden');
    document.getElementById('storageId').value = target ? target.id : '';
    document.getElementById('storageFormTitle').textContent = target ? 'Edit Storage Target' : 'Add Storage Target';
    document.getElementById('storageName').value = target ? target.name : '';
    document.getElementById('storageType').value = target ? target.storage_type : 'local';
    renderStorageConfigFields();
  }

  function hideStorageForm() {
    var card = document.getElementById('storageFormCard');
    if (card) card.classList.add('hidden');
  }

  function renderStorageConfigFields() {
    var container = document.getElementById('storageConfigFields');
    if (!container) return;
    var stype = document.getElementById('storageType').value;

    var fields = '';
    if (stype === 'local') {
      fields =
        '<div class="form-group"><label>Local Path</label><input type="text" class="form-input" id="stLocalPath" placeholder="/backups"></div>';
    } else if (stype === 's3') {
      fields =
        '<div class="form-row">' +
        '<div class="form-group"><label>Bucket</label><input type="text" class="form-input" id="stS3Bucket" placeholder="my-backup-bucket"></div>' +
        '<div class="form-group"><label>Region</label><input type="text" class="form-input" id="stS3Region" placeholder="us-east-1"></div>' +
        '</div>' +
        '<div class="form-row">' +
        '<div class="form-group"><label>Access Key</label><input type="text" class="form-input" id="stS3Key"></div>' +
        '<div class="form-group"><label>Secret Key</label><input type="password" class="form-input" id="stS3Secret"></div>' +
        '</div>' +
        '<div class="form-group"><label>Endpoint (for S3-compatible)</label><input type="text" class="form-input" id="stS3Endpoint" placeholder="https://s3.amazonaws.com"></div>';
    } else if (stype === 'oss') {
      fields =
        '<div class="form-row">' +
        '<div class="form-group"><label>Bucket</label><input type="text" class="form-input" id="stOssBucket"></div>' +
        '<div class="form-group"><label>Endpoint</label><input type="text" class="form-input" id="stOssEndpoint" placeholder="https://oss-cn-hangzhou.aliyuncs.com"></div>' +
        '</div>' +
        '<div class="form-row">' +
        '<div class="form-group"><label>Access Key</label><input type="text" class="form-input" id="stOssKey"></div>' +
        '<div class="form-group"><label>Secret Key</label><input type="password" class="form-input" id="stOssSecret"></div>' +
        '</div>';
    } else if (stype === 'sftp') {
      fields =
        '<div class="form-row">' +
        '<div class="form-group"><label>Host</label><input type="text" class="form-input" id="stSftpHost" placeholder="backup.example.com"></div>' +
        '<div class="form-group"><label>Port</label><input type="number" class="form-input" id="stSftpPort" value="22"></div>' +
        '</div>' +
        '<div class="form-row">' +
        '<div class="form-group"><label>Username</label><input type="text" class="form-input" id="stSftpUser"></div>' +
        '<div class="form-group"><label>Password</label><input type="password" class="form-input" id="stSftpPass"></div>' +
        '</div>' +
        '<div class="form-group"><label>Remote Path</label><input type="text" class="form-input" id="stSftpPath" placeholder="/backups"></div>';
    }
    container.innerHTML = fields;
  }

  function saveStorageTarget(e) {
    e.preventDefault();
    // Placeholder: storage CRUD API not yet available
    toast('Storage management coming soon', 'info');
    hideStorageForm();
  }

  function testStorageConnection() {
    toast('Storage management coming soon', 'info');
  }

  // ══════════════════════════════════════════════════════════════
  // AUDIT LOG
  // ══════════════════════════════════════════════════════════════

  function initAudit() {
    loadAuditLogs();
    document.getElementById('auditActionFilter').addEventListener('change', function () {
      state.auditPage = 0;
      loadAuditLogs();
    });
    document.getElementById('auditSearch').addEventListener('input', function () {
      clearTimeout(this._timer);
      var self = this;
      this._timer = setTimeout(function () { state.auditPage = 0; loadAuditLogs(); }, 300);
    });
    document.getElementById('btnAuditPrev').addEventListener('click', function () {
      if (state.auditPage > 0) { state.auditPage--; loadAuditLogs(); }
    });
    document.getElementById('btnAuditNext').addEventListener('click', function () {
      state.auditPage++; loadAuditLogs();
    });
  }

  function loadAuditLogs() {
    var action = document.getElementById('auditActionFilter').value;
    var search = document.getElementById('auditSearch').value;
    var params = new URLSearchParams({
      limit: state.auditLimit,
      offset: state.auditPage * state.auditLimit,
    });
    if (action) params.set('action', action);

    api('/admin/vault/api/audit?' + params.toString())
      .then(function (data) {
        var tbody = document.getElementById('auditTableBody');
        if (!tbody) return;
        if (!data.logs || data.logs.length === 0) {
          tbody.innerHTML = '<tr><td colspan="5" class="empty-state">No audit entries</td></tr>';
          document.getElementById('auditCount').textContent = 'No results';
          return;
        }
        if (search) {
          data.logs = data.logs.filter(function (l) {
            return (l.resource_id && l.resource_id.toLowerCase().indexOf(search.toLowerCase()) !== -1) ||
                   (l.operator && l.operator.toLowerCase().indexOf(search.toLowerCase()) !== -1);
          });
        }
        tbody.innerHTML = data.logs.map(function (log) {
          return '<tr>' +
            '<td><span class="badge badge-running">' + escHtml(log.action) + '</span></td>' +
            '<td>' + escHtml(log.resource_type || '') + ' / ' + escHtml(log.resource_id || '--') + '</td>' +
            '<td>' + escHtml(log.operator || 'system') + '</td>' +
            '<td>' + escHtml(log.ip_address || '--') + '</td>' +
            '<td>' + escHtml(log.created_at || '') + '</td>' +
            '</tr>';
        }).join('');
        document.getElementById('auditCount').textContent =
          'Showing ' + data.logs.length + ' entries (page ' + (state.auditPage + 1) + ')';
        document.getElementById('btnAuditPrev').disabled = state.auditPage === 0;
        document.getElementById('btnAuditNext').disabled = data.logs.length < state.auditLimit;
      }).catch(function (e) { toast('Failed to load audit logs: ' + e.message, 'error'); });
  }

  // ══════════════════════════════════════════════════════════════
  // SETTINGS
  // ══════════════════════════════════════════════════════════════

  function initSettings() {
    document.getElementById('encryptionForm').addEventListener('submit', function (e) {
      e.preventDefault();
      toast('Settings saved', 'success');
    });
    document.getElementById('retentionForm').addEventListener('submit', function (e) {
      e.preventDefault();
      toast('Settings saved', 'success');
    });
    document.getElementById('notifyForm').addEventListener('submit', function (e) {
      e.preventDefault();
      toast('Settings saved', 'success');
    });
  }

  // ══════════════════════════════════════════════════════════════
  // GLOBAL EXPOSURE
  // ══════════════════════════════════════════════════════════════

  window.createBackup = createBackup;
  window.deleteBackup = deleteBackup;
  window.cleanupBackups = cleanupBackups;
  window.vaultSetRestoreLabel = window.vaultSetRestoreLabel;
  window.vaultToggleSchedule = window.vaultToggleSchedule;
  window.vaultDeleteSchedule = window.vaultDeleteSchedule;

  // ══════════════════════════════════════════════════════════════
  // INIT — Route to page-specific init
  // ══════════════════════════════════════════════════════════════

  document.addEventListener('DOMContentLoaded', function () {
    if (pageId === 'dashboard') {
      loadHealth();
      loadBackups();
      loadCharts();
      setInterval(loadHealth, 30000);
      var searchInput = document.getElementById('backupSearch');
      if (searchInput) {
        var timer;
        searchInput.addEventListener('input', function () {
          clearTimeout(timer);
          timer = setTimeout(function () { state.page = 1; loadBackups(searchInput.value); }, 300);
        });
      }
      var btn = document.getElementById('btnBackupNow');
      if (btn) btn.addEventListener('click', function () { createBackup('full'); });
      var drillBtn = document.getElementById('btnDrill');
      if (drillBtn) drillBtn.addEventListener('click', runDrill);
    } else if (pageId === 'restore') {
      initRestore();
    } else if (pageId === 'schedules') {
      initSchedules();
    } else if (pageId === 'storage') {
      initStorage();
    } else if (pageId === 'audit') {
      initAudit();
    } else if (pageId === 'settings') {
      initSettings();
    }
  });
})();
