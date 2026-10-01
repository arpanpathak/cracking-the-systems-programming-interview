# Animations

Read this file before you add or change an animation. It describes the engine in
`tools/motion.py`, the rules every animation follows, and problems already solved.

## 1. Purpose

An animation shows a change over time that a still figure cannot show: a message sent
from one thread to another, a value that changes, a thread that stops running. Each
animation follows one run of the program in the listing beside it.

Most chapters still use the older slide animations in `animlib.py`, which swap whole
pictures every few seconds. They are converted to the engine below one chapter at a time,
and the author reviews each chapter before the next one starts.

## 2. Pacing and reader control

The reader may have ADHD, may be neurodivergent, or may be new to the topic. The engine
gives that reader time and control by default.

- `tl.say(text)` changes the caption. It first waits until the previous caption has been
  on screen for 0.36 s per word, and at least 2.6 s. After the new caption appears, nothing
  moves for `lead` seconds. Every scripted duration is multiplied by `pace` (1.2). Set
  captions only with `tl.say`.
- A code panel shows a line only after the highlight has reached it. Lines below that
  point are drawn as grey bars. Pass `reveal=s.timeline.reached(track, t)`.
- `render` writes an MP4 and a JSON step list next to each GIF. `tools/anim_markup.py`
  replaces the chapter's `<img>` with a `<video>` that keeps the GIF as a fallback.
  `theme/anim.js` adds a play button, speeds of 0.5x, 0.75x, and 1x, a button for each
  step, and a mode that pauses at the end of each step. When the reader's system asks for
  reduced motion, the video starts paused.

## 3. Drawing rules

1. Draw a message as an object that moves from the sender to the receiver. Draw a changed
   value in the place it is stored.
2. Use a physical object for each actor, and label it with the name from the code. The
   async chapter draws a thread as a robot at a desk, which closes its eyes when parked, and
   a waker as a bell.
3. Show each actor's code in a panel, with a bar on the line that actor is running.
4. Keep one caption at the foot of the frame. Use the plain band for a step, the brass band
   for the result the animation exists to show, and the rust band for the failing case.
5. Mark the element the caption names with a ring or a glow. Never draw a marker on top of
   the element it marks.
6. End with a failing case: the same run with one line removed or one rule broken.
7. Follow the code exactly. Events happen in the order the code runs them, and numbers
   match the program's output.
8. Show a progress rail with a label for each step.
9. Write captions by the rules in `../anti_ai_slop.md` and `WRITING_GUIDE.md`. Each caption
   states what is happening in the frame. Run the deletion test on each one.
10. Show the first occurrence of a repeated step slowly, and later ones faster. The builders
    take a speed factor `k` for this.

`tools/anim_async.py` is the reference implementation.

## 4. The engine: `tools/motion.py`

- `Timeline(**initial)`: named values over time, scripted in order.
  - `set(**v)` changes values at the cursor. `to(dur, ease, **v)` tweens and advances
    the cursor. `also(dur, ease, delay, **v)` tweens without advancing (parallel motion).
    `wait(s)`. `event(name)` marks a moment; `age(name, t)` in the draw function gives the
    seconds since, for one-shot effects (a bell ringing, a shake). `chapter(label)` adds a
    stop on the progress rail. `changed(name, t)` gives when a value last changed (used for
    caption fades and the split-flap tag flip).
  - Numbers, `(x, y)` tuples, and `#rrggbb` colours interpolate. Strings switch.
  - Easing: `in_out`, `ease_out`, `ease_in`, `linear`, `back` (overshoot, for things that
    land). Do not use `back` on gauges or counters: it overshoots (a CPU gauge read 110%).
- `draw(p, s, total)`: paints one frame from the sampled values `s` onto a `Pic` (an SVG
  canvas with `rect`, `circle`, `line`, `path`, `text`, and `group(opacity, dx, dy, rotate,
  scale)`). Keep it a pure function of `s`.
