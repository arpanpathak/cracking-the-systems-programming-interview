# Animations: how they are built, and what to keep doing

Read this before adding or changing any animation in the book. It records the method
chapter 22 (async) was rebuilt with, the rules that came out of it, and the traps that cost time.

## 1. The goal

An animation exists to build intuition the prose cannot: cause and effect over time.
The reader should be able to follow it without reading the caption first.

The first generation of GIFs (`animlib.py` + `Frame`, still used by most chapters) were
keyframe slides: boxes of text swapped every four seconds with a two-frame cross-fade.
Nothing moved, so the eye had nothing to follow. The author rejected them. Every chapter is
being converted to the motion style below, one chapter at a time, and the author reviews
each chapter before the next one starts.

## 2. What a good animation here looks like

- **Things travel.** A message is an object that moves from the actor that sends it to the
  actor that receives it. A value flips in place. A thread visibly falls asleep. If a step
  is "X gives Y to Z", draw X handing Y to Z.
- **Real-world metaphors, labelled with the real names.** A thread is a small robot at a
  desk: eyes open while running, closed with drifting z's while parked. A waker is a hand
  bell that is handed over, stored, and rung. Tasks are order tickets on a rail. A saved
  async state is a bookmark. A pinned value has a push pin in it. The metaphor carries the
  intuition; the label (`block_on`, `Waker`, `VecDeque<Arc<Task>>`) keeps it precise.
- **The code is on screen.** Each actor gets a small code panel, and a highlight bar
  slides to the line that actor is running. This ties the picture to the listing.
- **One narration line**, in a band at the foot. Plain band for a step, brass band with "!"
  for the insight, rust band with "x" for the failing case. The caption says what the
  motion is doing *now*; change it when the motion changes.
- **A focus cue** (a dashed brass ring, a glow) on whatever the caption names.
- **A failing case at the end**, in rust: the same run with one line removed or one rule
  broken, so the reader sees the bug the design prevents (a waker never stored, a task
  never re-queued, a future moved while borrowed).
- **Correct to the code.** Read the listing before scripting. The order of events must be
  the order the code runs in (for example, `wake_by_ref` re-queues a task *during* `poll`,
  before `Pending` is returned). Numbers in the animation match the program's output.
- **A progress rail** with named chapters, so the reader knows where the loop is.
- Length: 35 to 65 seconds per loop. Detail the first occurrence of a step, then speed up
  repeats (the builders take a speed factor `k`).

Chapter 22 (`tools/anim_async.py`) is the reference implementation of all of this.

## 3. The engine: `tools/motion.py`

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
  for the whole GIF, and writes `src/figures/<name>`. The last 0.6 s cross-fades into the
  first frame so the loop does not jump.
- Builders register in the module's `BUILDERS`, and `animations.py` merges them into
  `MOTION`. `make animations` runs them. `lint_animations.py` checks only the old slide
  builders, so motion builders are kept out of `animations.BUILDERS`.

Workflow:

```bash
# preview single frames (seconds) while scripting; PNGs go to $MOTION_PREVIEW
MOTION_PREVIEW=/some/scratch/dir python3 tools/anim_async.py frames poll-wake 0 5.5 13
# render one GIF (about 3 to 5 minutes each)
python3 tools/animations.py poll-wake
```

Print the timeline length and chapter times with `tl.now` and `tl.chapters` before
rendering. Preview frames at the busiest moments and look for collisions: labels on
arcs, flying objects crossing the title, captions wrapping onto a third line.

## 4. Traps already hit

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

## 5. Status

| Chapter | Animations | State |
|---|---|---|
| 22 async | poll-wake, task-queue, await, pin | motion |
| 20 sockets | tcp-handshake, bdp, epoll | motion |
| all others | see `grep -o 'figures/[a-z0-9-]*\.gif' src/*.md` | old slides, to convert |

Update this table when a chapter is converted.

## 6. The print edition

Animations do not work in print. The PDF (`tools/build_pdf.py`, WeasyPrint) shows a GIF's
first frame at best, and the HTML edition in `book/` is where the animations live. Do not
bend an animation to make its first frame a good still.

The print edition, if it is revived as a printable book, needs its own approach to
intuition: a strip of three to five numbered still panels per animation (the key
moments, drawn with the same actors), or a static figure that shows all states at once
with arrows for the order. Those can be rendered from the same timelines by sampling
chosen times with `render(..., only=[t1, t2, ...])`. That work has not been done.
