/**
 * EditorToolbar — floating toolbar at top of preview page.
 * Provides: save, publish, color panel toggle, spacing panel toggle, undo/redo.
 */
var EditorToolbar = (function() {

  var toolbar = null;
  var saveBtn = null;
  var countBadge = null;
  var state = null;
  var api = null;

  function init(stateManager, apiClient) {
    state = stateManager;
    api = apiClient;

    // Create toolbar DOM
    toolbar = document.createElement('div');
    toolbar.className = 'editor-toolbar';
    toolbar.innerHTML =
      '<div class="toolbar-left">' +
        '<span class="tb-brand">Editor</span>' +
        '<button class="tb-undo" title="Undo (Ctrl+Z)">\u21a9 Undo</button>' +
        '<button class="tb-redo" title="Redo (Ctrl+Shift+Z)">\u21aa Redo</button>' +
        '<span class="tb-sep"></span>' +
      '</div>' +
      '<div class="toolbar-right">' +
        '<button class="tb-versions" title="Version History">\u23f0 Versions</button>' +
        '<button class="tb-colors" title="Color Palette">\u2b1c Colors</button>' +
        '<button class="tb-spacing" title="Spacing & Typography">\u2195 Spacing</button>' +
        '<span class="tb-sep"></span>' +
        '<button class="tb-save" disabled>Save</button>' +
        '<button class="tb-publish">Publish</button>' +
      '</div>';

    document.body.insertBefore(toolbar, document.body.firstChild);

    // Show after short delay (animation)
    setTimeout(function() { toolbar.classList.add('visible'); }, 100);

    // Button references
    saveBtn = toolbar.querySelector('.tb-save');
    countBadge = document.createElement('span');
    countBadge.className = 'tb-count';
    countBadge.style.display = 'none';
    saveBtn.parentNode.insertBefore(countBadge, saveBtn.nextSibling);

    // Bind events
    toolbar.querySelector('.tb-undo').addEventListener('click', function() { state.undo(); });
    toolbar.querySelector('.tb-redo').addEventListener('click', function() { state.redo(); });
    toolbar.querySelector('.tb-versions').addEventListener('click', toggleVersionPanel);
    toolbar.querySelector('.tb-colors').addEventListener('click', toggleColorPanel);
    toolbar.querySelector('.tb-spacing').addEventListener('click', toggleSpacingPanel);
    toolbar.querySelector('.tb-save').addEventListener('click', saveAll);
    toolbar.querySelector('.tb-publish').addEventListener('click', publishAll);

    // Listen for state changes
    state.onChange(updateUI);
  }

  function updateUI(s) {
    if (!saveBtn || !countBadge) return;
    if (s.dirty && s.changeCount > 0) {
      saveBtn.disabled = false;
      countBadge.style.display = 'inline-flex';
      countBadge.textContent = s.changeCount;
    } else {
      saveBtn.disabled = true;
      countBadge.style.display = 'none';
    }
  }

  function toggleColorPanel() {
    // Delegated to color-palette.js via event
    var evt = new CustomEvent('editor-toggle-panel', { detail: { panel: 'colors' } });
    document.dispatchEvent(evt);
  }

  function toggleSpacingPanel() {
    var evt = new CustomEvent('editor-toggle-panel', { detail: { panel: 'spacing' } });
    document.dispatchEvent(evt);
  }

  /* ── Version History Panel ── */

  var versionPanel = null;

  function toggleVersionPanel() {
    if (versionPanel && versionPanel.classList.contains('visible')) {
      versionPanel.classList.remove('visible');
      return;
    }
    // Close other panels first
    closeAllPanels();
    loadVersionPanel();
  }

  function closeAllPanels() {
    document.querySelectorAll('.editor-panel.visible').forEach(function(p) {
      p.classList.remove('visible');
    });
  }

  function loadVersionPanel() {
    if (!versionPanel) {
      versionPanel = document.createElement('div');
      versionPanel.className = 'editor-panel version-panel';
      versionPanel.innerHTML =
        '<div class="panel-header">' +
          '<h3>Version History</h3>' +
          '<button class="panel-close" title="Close">&times;</button>' +
        '</div>' +
        '<div class="panel-body">' +
          '<div class="version-loading">Loading...</div>' +
        '</div>';
      document.body.appendChild(versionPanel);

      versionPanel.querySelector('.panel-close').addEventListener('click', function() {
        versionPanel.classList.remove('visible');
      });
    }

    versionPanel.classList.add('visible');
    loadVersionsList();
  }

  function loadVersionsList() {
    var body = versionPanel.querySelector('.panel-body');
    body.innerHTML = '<div class="version-loading">Loading versions...</div>';

    api.listVersions().then(function(versions) {
      if (!versions || versions.length === 0) {
        body.innerHTML = '<div class="version-empty">No versions yet. Publish to create the first version.</div>';
        return;
      }
      var html = '<div class="version-timeline">';
      versions.forEach(function(v) {
        var isCurrent = v.is_current ? ' current' : '';
        var label = v.version_label || 'v?';
        var time = v.created_at || '';
        // Format time
        try {
          var d = new Date(time + 'Z');
          time = d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
        } catch(e) { time = time || ''; }
        html +=
          '<div class="version-item' + isCurrent + '">' +
            '<div class="version-dot"></div>' +
            '<div class="version-info">' +
              '<span class="version-label">' + label + '</span>' +
              (isCurrent ? '<span class="version-badge">Current</span>' : '') +
              '<span class="version-time">' + time + '</span>' +
            '</div>' +
            '<div class="version-actions">' +
              '<button class="version-preview-btn" data-id="' + v.id + '" title="Preview this version">\u25b6 Preview</button>' +
              (!isCurrent ? '<button class="version-restore-btn" data-id="' + v.id + '" title="Restore this version">\u21a9 Restore</button>' : '') +
            '</div>' +
          '</div>';
      });
      html += '</div>';
      body.innerHTML = html;

      // Bind preview buttons
      body.querySelectorAll('.version-preview-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
          var id = this.getAttribute('data-id');
          previewVersion(id);
        });
      });

      // Bind restore buttons
      body.querySelectorAll('.version-restore-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
          var id = this.getAttribute('data-id');
          restoreVersion(id);
        });
      });
    })
    .catch(function(err) {
      body.innerHTML = '<div class="version-error">Failed to load: ' + err + '</div>';
    });
  }

  function previewVersion(versionId) {
    var body = versionPanel.querySelector('.panel-body');
    body.innerHTML = '<div class="version-loading">Loading version data...</div>';

    api.getVersion(versionId).then(function(data) {
      if (!data) {
        body.innerHTML = '<div class="version-error">Version not found.</div>' +
          '<button class="version-back-btn">\u2190 Back</button>';
        body.querySelector('.version-back-btn').addEventListener('click', loadVersionsList);
        return;
      }

      var html =
        '<button class="version-back-btn">\u2190 Back to list</button>' +
        '<div class="version-detail">' +
          '<h4>' + (data.version_label || 'Version') + '</h4>' +
          '<table class="version-summary-table">' +
            '<tr><td>Created</td><td>' + (data.created_at || '-') + '</td></tr>' +
            '<tr><td>Token sections</td><td>' + Object.keys(data.snapshot_json || {}).length + '</td></tr>' +
            '<tr><td>Blocks</td><td>' + (data.blocks_json || []).length + '</td></tr>' +
          '</table>' +
          '<div class="version-detail-actions">' +
            '<button class="version-restore-btn" data-id="' + versionId + '">\u21a9 Restore this version</button>' +
          '</div>' +
        '</div>';

      body.innerHTML = html;

      body.querySelector('.version-back-btn').addEventListener('click', loadVersionsList);
      body.querySelector('.version-restore-btn').addEventListener('click', function() {
        restoreVersion(versionId);
      });
    })
    .catch(function(err) {
      body.innerHTML = '<div class="version-error">Error: ' + err + '</div>' +
        '<button class="version-back-btn">\u2190 Back</button>';
      body.querySelector('.version-back-btn').addEventListener('click', loadVersionsList);
    });
  }

  function restoreVersion(versionId) {
    if (!confirm('Restore this version? Any unsaved changes will be lost.')) return;

    var body = versionPanel.querySelector('.panel-body');
    body.innerHTML = '<div class="version-loading">Restoring...</div>';

    api.restoreVersion(versionId).then(function(data) {
      if (data && data.success) {
        showToast('Version restored! Reloading...', 'success');
        // Refresh the page to show restored draft
        setTimeout(function() { location.reload(); }, 1500);
      } else {
        showToast('Restore failed: ' + (data.error || 'Unknown error'), 'error');
        loadVersionsList();
      }
    })
    .catch(function(err) {
      showToast('Restore error: ' + err, 'error');
      loadVersionsList();
    });
  }

  function saveAll() {
    if (!state.dirty) return;
    saveBtn.textContent = 'Saving...';
    saveBtn.disabled = true;

    // For inline editors, the data is already saved per-field.
    // saveAll is a "flush" confirmation — resets dirty flag.
    state.dirty = false;
    state.changeCount = 0;
    state._notify();
    showToast('All changes saved', 'success');
    saveBtn.textContent = 'Save';
  }

  function publishAll() {
    if (state.dirty) {
      showToast('Please save changes before publishing', 'error');
      return;
    }

    var btn = toolbar.querySelector('.tb-publish');
    btn.textContent = 'Publishing...';
    btn.disabled = true;

    fetch('/admin/site-builder/publish', {
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + getToken() }
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data && data.success) {
        var versionLabel = (data.data && data.data.version && data.data.version.label) || '';
        var msg = 'Published successfully!';
        if (versionLabel) msg += ' (' + versionLabel + ')';
        showToast(msg, 'success');
        // Refresh version list if panel is open
        if (versionPanel && versionPanel.classList.contains('visible')) {
          loadVersionsList();
        }
      } else {
        showToast(data.error || 'Publish failed', 'error');
      }
    })
    .catch(function(err) {
      showToast('Publish failed: ' + err, 'error');
    })
    .finally(function() {
      btn.textContent = 'Publish';
      btn.disabled = false;
    });
  }

  function getToken() {
    var match = document.cookie.match(/(?:^|;\s*)sso_token=([^;]*)/);
    return match ? match[1] : '';
  }

  return { init: init };
})();
