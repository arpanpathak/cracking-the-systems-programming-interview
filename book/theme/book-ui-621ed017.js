// Material Design 3 section icons, figure zoom, and theme menu labels
// for Cracking the Systems Programming Interview (preserving all art & anim.js).
(function () {
    "use strict";

    var ICONS = {
        bolt: '<svg viewBox="0 0 24 24"><path d="M11 21h-1l1-7H7.5c-.58 0-.57-.32-.38-.66.19-.34.05-.08.07-.12C8.48 10.94 10.42 7.54 13 3h1l-1 7h3.5c.49 0 .56.33.47.51l-.07.15C12.96 17.55 11 21 11 21z"/></svg>',
        memory: '<svg viewBox="0 0 24 24"><path d="M15 9H9v6h6V9zm-2 4h-2v-2h2v2zm8-2V9h-2V7c0-1.1-.9-2-2-2h-2V3h-2v2h-2V3H9v2H7c-1.1 0-2 .9-2 2v2H3v2h2v2H3v2h2v2c0 1.1.9 2 2 2h2v2h2v-2h2v2h2v-2h2c1.1 0 2-.9 2-2v-2h2v-2h-2v-2h2zm-4 6H7V7h10v10z"/></svg>',
        code: '<svg viewBox="0 0 24 24"><path d="M9.4 16.6L4.8 12l4.6-4.6L8 6l-6 6 6 6 1.4-1.4zm5.2 0l4.6-4.6-4.6-4.6L16 6l6 6-6 6-1.4-1.4z"/></svg>',
        shield: '<svg viewBox="0 0 24 24"><path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4z"/></svg>',
        layers: '<svg viewBox="0 0 24 24"><path d="M11.99 18.54l-7.37-5.73L3 14.07l9 7 9-7-1.63-1.27-7.38 5.74zM12 16l7.36-5.73L21 9l-9-7-9 7 1.63 1.27L12 16z"/></svg>',
        speed: '<svg viewBox="0 0 24 24"><path d="M20.38 8.57l-1.23 1.85a8 8 0 0 1-.22 7.58H5.07A8 8 0 0 1 15.58 6.85l1.85-1.23A10 10 0 0 0 3.35 19a2 2 0 0 0 1.72 1h13.85a2 2 0 0 0 1.74-1 10 10 0 0 0-.27-10.44z"/><path d="M10.59 15.41a2 2 0 0 0 2.83 0l5.66-8.49-8.49 5.66a2 2 0 0 0 0 2.83z"/></svg>',
        hub: '<svg viewBox="0 0 24 24"><path d="M17 16l-4-4V8.82C14.16 8.4 15 7.3 15 6c0-1.66-1.34-3-3-3S9 4.34 9 6c0 1.3.84 2.4 2 2.82V12l-4 4H3v5h5v-3.05l4-4.2 4 4.2V21h5v-5h-4z"/></svg>',
        check: '<svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>',
        book: '<svg viewBox="0 0 24 24"><path d="M18 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM6 4h5v8l-2.5-1.5L6 12V4z"/></svg>'
    };

    function pickIcon(text) {
        var t = text.toLowerCase();
        if (/benchmark|latency|cost|measur|time|perf|speed|cache/.test(t)) return ICONS.speed;
        if (/memory|alloc|stack|heap|mmap|page|pointer|ownership|align/.test(t)) return ICONS.memory;
        if (/lock|mutex|atomic|futex|thread|concurren|sync|race|pool|queue/.test(t)) return ICONS.bolt;
        if (/tcp|http|socket|tls|epoll|network|fd|pipe|fork|async|kernel/.test(t)) return ICONS.hub;
        if (/fail|error|warn|safe|pitfall|bound|limit|retry|idempoten|interview|question/.test(t)) return ICONS.shield;
        if (/summary|takeaway|exercise|drill|review/.test(t)) return ICONS.check;
        if (/code|impl|listing|design|struct|type|iter|tree|graph|list|heap|hash|shard/.test(t)) return ICONS.code;
        if (/reference|appendix|about|table of contents/.test(t)) return ICONS.book;
        return ICONS.layers;
    }

    function decorateHeadings() {
        var main = document.querySelector(".content main");
        if (!main) return;
        main.querySelectorAll("h2").forEach(function (h) {
            if (h.querySelector(".md-sec-icon")) return;
            var span = document.createElement("span");
            span.className = "md-sec-icon";
            span.setAttribute("aria-hidden", "true");
            span.innerHTML = pickIcon(h.textContent || "");
            h.insertBefore(span, h.firstChild);
        });
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
            if (btn) btn.textContent = labels[id];
        });
    }

    function initFigureZoom() {
        document.querySelectorAll('.content figure img[src*=".svg"]').forEach(function (img) {
            img.addEventListener("click", function () {
                var overlay = document.createElement("div");
                overlay.className = "figure-zoom";
                var copy = document.createElement("img");
                copy.src = img.src;
                copy.alt = img.alt;
                overlay.appendChild(copy);
                function close() {
                    overlay.remove();
                    document.removeEventListener("keydown", onKey);
                }
                function onKey(e) { if (e.key === "Escape") close(); }
                overlay.addEventListener("click", close);
                document.addEventListener("keydown", onKey);
                document.body.appendChild(overlay);
            });
        });
    }

    function init() {
        decorateHeadings();
        labelThemeMenu();
        initFigureZoom();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