- Actors and furniture: `robot`, `zzz`, `bell`, `ring_waves`, `pill` (a message in
  flight), `chip`, `meter`, `focus`, `code_panel`, `title_block`, `scoreboard`, `caption`,
  `progress`, `bezier` (for arcs).
- `render(name, tl, draw, height)`: samples at 20 fps, merges identical frames into longer
  holds, rasterises the distinct frames with `rsvg-convert` in parallel, builds one palette
  for the whole GIF, and writes `src/figures/<name>`, plus `<stem>.mp4` (same frames,
  H.264) and `<stem>.json` (duration and chapter times for the step buttons). The last
  0.6 s cross-fades into the first frame so the loop does not jump.
- Builders register in the module's `BUILDERS`, and `animations.py` merges them into
  `MOTION`. `make animations` runs them. `lint_animations.py` checks only the old slide
  builders, so motion builders are kept out of `animations.BUILDERS`.

Workflow:

```bash
# preview single frames (seconds) while scripting; PNGs go to $MOTION_PREVIEW
MOTION_PREVIEW=/some/scratch/dir python3 tools/anim_async.py frames poll-wake 0 5.5 13
# render one GIF (about 3 to 5 minutes each)
python3 tools/animations.py poll-wake
python3 tools/anim_markup.py          # point the chapter at the new video and steps
```

Print the timeline length and chapter times with `tl.now` and `tl.chapters` before
rendering. Preview frames at the busiest moments and look for collisions: labels on
arcs, flying objects crossing the title, captions wrapping onto a third line.

## 5. Problems already solved

- **File size.** Anything that changes on every frame makes every frame a new image. The
  first render was 76 MB because the progress rail crept every frame. Now the rail steps
  twice a second, idle motion (drifting z's, a stopwatch hand) is quantised to a few
  steps a second, and the palette has 255 colours so the encoder has a free slot for
  "unchanged" pixels. With that, a 60 s loop is 3.5 to 8 MB at 1517 px wide. Large objects
  that travel far and often (the task-queue tickets) cost the most.
- **Palette.** Median cut alone turned the page white into grey. The book's flat colours
  are pinned first (`exact` in `render`, plus `extra_colors` per animation), and pixels are
  mapped with an exact nearest-colour search (`nearest`), because Pillow's own
  palette conversion uses a reduced-precision cache.
- **Whitespace.** SVG collapses leading spaces, which flattened the code panels. Text is
  written with `xml:space="preserve"`.
- **`set` at t = 0** must take effect at t = 0 (zero-length segments count as done at their
  start). Otherwise the first frame shows the old value.
- **Workers re-import the modules.** `render` uses a process pool, and on macOS the workers
  import the main module again. Do not edit `motion.py` or the builders while a render is
  running. To keep working, render from a copy of the builder module:
  `cp tools/anim_sockets.py /scratch/snap.py && PYTHONPATH=tools python3 /scratch/snap.py epoll`.
  Several renders can run at once this way.
- **Lifted arcs** have to stay below the subtitle: keep a flying object's top edge under
  y = 64.

## 6. Status

| Chapter | Animations | State |
|---|---|---|
| 20 sockets | tcp-handshake, bdp, epoll | motion |
| 21 http | http-framing, keep-alive | motion |
| 22 async | poll-wake, task-queue, await, pin | motion |
| all others | see `grep -o 'figures/[a-z0-9-]*\.gif' src/*.md` | old slides, to convert |

Update this table when a chapter is converted.

## 7. The print edition

Animations do not work in print. The PDF (`tools/build_pdf.py`, WeasyPrint) shows a GIF's
first frame at best, and the HTML edition in `book/` is where the animations live.

The print edition, if it is revived as a printable book, needs its own approach to
intuition: a strip of three to five numbered still panels per animation (the key
moments, drawn with the same actors), or a static figure that shows all states at once
with arrows for the order. Those can be rendered from the same timelines by sampling
chosen times with `render(..., only=[t1, t2, ...])`. That work has not been done.
