/**
 * InlineEditor — double-click text editing with auto-save on blur.
 * Uses contenteditable="plaintext-only" to avoid HTML injection.
 */
var InlineEditor = (function() {

  var activeEl = null;   // currently editing element
  var oldValue = '';

  function init(stateManager, api) {
    var root = document.querySelector('.preview-content');
    if (!root) return;

    // Delegate dblclick on [data-editable="text"]
    root.addEventListener('dblclick', function(e) {
      var el = e.target.closest('[data-editable="text"]');
      if (!el || el.getAttribute('data-editable') !== 'text') return;
      if (el.classList.contains('editor-editing')) return;
      startEdit(el);
    });

    // Click-outside to save
    document.addEventListener('click', function(e) {
      if (!activeEl) return;
      var el = activeEl;
      if (el.contains(e.target)) return;
      saveEdit(el, stateManager, api);
    });

    // Escape key to cancel
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && activeEl) {
        cancelEdit(activeEl);
      }
    });
  }

  function startEdit(el) {
    if (activeEl) {
      saveEdit(activeEl, window.__editorState, window.__editorApi);
    }
    activeEl = el;
    oldValue = el.textContent.trim();

    // Make editable
    el.contentEditable = 'plaintext-only';
    el.classList.add('editor-editing');

    // Select all text
    var range = document.createRange();
    range.selectNodeContents(el);
    var sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);

    // Focus
    el.focus();
  }

  function saveEdit(el, stateManager, api) {
    if (!el || el !== activeEl) return;
    activeEl = null;

    el.contentEditable = 'false';
    el.classList.remove('editor-editing');

    var newValue = el.textContent.trim();
    if (newValue === oldValue) return;  // no change

    var blockId = el.getAttribute('data-block-id');
    var field = el.getAttribute('data-field');

    if (!blockId || !field) return;

    // Visual: saving state
    el.classList.add('editor-saving');

    var scope = isNaN(blockId) ? 'token' : 'block';
    api.updateBlock(blockId, field, newValue, scope)
      .then(function() {
        el.classList.remove('editor-saving');
        el.classList.add('editor-saved');
        setTimeout(function() { el.classList.remove('editor-saved'); }, 600);
        stateManager.push(blockId, field, oldValue, newValue, scope, el);
      })
      .catch(function(err) {
        el.classList.remove('editor-saving');
        el.classList.add('editor-error');
        el.textContent = oldValue;  // revert
        setTimeout(function() { el.classList.remove('editor-error'); }, 600);
        showToast(err || 'Save failed', 'error');
      });
  }

  function cancelEdit(el) {
    if (!el) return;
    el.contentEditable = 'false';
    el.classList.remove('editor-editing');
    el.textContent = oldValue;
    activeEl = null;
  }

  return { init: init };
})();
