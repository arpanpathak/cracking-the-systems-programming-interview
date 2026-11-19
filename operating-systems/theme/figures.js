// 1. Shows the dark variant of each figure in the dark themes, and the light
//    variant in the light themes and in print.
// 2. Transforms consecutive C++20 and Rust 2024 listing blocks into independent
//    Material Design tabbed code cards (with optional per-card desktop split view).
(function () {
  var DARK_THEMES = ['coal', 'navy', 'ayu'];

  function isDark() {
    var classes = document.documentElement.classList;
    return DARK_THEMES.some(function (name) { return classes.contains(name); });
  }

  function applyFigures(forceLight) {
    var dark = !forceLight && isDark();
    document.querySelectorAll('img[src*="figures/"]').forEach(function (img) {
      var current = img.getAttribute('src');
      var light = current.replace('figures/dark/', 'figures/');
      var wanted = dark ? light.replace('figures/', 'figures/dark/') : light;
      if (wanted !== current) img.setAttribute('src', wanted);
    });
  }

  function isListingHeader(el) {
    if (!el || el.tagName !== 'P') return false;
    var strong = el.querySelector('strong:first-child');
    if (!strong) return false;
    return /^Listing\s+\d+/i.test(strong.textContent.trim());
  }

  function isOutputHeader(el) {
    if (!el || el.tagName !== 'P') return false;
    var strong = el.querySelector('strong:first-child');
    if (!strong) return false;
    return /^Output\s+\d+/i.test(strong.textContent.trim());
  }

  function getPreLang(el) {
    if (!el || el.tagName !== 'PRE') return null;
    var code = el.querySelector('code');
    if (!code) return null;
    if (code.classList.contains('language-cpp') || code.classList.contains('cpp')) return 'cpp';
    if (code.classList.contains('language-rust') || code.classList.contains('rust')) return 'rust';
    return 'other';
  }

  function collectUnit(children, startIdx) {
    if (!isListingHeader(children[startIdx])) return null;
    var nextEl = children[startIdx + 1];
    var lang = getPreLang(nextEl);
    if (lang !== 'cpp' && lang !== 'rust') return null;

    var nodes = [children[startIdx], nextEl];
    var idx = startIdx + 2;

    while (idx < children.length) {
      if (isOutputHeader(children[idx]) && children[idx + 1] && children[idx + 1].tagName === 'PRE') {
        nodes.push(children[idx], children[idx + 1]);
        idx += 2;
      } else if (isListingHeader(children[idx]) && getPreLang(children[idx + 1]) === lang) {
        nodes.push(children[idx], children[idx + 1]);
        idx += 2;
      } else {
        break;
      }
    }

    return { lang: lang, nodes: nodes, nextIndex: idx };
  }

  function extractShortTitle(nodes, fallback) {
    var firstStrong = nodes[0] && nodes[0].querySelector('strong');
    if (!firstStrong) return fallback;
    var raw = firstStrong.textContent.trim();
    var m = raw.match(/^(Listing\s+[\d-]+[a-z]?)/i);
    return m ? m[1] : fallback;
  }

  // Updates ONLY the clicked card — never mutates other cards on the page.
  function activateCardMode(card, mode) {
    card.classList.toggle('is-split', mode === 'split');

    card.querySelectorAll('.md-code-tab').forEach(function (btn) {
      var active = btn.getAttribute('data-mode') === mode;
      btn.classList.toggle('active', active);
      btn.setAttribute('aria-selected', active ? 'true' : 'false');
    });

    card.querySelectorAll('.md-code-panel').forEach(function (panel) {
      var lang = panel.getAttribute('data-lang');
      var visible = mode === 'split' || lang === mode;
      panel.classList.toggle('active', visible);
    });
  }

  function initMaterialCodeTabs() {
    var main = document.querySelector('.content main');
    if (!main) return;

    var children = Array.prototype.slice.call(main.children);
    var i = 0;

    while (i < children.length) {
      var unit1 = collectUnit(children, i);
      if (unit1 && unit1.lang === 'cpp') {
        var unit2 = collectUnit(children, unit1.nextIndex);
        if (unit2 && unit2.lang === 'rust') {
          var card = document.createElement('div');
          card.className = 'md-code-tabs';

          var bar = document.createElement('div');
          bar.className = 'md-code-tabs-bar';
          bar.setAttribute('role', 'tablist');

          var cppListingId = extractShortTitle(unit1.nodes, 'C++20');
          var rustListingId = extractShortTitle(unit2.nodes, 'Rust 2024');

          var btnCpp = document.createElement('button');
          btnCpp.type = 'button';
          btnCpp.className = 'md-code-tab active';
          btnCpp.setAttribute('data-mode', 'cpp');
          btnCpp.setAttribute('role', 'tab');
          btnCpp.setAttribute('aria-selected', 'true');
          btnCpp.innerHTML =
            '<span class="md-lang-chip cpp">C++20</span>' +
            '<span class="md-tab-title">' + cppListingId + '</span>';

          var btnRust = document.createElement('button');
          btnRust.type = 'button';
          btnRust.className = 'md-code-tab';
          btnRust.setAttribute('data-mode', 'rust');
          btnRust.setAttribute('role', 'tab');
          btnRust.setAttribute('aria-selected', 'false');
          btnRust.innerHTML =
            '<span class="md-lang-chip rust">Rust 2024</span>' +
            '<span class="md-tab-title">' + rustListingId + '</span>';

          var btnSplit = document.createElement('button');
          btnSplit.type = 'button';
          btnSplit.className = 'md-code-tab md-code-tab-split';
          btnSplit.setAttribute('data-mode', 'split');
          btnSplit.setAttribute('role', 'tab');
          btnSplit.setAttribute('aria-selected', 'false');
          btnSplit.innerHTML =
            '<span class="md-lang-chip split">Split</span>' +
            '<span class="md-tab-title">Side by Side</span>';

          (function (thisCard) {
            btnCpp.addEventListener('click', function () { activateCardMode(thisCard, 'cpp'); });
            btnRust.addEventListener('click', function () { activateCardMode(thisCard, 'rust'); });
            btnSplit.addEventListener('click', function () { activateCardMode(thisCard, 'split'); });
          })(card);

          bar.appendChild(btnCpp);
          bar.appendChild(btnRust);
          bar.appendChild(btnSplit);
          card.appendChild(bar);

          var panelsWrap = document.createElement('div');
          panelsWrap.className = 'md-code-panels';

          var panelCpp = document.createElement('div');
          panelCpp.className = 'md-code-panel active';
          panelCpp.setAttribute('data-lang', 'cpp');
          panelCpp.setAttribute('role', 'tabpanel');

          var panelRust = document.createElement('div');
          panelRust.className = 'md-code-panel';
          panelRust.setAttribute('data-lang', 'rust');
          panelRust.setAttribute('role', 'tabpanel');

          main.insertBefore(card, unit1.nodes[0]);
          unit1.nodes.forEach(function (n) { panelCpp.appendChild(n); });
          unit2.nodes.forEach(function (n) { panelRust.appendChild(n); });

          panelsWrap.appendChild(panelCpp);
          panelsWrap.appendChild(panelRust);
          card.appendChild(panelsWrap);

          i = unit2.nextIndex;
          continue;
        }
      }
      i += 1;
    }
  }

  applyFigures(false);
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMaterialCodeTabs);
  } else {
    initMaterialCodeTabs();
  }

  new MutationObserver(function () { applyFigures(false); })
    .observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
  window.addEventListener('beforeprint', function () { applyFigures(true); });
  window.addEventListener('afterprint', function () { applyFigures(false); });
})();
