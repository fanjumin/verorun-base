/**
 * BlockActions — drag-sort, drag-to-add, hide/show, delete for sections.
 * Uses native HTML5 Drag & Drop (no external library).
 */
var BlockActions = (function() {

  var draggedEl = null;
  var dragPlaceholder = null;
  var dropIndicator = null;
  var addPanelVisible = false;
  var addPanel = null;
  var _pendingOrder = null;        // debounced order POST
  var _pendingOrderTimer = null;

  function init(stateManager, api) {
    initDragSort(stateManager, api);
    initSectionActions(stateManager, api);
    initAddPanel(api);
  }

  /* ── Drag Sort ────────────────────────────────────── */

  function initDragSort(state, api) {
    var sections = document.querySelectorAll('[data-editable="section"]');
    Array.prototype.forEach.call(sections, function(s) {
      s.draggable = true;
      s.classList.add('editor-draggable');
      s.addEventListener('dragstart', onDragStart);
      s.addEventListener('dragend', onDragEnd);
      s.addEventListener('dragover', onDragOver);
      s.addEventListener('dragenter', onDragEnter);
      s.addEventListener('dragleave', onDragLeave);
      s.addEventListener('drop', onDrop.bind(null, state, api));
    });
  }

  function onDragStart(e) {
    draggedEl = this;
    this.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', this.id || '');
    // Create placeholder
    dragPlaceholder = document.createElement('div');
    dragPlaceholder.className = 'drag-placeholder';
    this.parentNode.insertBefore(dragPlaceholder, this.nextSibling);
  }

  function onDragEnd() {
    this.classList.remove('dragging');
    if (dragPlaceholder && dragPlaceholder.parentNode) {
      dragPlaceholder.parentNode.removeChild(dragPlaceholder);
    }
    dragPlaceholder = null;
    draggedEl = null;
    // Remove drag-over from all
    var all = document.querySelectorAll('[data-editable="section"].drag-over');
    Array.prototype.forEach.call(all, function(el) { el.classList.remove('drag-over'); });
  }

  function onDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  }

  function onDragEnter(e) {
    e.preventDefault();
    if (this !== draggedEl) {
      this.classList.add('drag-over');
    }
  }

  function onDragLeave() {
    this.classList.remove('drag-over');
  }

  function onDrop(state, api, e) {
    e.preventDefault();
    var target = e.currentTarget;
    if (!target) return;
    target.classList.remove('drag-over');
    if (!draggedEl || draggedEl === target) return;

    var parent = target.parentNode;
    var siblings = Array.prototype.filter.call(parent.children, function(c) {
      return c.getAttribute('data-editable') === 'section';
    });

    var fromIdx = siblings.indexOf(draggedEl);
    var toIdx = siblings.indexOf(target);

    if (fromIdx === -1 || toIdx === -1) return;

    // Remove placeholder before reordering to keep DOM clean
    if (dragPlaceholder && dragPlaceholder.parentNode) {
      dragPlaceholder.parentNode.removeChild(dragPlaceholder);
      dragPlaceholder = null;
    }

    // Reorder DOM
    if (fromIdx < toIdx) {
      parent.insertBefore(draggedEl, target.nextSibling);
    } else {
      parent.insertBefore(draggedEl, target);
    }

    // Collect new order after DOM settles
    setTimeout(function() {
      var newSiblings = Array.prototype.filter.call(parent.children, function(c) {
        return c.getAttribute('data-editable') === 'section';
      });
      var order = newSiblings.map(function(el, idx) {
        var page = el.getAttribute('data-page') || 'home';
        return { block_id: page, position: idx };
      });
      // For cms_blocks-based sections, need block IDs
      var blockOrder = [];
      newSiblings.forEach(function(el) {
        var page = el.getAttribute('data-page') || 'home';
        var cards = el.querySelectorAll('[data-editable="card"]');
        Array.prototype.forEach.call(cards, function(card) {
          var bid = card.getAttribute('data-block-id');
          if (bid && !isNaN(bid)) {
            blockOrder.push({ block_id: parseInt(bid), position: blockOrder.length });
          }
        });
      });
      if (blockOrder.length > 0) {
        debouncedSaveOrder(blockOrder, api);
      }
    }, 100);
  }

  function debouncedSaveOrder(blockOrder, api) {
    // Cancel any pending save
    _pendingOrder = blockOrder;
    if (_pendingOrderTimer) {
      clearTimeout(_pendingOrderTimer);
    }
    _pendingOrderTimer = setTimeout(function() {
      var order = _pendingOrder;
      _pendingOrder = null;
      api.updateBlockOrder(order).catch(function(err) {
        showToast('Sort save failed: ' + err, 'error');
      });
    }, 400);
  }

  function initSectionActions(state, api) {
    var sections = document.querySelectorAll('[data-editable="section"]');
    Array.prototype.forEach.call(sections, function(s) {
      var actions = document.createElement('div');
      actions.className = 'editor-section-actions';
      actions.innerHTML =
        '<div class="action-bar">' +
          '<button class="move-up" title="Move up">\u2191</button>' +
          '<button class="move-down" title="Move down">\u2193</button>' +
          '<button class="toggle-vis" title="Toggle visibility">\u2b1c</button>' +
          '<button class="delete danger" title="Delete section">\u2715</button>' +
        '</div>';
      s.appendChild(actions);

      actions.querySelector('.move-up').addEventListener('click', function(e) {
        e.stopPropagation();
        moveSection(s, -1, api);
      });
      actions.querySelector('.move-down').addEventListener('click', function(e) {
        e.stopPropagation();
        moveSection(s, 1, api);
      });
      actions.querySelector('.toggle-vis').addEventListener('click', function(e) {
        e.stopPropagation();
        toggleVisibility(s, api);
      });
      actions.querySelector('.delete').addEventListener('click', function(e) {
        e.stopPropagation();
        deleteSection(s, api);
      });
    });
  }

  function moveSection(el, direction, api) {
    var parent = el.parentNode;
    var siblings = Array.prototype.filter.call(parent.children, function(c) {
      return c.getAttribute('data-editable') === 'section';
    });
    var idx = siblings.indexOf(el);
    var target = idx + direction;
    if (target < 0 || target >= siblings.length) return;

    if (direction < 0) {
      parent.insertBefore(el, siblings[target]);
    } else {
      parent.insertBefore(el, siblings[target].nextSibling);
    }

    // Rebuild order
    setTimeout(function() {
      var newSiblings = Array.prototype.filter.call(parent.children, function(c) {
        return c.getAttribute('data-editable') === 'section';
      });
      var blockOrder = [];
      newSiblings.forEach(function(sec) {
        var cards = sec.querySelectorAll('[data-editable="card"]');
        Array.prototype.forEach.call(cards, function(card) {
          var bid = card.getAttribute('data-block-id');
          if (bid && !isNaN(bid)) {
            blockOrder.push({ block_id: parseInt(bid), position: blockOrder.length });
          }
        });
      });
      if (blockOrder.length > 0) {
        debouncedSaveOrder(blockOrder, api);
      }
    }, 100);
  }

  function toggleVisibility(el, api) {
    var cards = el.querySelectorAll('[data-editable="card"]');
    Array.prototype.forEach.call(cards, function(card) {
      var bid = card.getAttribute('data-block-id');
      if (bid && !isNaN(bid)) {
        if (card.classList.contains('editor-hidden')) {
          card.classList.remove('editor-hidden');
          api.updateBlock(bid, 'extra_json', { is_visible: true }, 'block').catch(function(){});
        } else {
          card.classList.add('editor-hidden');
          api.updateBlock(bid, 'extra_json', { is_visible: false }, 'block').catch(function(){});
        }
      }
    });
  }

  function deleteSection(el, api) {
    if (!confirm('Delete this section?')) return;

    var cards = el.querySelectorAll('[data-editable="card"]');
    var promises = [];
    Array.prototype.forEach.call(cards, function(card) {
      var bid = card.getAttribute('data-block-id');
      if (bid && !isNaN(bid)) {
        promises.push(api.deleteBlock(bid));
      }
    });

    Promise.all(promises)
      .then(function() {
        el.parentNode.removeChild(el);
        showToast('Section deleted', 'info');
      })
      .catch(function(err) {
        showToast('Delete failed: ' + err, 'error');
      });
  }

  /* ── Drag-to-Add Panel ────────────────────────────── */

  function initAddPanel(api) {
    // Create panel
    addPanel = document.createElement('div');
    addPanel.className = 'editor-add-panel';
    addPanel.innerHTML =
      '<h4>Add Block</h4>' +
      '<div class="add-block-item" data-block-type="hero" data-title="Hero" data-icon="\u{1f3e0}">' +
        '<span class="abi-icon">\u{1f3e0}</span><span class="abi-label">Hero</span>' +
      '</div>' +
      '<div class="add-block-item" data-block-type="features" data-title="Features" data-icon="\u2728">' +
        '<span class="abi-icon">\u2728</span><span class="abi-label">Features</span>' +
      '</div>' +
      '<div class="add-block-item" data-block-type="cta" data-title="CTA" data-icon="\u{1f514}">' +
        '<span class="abi-icon">\u{1f514}</span><span class="abi-label">CTA</span>' +
      '</div>' +
      '<div class="add-block-item" data-block-type="faq" data-title="FAQ" data-icon="\u2753">' +
        '<span class="abi-icon">\u2753</span><span class="abi-label">FAQ</span>' +
      '</div>' +
      '<div class="add-block-item" data-block-type="contact" data-title="Contact" data-icon="\u{1f4e7}">' +
        '<span class="abi-icon">\u{1f4e7}</span><span class="abi-label">Contact</span>' +
      '</div>';

    document.body.appendChild(addPanel);

    // Make items draggable
    var items = addPanel.querySelectorAll('.add-block-item');
    Array.prototype.forEach.call(items, function(item) {
      item.draggable = true;
      item.addEventListener('dragstart', function(e) {
        e.dataTransfer.setData('application/x-block-type', JSON.stringify({
          type: this.getAttribute('data-block-type'),
          title: this.getAttribute('data-title'),
          icon: this.getAttribute('data-icon')
        }));
        e.dataTransfer.effectAllowed = 'copy';
      });
    });

    // Make sections droppable for adding
    var sections = document.querySelectorAll('[data-editable="section"]');
    Array.prototype.forEach.call(sections, function(s) {
      s.addEventListener('dragover', function(e) {
        // Only allow drop if coming from add panel (type text/plain won't match for copy)
        // Accept if we have our custom type
        if (e.dataTransfer.types.indexOf('application/x-block-type') !== -1) {
          e.preventDefault();
          e.dataTransfer.dropEffect = 'copy';
          this.classList.add('editor-drop-zone');
        } else {
          // Allow sort (handled above)
        }
      });
      s.addEventListener('dragleave', function() {
        this.classList.remove('editor-drop-zone');
      });
      s.addEventListener('drop', function(e) {
        this.classList.remove('editor-drop-zone');
        var raw = e.dataTransfer.getData('application/x-block-type');
        if (!raw) return;
        e.preventDefault();

        try {
          var data = JSON.parse(raw);
          var page = this.getAttribute('data-page') || 'home';
          var title = data.title || 'New Block';
          var blockType = data.type || 'feature-card';
          var icon = data.icon || '';

          api.addBlock(page, 0, blockType, title, '', icon)
            .then(function(resp) {
              showToast('Block added: ' + title, 'success');
              // Reload preview to show new block
              setTimeout(function() { location.reload(); }, 800);
            })
            .catch(function(err) {
              showToast('Add failed: ' + err, 'error');
            });
        } catch(e) { /* ignore */ }
      });
    });
  }

  return { init: init };
})();
