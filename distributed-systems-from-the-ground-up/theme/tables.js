// On a narrow screen a table is shown as a list: each row becomes a block,
// and each cell goes on a line of its own. This gives every cell the name of
// its column, so that a value is not shown without saying what it is.
(function () {
    "use strict";

    document.querySelectorAll(".content table").forEach(function (table) {
        var names = Array.prototype.map.call(table.querySelectorAll("thead th"), function (cell) {
            return cell.textContent.trim();
        });

        table.querySelectorAll("tbody tr").forEach(function (row) {
            Array.prototype.forEach.call(row.children, function (cell, index) {
                if (names[index]) {
                    cell.setAttribute("data-label", names[index]);
                }
            });
        });
    });
})();
