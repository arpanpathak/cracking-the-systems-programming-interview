// Shows the Go and Rust versions of a listing as 2 tabs of 1 box.
//
//   <div class="code-tabs">
//   <p class="listing">...</p>
//   ```go ... ```
//   ```rust ... ```
//   </div>
//
// The language a reader picks is remembered and applied to every listing.
(function () {
    "use strict";

    var KEY = "gpu-k8s-language";
    var names = { "language-go": "Go", "language-rust": "Rust" };

    function remembered() {
        try { return localStorage.getItem(KEY) || "Go"; } catch (e) { return "Go"; }
    }

    function remember(name) {
        try { localStorage.setItem(KEY, name); } catch (e) { /* storage unavailable */ }
    }

    var groups = [];

    function show(name) {
        groups.forEach(function (group) {
            group.forEach(function (tab) {
                var on = tab.name === name;
                tab.button.setAttribute("aria-selected", on ? "true" : "false");
                tab.pre.hidden = !on;
            });
        });
    }

    document.querySelectorAll(".code-tabs").forEach(function (box) {
        var pres = Array.prototype.slice.call(box.querySelectorAll(":scope > pre"));
        var bar = document.createElement("div");
        var group = [];

        bar.className = "code-tabs-bar";
        bar.setAttribute("role", "tablist");

        pres.forEach(function (pre) {
            var code = pre.querySelector("code");
            var name = Object.keys(names).filter(function (c) { return code && code.classList.contains(c); })
                .map(function (c) { return names[c]; })[0] || "Code";
            var button = document.createElement("button");

            button.type = "button";
            button.textContent = name;
            button.setAttribute("role", "tab");
            button.addEventListener("click", function () { remember(name); show(name); });
            bar.appendChild(button);
            group.push({ name: name, button: button, pre: pre });
        });

        if (pres.length) {
            box.insertBefore(bar, pres[0]);
            groups.push(group);
        }
    });

    show(remembered());
})();
