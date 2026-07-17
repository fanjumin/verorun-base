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
        showToast('Published successfully!', 'success');
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
