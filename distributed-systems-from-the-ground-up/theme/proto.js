// Colours Protocol Buffers listings. highlight.js, as mdBook ships it, has no
// grammar for the language, so this marks comments, strings, keywords, types
// and numbers with the classes the theme already styles.
(function () {
    "use strict";

    var KEYWORDS = /^(syntax|package|import|option|service|rpc|returns|message|enum|oneof|repeated|optional|reserved|stream)$/;
    var TYPES = /^(double|float|int32|int64|uint32|uint64|sint32|sint64|fixed32|fixed64|sfixed32|sfixed64|bool|string|bytes)$/;
    var TOKEN = /(\/\/[^\n]*)|("(?:\\.|[^"\\])*")|\b([A-Za-z_][A-Za-z0-9_]*)\b|\b(\d+)\b/g;

    function span(kind, text) {
        var element = document.createElement("span");

        element.className = "hljs-" + kind;
        element.textContent = text;

        return element;
    }

    function colour(code) {
        var source = code.textContent;
        var parts = document.createDocumentFragment();
        var last = 0;

        source.replace(TOKEN, function (match, comment, string, word, number, offset) {
            var kind = comment ? "comment" : string ? "string" : number ? "number"
                : KEYWORDS.test(word) ? "keyword" : TYPES.test(word) ? "type"
                : /^[A-Z]/.test(word) ? "title" : null;

            parts.appendChild(document.createTextNode(source.slice(last, offset)));
            parts.appendChild(kind ? span(kind, match) : document.createTextNode(match));
            last = offset + match.length;

            return match;
        });

        parts.appendChild(document.createTextNode(source.slice(last)));
        code.textContent = "";
        code.appendChild(parts);
        code.classList.add("hljs");
    }

    document.querySelectorAll("code.language-protobuf").forEach(colour);
})();
