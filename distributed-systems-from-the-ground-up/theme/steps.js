// A picture in numbered steps. The reader moves through the steps with Back
// and Next, or lets them play. Each step is its own picture file, so a reader
// can stay on a step for as long as they need.
(function () {
    "use strict";

    function pad(number) {
        return number < 10 ? "0" + number : String(number);
    }

    function button(label, onClick) {
        var made = document.createElement("button");

        made.type = "button";
        made.textContent = label;
        made.addEventListener("click", onClick);

        return made;
    }

    document.querySelectorAll("figure.steps").forEach(function (figure) {
        var picture = figure.querySelector("img");
        var prefix = figure.dataset.prefix;
        var count = Number(figure.dataset.count);
        var version = figure.dataset.version;
        var step = 1;
        var timer = null;

        var bar = document.createElement("div");
        var place = document.createElement("span");

        function address(number) {
            return prefix + "-" + pad(number) + ".svg?v=" + version;
        }

        function show(number) {
            step = Math.min(Math.max(number, 1), count);
            picture.src = address(step);
            place.textContent = "Step " + step + " of " + count;
            back.disabled = step === 1;
            next.disabled = step === count;
        }

        function stop() {
            window.clearInterval(timer);
            timer = null;
            play.textContent = "Play";
        }

        function start() {
            if (step === count) {
                show(1);
            }

            play.textContent = "Pause";
            timer = window.setInterval(function () {
                if (step === count) {
                    stop();

                    return;
                }

                show(step + 1);
            }, 3500);
        }

        var back = button("Back", function () { stop(); show(step - 1); });
        var next = button("Next", function () { stop(); show(step + 1); });
        var play = button("Play", function () { return timer ? stop() : start(); });

        bar.className = "steps-bar";
        place.className = "steps-place";
        bar.append(back, place, next, play);
        picture.after(bar);

        // The pictures are fetched ahead, so a step appears without a pause.
        for (var number = 2; number <= count; number += 1) {
            new Image().src = address(number);
        }

        show(1);
    });
})();
