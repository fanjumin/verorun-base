/**
 * EditStateManager — undo/redo stack, dirty flag, change counter.
 * Max 20 undo steps. Supports Ctrl+Z / Ctrl+Shift+Z.
 */
var EditStateManager = (function() {

  var MAX_STACK = 20;

  function EditStateManager() {
    this.undoStack = [];   // [{blockId, field, oldValue, newValue, scope, domRef}]
    this.redoStack = [];
    this.dirty = false;
    this.changeCount = 0;
    this.listeners = [];   // [{onChange}]
  }

  /** Subscribe to state changes */
  EditStateManager.prototype.onChange = function(fn) {
    this.listeners.push(fn);
  };

  /** Notify all listeners */
  EditStateManager.prototype._notify = function() {
    for (var i = 0; i < this.listeners.length; i++) {
      this.listeners[i](this);
    }
  };

  /** Push an operation onto the undo stack */
  EditStateManager.prototype.push = function(blockId, field, oldValue, newValue, scope, domRef) {
    this.undoStack.push({
      blockId: blockId, field: field,
      oldValue: oldValue, newValue: newValue,
      scope: scope || 'block', domRef: domRef || null
    });
    if (this.undoStack.length > MAX_STACK) {
      this.undoStack.shift();
    }
    this.redoStack = [];  // new op clears redo
    this.dirty = true;
    this.changeCount++;
    this._notify();
  };

  /** Undo last operation */
  EditStateManager.prototype.undo = function() {
    var op = this.undoStack.pop();
    if (!op) return;

    // POST to restore on server first, then update DOM on success
    var self = this;
    this._restoreServer(op.blockId, op.field, op.oldValue, op.scope)
      .then(function() {
        // Restore DOM after server confirms
        if (op.domRef && op.domRef.parentNode) {
          op.domRef.textContent = op.oldValue;
        }
        self.redoStack.push(op);
        self.changeCount = Math.max(0, self.changeCount - 1);
        if (self.undoStack.length === 0) self.dirty = false;
        self._notify();
      })
      .catch(function(err) {
        // Network failure — push back to undo stack and warn
        self.undoStack.push(op);
        showToast('Undo failed: ' + (err || 'network error'), 'error');
      });
  };

  /** Redo last undone operation */
  EditStateManager.prototype.redo = function() {
    var op = this.redoStack.pop();
    if (!op) return;

    var self = this;
    this._restoreServer(op.blockId, op.field, op.newValue, op.scope)
      .then(function() {
        if (op.domRef && op.domRef.parentNode) {
          op.domRef.textContent = op.newValue;
        }
        self.undoStack.push(op);
        self.changeCount++;
        self.dirty = true;
        self._notify();
      })
      .catch(function(err) {
        self.redoStack.push(op);
        showToast('Redo failed: ' + (err || 'network error'), 'error');
      });
  };

  /** Internal: POST to restore value (returns a promise) */
  EditStateManager.prototype._restoreServer = function(blockId, field, value, scope) {
    var api = window.__editorApi;
    if (!api) return Promise.reject('API not available');
    if (scope === 'token') {
      return api.updateBlock(blockId, field, value, 'token');
    } else {
      return api.updateBlock(blockId, field, value, 'block');
    }
  };

  return EditStateManager;
})();
