// Puts every line of a code listing in a block of its own, so that a long
// line wraps under its own indentation on a narrow screen. The syntax
// colouring that highlight.js added is kept: an element that spans several
// lines is closed at the end of each line and opened again on the next.
(function () {
    "use strict";

    function splitLines(code) {
        var lines = [];
        var open = [];
        var tips = [];

        function newLine() {
            var line = document.createElement("span");

            line.className = "line";
            lines.push(line);
            tips = [line];

            open.forEach(function (element) {
                var copy = element.cloneNode(false);

                tips[tips.length - 1].appendChild(copy);
                tips.push(copy);
            });
        }

        function walk(node) {
            node.childNodes.forEach(function (child) {
                if (child.nodeType === Node.TEXT_NODE) {
                    child.nodeValue.split("\n").forEach(function (part, i) {
                        if (i > 0) {
                            tips[tips.length - 1].appendChild(document.createTextNode("\n"));
                            newLine();
                        }

                        if (part) {
                            tips[tips.length - 1].appendChild(document.createTextNode(part));
                        }
                    });

                    return;
                }

                if (child.nodeType === Node.ELEMENT_NODE) {
                    var copy = child.cloneNode(false);

                    tips[tips.length - 1].appendChild(copy);
                    tips.push(copy);
                    open.push(child);
                    walk(child);
                    open.pop();
                    tips.pop();
                }
            });
        }

        newLine();
        walk(code);

        if (lines.length > 1 && lines[lines.length - 1].textContent === "") {
            lines.pop();
        }

        return lines;
    }

    // The width of a line's leading white space, counting a tab as 4.
    function indentOf(text) {
        var width = 0;

        for (var i = 0; i < text.length; i += 1) {
            if (text[i] === " ") {
                width += 1;
            } else if (text[i] === "\t") {
                width += 4;
            } else {
                break;
            }
        }

        return width;
    }

    document.querySelectorAll(".content pre > code").forEach(function (code) {
        var lines = splitLines(code);

        code.textContent = "";
        code.classList.add("lined");

        lines.forEach(function (line) {
            line.style.setProperty("--indent", indentOf(line.textContent));
            code.appendChild(line);
        });
    });
})();
