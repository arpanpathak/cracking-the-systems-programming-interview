// Shows the dark variant of each figure in the dark themes, and the light
// variant in the light themes and in print.
(function () {
  var DARK_THEMES = ['coal', 'navy', 'ayu'];

  function isDark() {
    var classes = document.documentElement.classList;
    return DARK_THEMES.some(function (name) { return classes.contains(name); });
  }

  function apply(forceLight) {
    var dark = !forceLight && isDark();
    document.querySelectorAll('img[src*="figures/"]').forEach(function (img) {
      var current = img.getAttribute('src');
      var light = current.replace('figures/dark/', 'figures/');
      var wanted = dark ? light.replace('figures/', 'figures/dark/') : light;
      if (wanted !== current) img.setAttribute('src', wanted);
    });
  }

  apply(false);
  new MutationObserver(function () { apply(false); })
    .observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
  window.addEventListener('beforeprint', function () { apply(true); });
  window.addEventListener('afterprint', function () { apply(false); });
})();
