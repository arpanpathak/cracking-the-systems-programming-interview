// 1. Swaps theme-aware Material Design 3 SVGs (`figures/m3/*.svg` and
//    `art/ch*-plate.svg`) between light and dark variants automatically based
//    on the active mdBook theme (and forces light mode when printing).
// 2. Opens any figure diagram full screen on click/tap for inspection.
(function () {
    "use strict";

    var DARK_THEMES = ["coal", "navy", "ayu"];

    function isDark() {
        var classes = document.documentElement.classList;
        return DARK_THEMES.some(function (name) {
            return classes.contains(name);
        });
    }

    function swapDir(selector, dirPrefix, forceLight) {
        var dark = !forceLight && isDark();
        var darkPrefix = dirPrefix + "dark/";
        document.querySelectorAll(selector).forEach(function (img) {
            var current = img.getAttribute("src");
            var light = current.replace(darkPrefix, dirPrefix);
            var wanted = dark ? light.replace(dirPrefix, darkPrefix) : light;
            if (wanted !== current) {
                img.setAttribute("src", wanted);
            }
        });
    }

    function isPrintPage() {
        return /print\.html$/i.test(window.location.pathname) ||
            (window.matchMedia && window.matchMedia("print").matches);
    }

    function applyThemeAssets(forceLight) {
        var light = Boolean(forceLight) || isPrintPage();
        swapDir('img[src*="figures/m3/"]', "figures/m3/", light);
        swapDir('img.plate[src*="-plate.svg"]', "art/", light);
        swapDir('img.cover[src*="cover.svg"]', "art/", light);
    }

    function open(diagram) {
        var view = document.createElement("div");
        var picture = document.createElement("img");

        view.className = "figure-zoom";
        picture.src = diagram.src;
        picture.alt = diagram.alt;

        var upright = window.innerHeight > window.innerWidth;
        var wide = diagram.naturalWidth > diagram.naturalHeight * 1.2;

        if (upright && wide) {
            view.classList.add("turned");
        }

        function close() {
            view.remove();
            document.removeEventListener("keydown", onKey);
        }

        function onKey(event) {
            if (event.key === "Escape") {
                close();
            }
        }

        view.appendChild(picture);
        view.addEventListener("click", close);
        document.addEventListener("keydown", onKey);
        document.body.appendChild(view);
    }

    function labelThemeMenu() {
        var labels = {
            light: "Light (Paper)",
            rust: "Warm Parchment",
            navy: "Night Owl (Blue)",
            coal: "Material Deep Ocean",
            ayu: "Oceanic Next"
        };
        Object.keys(labels).forEach(function (id) {
            var btn = document.getElementById(id);
            if (btn) {
                btn.textContent = labels[id];
            }
        });
    }

    applyThemeAssets(false);
    labelThemeMenu();

    new MutationObserver(function () {
        applyThemeAssets(false);
    }).observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });

    window.addEventListener("beforeprint", function () { applyThemeAssets(true); });
    window.addEventListener("afterprint", function () { applyThemeAssets(false); });

    document.querySelectorAll('figure > img[src*=".svg"]').forEach(function (diagram) {
        diagram.style.cursor = "zoom-in";
        diagram.title = "Open at full size";
        diagram.addEventListener("click", function () { open(diagram); });
    });
})();
