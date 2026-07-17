/**
 * NavEditor — inline editing of navigation menu items.
 * Click pencil icon to edit title/url, add/delete items.
 */
var NavEditor = (function() {

  var activePopover = null;

  function init(stateManager, api) {
    var nav = document.querySelector('.navbar nav');
    if (!nav) return;

    // Add edit pencil to each nav item
    var links = nav.querySelectorAll('a[data-editable="nav-item"]');
    Array.prototype.forEach.call(links, function(a) {
      addPencil(a);
    });

    // Handle "Add menu item" click
    var addBtn = nav.querySelector('.editor-nav-add');
    if (addBtn) {
      addBtn.addEventListener('click', function(e) {
        e.preventDefault();
        addNavItem(stateManager, api, nav);
      });
    }

    // Delegate click on pencil
    nav.addEventListener('click', function(e) {
      var pencil = e.target.closest('.editor-nav-pencil');
      if (!pencil) return;
      e.preventDefault();
      var a = pencil.closest('a[data-editable="nav-item"]');
      if (a) showEditPopover(a, stateManager, api);
    });

    // Close popover on outside click
    document.addEventListener('click', function(e) {
      if (activePopover && !activePopover.contains(e.target)) {
        closePopover();
      }
    });
  }

  function addPencil(a) {
    var pencil = document.createElement('span');
    pencil.className = 'editor-nav-pencil';
    pencil.textContent = '\u270f';  // pencil icon
    pencil.style.cssText =
      'display:inline-block;margin-left:4px;font-size:12px;' +
      'cursor:pointer;opacity:0.3;transition:opacity 0.15s;';
    a.appendChild(pencil);

    a.addEventListener('mouseenter', function() { pencil.style.opacity = '1'; });
    a.addEventListener('mouseleave', function() { pencil.style.opacity = '0.3'; });
  }

  function showEditPopover(a, stateManager, api) {
    closePopover();

    var rect = a.getBoundingClientRect();
    var popover = document.createElement('div');
    popover.className = 'editor-nav-popover';
    popover.style.top = (rect.bottom + 4) + 'px';
    popover.style.left = Math.min(rect.left, window.innerWidth - 240) + 'px';

    var idx = a.getAttribute('data-nav-index');
    var title = a.textContent.trim();
    var href = a.getAttribute('href') || '#';

    popover.innerHTML =
      '<label>Title</label><input class="nav-title" value="' + escHtml(title) + '"/>' +
      '<label>URL</label><input class="nav-url" value="' + escHtml(href) + '"/>' +
      '<div class="nav-pop-actions">' +
        '<button class="btn-del">Delete</button>' +
      '</div>';

    document.body.appendChild(popover);
    activePopover = popover;

    // Focus title input
    popover.querySelector('.nav-title').focus();

    // Save on blur
    function save() {
      var newTitle = sanitizeInput(popover.querySelector('.nav-title').value, 50);
      var newUrl = sanitizeUrl(popover.querySelector('.nav-url').value);
      if (newTitle && newTitle !== title) {
        a.textContent = newTitle;
        addPencil(a);
        saveNavItem(idx, 'title', newTitle, api);
      }
      if (newUrl && newUrl !== href) {
        a.setAttribute('href', newUrl);
        saveNavItem(idx, 'url', newUrl, api);
      }
    }

    // Blur save
    var inputs = popover.querySelectorAll('input');
    Array.prototype.forEach.call(inputs, function(inp) {
      inp.addEventListener('blur', function() {
        setTimeout(save, 200);
      });
    });

    // Delete
    popover.querySelector('.btn-del').addEventListener('click', function() {
      a.parentNode.removeChild(a);
      deleteNavItem(idx, api);
      closePopover();
    });
  }

  function saveNavItem(idx, field, value, api) {
    // Read current nav items from draft_tokens (injected on page)
    var navData = window.__draftNavItems || [];
    if (navData[idx]) {
      navData[idx][field] = value;
    }
    api.updateTokens('navigation', { items: navData }).catch(function(err) {
      showToast('Nav save failed: ' + err, 'error');
    });
  }

  function deleteNavItem(idx, api) {
    var navData = window.__draftNavItems || [];
    navData.splice(idx, 1);
    api.updateTokens('navigation', { items: navData }).catch(function(err) {
      showToast('Nav delete failed: ' + err, 'error');
    });
  }

  function addNavItem(stateManager, api, nav) {
    var navData = window.__draftNavItems || [];
    var newItem = { id: Date.now(), title: 'New Page', url: '#', icon: '', target: '_self' };
    navData.push(newItem);

    api.updateTokens('navigation', { items: navData })
      .then(function() {
        // Reload to show new item
        showToast('Menu item added', 'success');
        setTimeout(function() { location.reload(); }, 600);
      })
      .catch(function(err) {
        showToast('Add failed: ' + err, 'error');
      });
  }

  function closePopover() {
    if (activePopover && activePopover.parentNode) {
      activePopover.parentNode.removeChild(activePopover);
    }
    activePopover = null;
  }

  function escHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  function sanitizeInput(s, maxLen) {
    return String(s).trim().replace(/[<>"']/g, '').slice(0, maxLen || 100);
  }

  function sanitizeUrl(s) {
    s = String(s).trim();
    // Only allow http, https, mailto, tel, and relative URLs
    if (/^(https?:\/\/|mailto:|tel:|\/|#)/.test(s)) {
      return s;
    }
    return '/';
  }

  return { init: init };
})();
