/**
 * ColorPalette — color editing panel for brand colors.
 * Lists all 10 color variables as swatches with input[type=color].
 * Includes preset theme buttons.
 */
var ColorPalette = (function() {

  var panel = null;
  var visible = false;
  var currentTokens = {};

  // Map CSS var -> label -> draft_tokens path
  var COLOR_MAP = [
    { css: '--color-primary',      label: 'Primary',      scope: 'colors', key: 'primary' },
    { css: '--color-secondary',    label: 'Secondary',    scope: 'colors', key: 'secondary' },
    { css: '--color-accent',       label: 'Accent',       scope: 'colors', key: 'accent' },
    { css: '--color-background',   label: 'Background',   scope: 'colors', key: 'background' },
    { css: '--color-surface',      label: 'Surface',      scope: 'colors', key: 'surface' },
    { css: '--color-text-primary', label: 'Text Primary', scope: 'colors', key: 'text_primary' },
    { css: '--color-text-secondary', label: 'Text Secondary', scope: 'colors', key: 'text_secondary' },
    { css: '--color-border',       label: 'Border',       scope: 'colors', key: 'border' },
    { css: '--color-error',        label: 'Error',        scope: 'colors', key: 'error' },
    { css: '--color-success',      label: 'Success',      scope: 'colors', key: 'success' },
  ];

  // Preset themes
  var PRESETS = {
    'Deep Blue': {
      '--color-primary': '#2563eb', '--color-secondary': '#7c3aed',
      '--color-accent': '#f59e0b', '--color-background': '#ffffff',
      '--color-surface': '#f8fafc', '--color-text-primary': '#0f172a',
      '--color-text-secondary': '#64748b', '--color-border': '#e2e8f0',
    },
    'Forest Green': {
      '--color-primary': '#059669', '--color-secondary': '#10b981',
      '--color-accent': '#f97316', '--color-background': '#ffffff',
      '--color-surface': '#f0fdf4', '--color-text-primary': '#0f172a',
      '--color-text-secondary': '#6b7280', '--color-border': '#dcfce7',
    },
    'Sunset Orange': {
      '--color-primary': '#ea580c', '--color-secondary': '#d97706',
      '--color-accent': '#eab308', '--color-background': '#fffcf5',
      '--color-surface': '#fff7ed', '--color-text-primary': '#1c1917',
      '--color-text-secondary': '#78716c', '--color-border': '#fed7aa',
    },
    'Minimal Gray': {
      '--color-primary': '#6b7280', '--color-secondary': '#9ca3af',
      '--color-accent': '#f59e0b', '--color-background': '#ffffff',
      '--color-surface': '#f9fafb', '--color-text-primary': '#111827',
      '--color-text-secondary': '#6b7280', '--color-border': '#e5e7eb',
    },
    'Dark Mode': {
      '--color-primary': '#818cf8', '--color-secondary': '#a78bfa',
      '--color-accent': '#fbbf24', '--color-background': '#0f172a',
      '--color-surface': '#1e293b', '--color-text-primary': '#f1f5f9',
      '--color-text-secondary': '#94a3b8', '--color-border': '#334155',
    },
  };

  function init(stateManager, api) {
    // Build panel DOM
    panel = document.createElement('div');
    panel.className = 'editor-panel';
    panel.id = 'editor-color-panel';

    var html = '<h3>Color Palette</h3><div class="color-grid">';
    COLOR_MAP.forEach(function(c) {
      html +=
        '<div class="color-item" data-css="' + c.css + '" data-scope="' + c.scope + '" data-key="' + c.key + '">' +
          '<div class="color-swatch" style="background:var(' + c.css + ')"></div>' +
          '<span class="color-label">' + c.label + '</span>' +
          '<span class="color-value"></span>' +
        '</div>';
    });
    html += '</div><div class="preset-row"><span class="preset-label">Presets:</span>';

    for (var name in PRESETS) {
      html += '<button class="preset-btn" data-preset="' + name + '">' + name + '</button>';
    }
    html += '</div>';

    panel.innerHTML = html;
    document.body.appendChild(panel);

    // Read current CSS values
    updateValueLabels();

    // Bind: click swatch -> open color picker
    var items = panel.querySelectorAll('.color-item');
    Array.prototype.forEach.call(items, function(item) {
      item.addEventListener('click', function() {
        var cssVar = this.getAttribute('data-css');
        var current = getComputedStyle(document.documentElement).getPropertyValue(cssVar).trim();
        var input = document.createElement('input');
        input.type = 'color';
        input.value = rgbToHex(current) || '#6366f1';
        input.addEventListener('input', function() {
          applyColor(cssVar, this.value);
        });
        input.addEventListener('change', function() {
          saveColor(cssVar, this.value, api);
        });
        input.click();
      });
    });

    // Bind: preset buttons
    var presets = panel.querySelectorAll('.preset-btn');
    Array.prototype.forEach.call(presets, function(btn) {
      btn.addEventListener('click', function() {
        var name = this.getAttribute('data-preset');
        var colors = PRESETS[name];
        if (!colors) return;
        for (var cssVar in colors) {
          applyColor(cssVar, colors[cssVar]);
        }
        // Save all colors
        var data = {};
        COLOR_MAP.forEach(function(c) {
          data[c.key] = getComputedStyle(document.documentElement)
            .getPropertyValue(c.css).trim();
        });
        api.updateTokens('colors', data).catch(function(err) {
          showToast('Preset save failed: ' + err, 'error');
        });
        updateValueLabels();
        showToast('Applied preset: ' + name, 'success');
      });
    });

    // Listen for toggle events from toolbar
    document.addEventListener('editor-toggle-panel', function(e) {
      if (e.detail && e.detail.panel === 'colors') {
        toggle();
      }
    });
  }

  function toggle() {
    visible = !visible;
    panel.classList.toggle('visible', visible);
    if (visible) {
      updateValueLabels();
      // Close spacing panel if open
      var sp = document.getElementById('editor-spacing-panel');
      if (sp) sp.classList.remove('visible');
    }
  }

  function updateValueLabels() {
    var items = panel.querySelectorAll('.color-item');
    Array.prototype.forEach.call(items, function(item) {
      var cssVar = item.getAttribute('data-css');
      var val = getComputedStyle(document.documentElement).getPropertyValue(cssVar).trim();
      item.querySelector('.color-swatch').style.background = val || 'transparent';
      var vLabel = item.querySelector('.color-value');
      if (vLabel) vLabel.textContent = val;
    });
  }

  function applyColor(cssVar, hex) {
    document.documentElement.style.setProperty(cssVar, hex);
    // Update swatch in panel
    var item = panel.querySelector('[data-css="' + cssVar + '"]');
    if (item) {
      item.querySelector('.color-swatch').style.background = hex;
      var vLabel = item.querySelector('.color-value');
      if (vLabel) vLabel.textContent = hex;
    }
  }

  function saveColor(cssVar, hex, api) {
    // Find the matching token key
    for (var i = 0; i < COLOR_MAP.length; i++) {
      if (COLOR_MAP[i].css === cssVar) {
        var data = {};
        data[COLOR_MAP[i].key] = hex;
        api.updateTokens('colors', data).catch(function(err) {
          showToast('Color save failed: ' + err, 'error');
        });
        break;
      }
    }
  }

  function rgbToHex(rgb) {
    if (!rgb) return null;
    if (rgb.startsWith('#')) return rgb;
    var m = rgb.match(/\d+/g);
    if (!m || m.length < 3) return null;
    return '#' + [0,1,2].map(function(i) {
      var v = parseInt(m[i]);
      return (v < 16 ? '0' : '') + v.toString(16);
    }).join('');
  }

  return { init: init };
})();
