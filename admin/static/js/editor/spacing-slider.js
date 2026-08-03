/**
 * SpacingSlider — spacing & typography adjustment panel.
 * Uses range sliders to control section gap, card padding, and body font size.
 */
var SpacingSlider = (function() {

  var panel = null;
  var visible = false;

  var SLIDERS = [
    { css: '--section-gap',  label: 'Section Gap',    min: 24, max: 120, step: 4, unit: 'px', tokenKey: 'section_gap' },
    { css: '--card-padding', label: 'Card Padding',   min: 8,  max: 48,  step: 4, unit: 'px', tokenKey: 'card_padding' },
    { css: '--body-size',    label: 'Body Font Size', min: 12, max: 24,  step: 1, unit: 'px', tokenKey: 'body_size' },
    { css: '--h1-size',      label: 'Heading H1',     min: 20, max: 64,  step: 2, unit: 'px', tokenKey: 'h1_size' },
  ];

  function init(stateManager, api) {
    panel = document.createElement('div');
    panel.className = 'editor-panel';
    panel.id = 'editor-spacing-panel';

    var html = '<h3>Spacing & Typography</h3><div class="spacing-list">';

    SLIDERS.forEach(function(s) {
      var current = parseInt(getComputedStyle(document.documentElement)
        .getPropertyValue(s.css).trim()) || s.min;
      html +=
        '<div class="spacing-item" data-css="' + s.css + '" data-token="' + s.tokenKey + '">' +
          '<label><span>' + s.label + '</span><span class="sp-val">' + current + s.unit + '</span></label>' +
          '<input type="range" min="' + s.min + '" max="' + s.max + '" step="' + s.step + '" value="' + current + '"/>' +
        '</div>';
    });

    html += '</div>';
    panel.innerHTML = html;
    document.body.appendChild(panel);

    // Bind sliders
    var items = panel.querySelectorAll('.spacing-item');
    Array.prototype.forEach.call(items, function(item) {
      var input = item.querySelector('input[type="range"]');
      var cssVar = item.getAttribute('data-css');
      var tokenKey = item.getAttribute('data-token');
      var unit = cssVar === '--body-size' || cssVar === '--section-gap' || cssVar === '--card-padding' || cssVar === '--h1-size' ? 'px' : 'px';

      input.addEventListener('input', function() {
        var val = this.value + unit;
        document.documentElement.style.setProperty(cssVar, val);
        item.querySelector('.sp-val').textContent = val;
      });

      input.addEventListener('change', function() {
        var val = this.value + unit;
        var scope = (cssVar === '--section-gap' || cssVar === '--card-padding') ? 'spacing' : 'typography';
        var data = {};
        data[tokenKey] = val;
        api.updateTokens(scope, data).catch(function(err) {
          showToast('Save failed: ' + err, 'error');
        });
      });
    });

    // Listen for toggle events from toolbar
    document.addEventListener('editor-toggle-panel', function(e) {
      if (e.detail && e.detail.panel === 'spacing') {
        toggle();
      }
    });
  }

  function toggle() {
    visible = !visible;
    panel.classList.toggle('visible', visible);
    if (visible) {
      // Close color panel if open
      var cp = document.getElementById('editor-color-panel');
      if (cp) cp.classList.remove('visible');
    }
  }

  return { init: init };
})();
