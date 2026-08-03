/**
 * EditorInit — main entry point for the Preview-as-Editor.
 * Initializes all modules, wires up keyboard shortcuts, beforeunload guard.
 */

(function() {

  'use strict';

  // Wait for DOM
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

  function boot() {
    // ── Read tokens from the CSS variable script ──
    var tokenScript = document.querySelector('script:not([src])');
    var tokens = {};
    try {
      // Re-read from CSS var initializer context
      var root = document.documentElement;
      var colorProps = [
        '--color-primary','--color-secondary','--color-accent',
        '--color-background','--color-surface',
        '--color-text-primary','--color-text-secondary','--color-border'
      ];
      colorProps.forEach(function(p) {
        var val = getComputedStyle(root).getPropertyValue(p).trim();
        if (val) tokens[p] = val;
      });
    } catch(e) {}

    // ── Set up nav data for NavEditor ──
    try {
      var navEl = document.querySelector('.navbar nav');
      if (navEl) {
        var links = navEl.querySelectorAll('a[data-editable="nav-item"]');
        var navItems = [];
        Array.prototype.forEach.call(links, function(a) {
          navItems.push({
            id: navItems.length + 1,
            title: a.textContent.trim(),
            url: a.getAttribute('href') || '#',
            icon: '',
            target: '_self'
          });
        });
        window.__draftNavItems = navItems;
      }
    } catch(e) {}

    // ── Instantiate core modules ──
    var state = new EditStateManager();
    var api = new ApiClient();

    // Expose for cross-module access (undo/redo uses these)
    window.__editorState = state;
    window.__editorApi = api;

    // ── Bootstrap all editors ──
    EditorToolbar.init(state, api);
    InlineEditor.init(state, api);
    BlockActions.init(state, api);
    NavEditor.init(state, api);
    ColorPalette.init(state, api);
    SpacingSlider.init(state, api);

    // ── Keyboard shortcuts ──
    document.addEventListener('keydown', function(e) {
      if (e.ctrlKey && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        state.undo();
      }
      if (e.ctrlKey && e.key === 'z' && e.shiftKey) {
        e.preventDefault();
        state.redo();
      }
      if (e.key === 'Escape') {
        closeAllPanels();
      }
    });

    // ── Beforeunload guard ──
    window.addEventListener('beforeunload', function(e) {
      if (state.dirty) {
        e.preventDefault();
        e.returnValue = 'You have unsaved changes. Leave anyway?';
      }
    });
  }

  function closeAllPanels() {
    document.querySelectorAll('.editor-panel.visible').forEach(function(p) {
      p.classList.remove('visible');
    });
  }

})();


/**
 * Global: showToast — display a temporary notification.
 * Used by all editor modules.
 */
function showToast(message, type) {
  type = type || 'info';
  var existing = document.querySelector('.editor-toast');
  if (existing) {
    existing.parentNode.removeChild(existing);
  }
  var toast = document.createElement('div');
  toast.className = 'editor-toast ' + type;
  toast.textContent = message;
  document.body.appendChild(toast);

  // Force reflow
  toast.offsetHeight;
  toast.classList.add('visible');

  setTimeout(function() {
    toast.classList.remove('visible');
    setTimeout(function() {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 300);
  }, 2500);
}
