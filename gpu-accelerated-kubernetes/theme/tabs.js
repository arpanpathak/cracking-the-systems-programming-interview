// Code tabs: a <div class="code-tabs"> holds 1 <div class="code-tab" data-lang="...">
// per language. The script adds a row of buttons above the panels and shows 1 panel
// at a time. Choosing a language in one group switches every group on the page, and
// the choice is remembered for the next page.
(function () {
    "use strict";

    var KEY = "gpu-k8s-book-code-lang";

    function load() {
        try {
            return window.localStorage.getItem(KEY);
        } catch (error) {
            return null;
        }
    }

    function save(lang) {
        try {
            window.localStorage.setItem(KEY, lang);
        } catch (error) {
            // Storage can be unavailable; the tabs still work on this page.
        }
    }

    var groups = [];
    var NAMES = { "language-go": "Go", "language-rust": "Rust" };

    // A box can also hold 1 shared caption and the code blocks directly. Each code
    // block is then wrapped in a panel named after its language, so both forms of
    // box get the same tabs.
    function panelize(box) {
        Array.prototype.slice.call(box.querySelectorAll(":scope > pre")).forEach(function (pre) {
            var code = pre.querySelector("code");
            var lang = null;

            Object.keys(NAMES).forEach(function (cls) {
                if (code && code.classList.contains(cls)) {
                    lang = NAMES[cls];
                }
            });

            if (lang === null) {
                return;
            }

            var panel = document.createElement("div");

            panel.className = "code-tab";
            panel.dataset.lang = lang;
            box.insertBefore(panel, pre);
            panel.appendChild(pre);
        });
    }

    function show(group, lang) {
        var found = group.panels.some(function (panel) {
            return panel.dataset.lang === lang;
        });

        if (!found) {
            lang = group.panels[0].dataset.lang;
        }

        group.panels.forEach(function (panel) {
            panel.hidden = panel.dataset.lang !== lang;
        });

        group.buttons.forEach(function (button) {
            var active = button.dataset.lang === lang;

            button.classList.toggle("active", active);
            button.setAttribute("aria-selected", active ? "true" : "false");
            button.tabIndex = active ? 0 : -1;
        });
    }

    function choose(lang) {
        save(lang);
        groups.forEach(function (group) {
            show(group, lang);
        });
    }

    document.querySelectorAll("div.code-tabs").forEach(function (box, index) {
        if (box.querySelector(":scope > .code-tab") === null) {
            panelize(box);
        }

        var panels = Array.prototype.slice.call(box.querySelectorAll(":scope > .code-tab"));

        if (panels.length === 0) {
            return;
        }

        var bar = document.createElement("div");
        var buttons = [];

        bar.className = "code-tab-bar";
        bar.setAttribute("role", "tablist");

        panels.forEach(function (panel, n) {
            var button = document.createElement("button");
            var id = "code-tab-" + index + "-" + n;

            button.type = "button";
            button.textContent = panel.dataset.lang;
            button.dataset.lang = panel.dataset.lang;
            button.setAttribute("role", "tab");
            button.setAttribute("aria-controls", id);

            panel.id = id;
            panel.setAttribute("role", "tabpanel");

            button.addEventListener("click", function () {
                choose(panel.dataset.lang);
            });

            button.addEventListener("keydown", function (event) {
                var step = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;

                if (step !== 0) {
                    var next = buttons[(n + step + buttons.length) % buttons.length];

                    choose(next.dataset.lang);
                    next.focus();
                }
            });

            buttons.push(button);
            bar.appendChild(button);
        });

        box.insertBefore(bar, panels[0]);
        box.classList.add("ready");
        groups.push({ panels: panels, buttons: buttons });
    });

    var initial = load() || "Go";

    groups.forEach(function (group) {
        show(group, initial);
    });
})();
