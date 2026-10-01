# Start here: a briefing for the next agent session

Paste the prompt below into a new session to start work on this book. The rest of this file is the material
the prompt points to.

## The prompt

```text
You are continuing work on the mdBook "Cracking the Systems Programming Interview".

Repository: /Users/arpanpathak/Projects/rust/cracking-the-systems-programming-interview
  Book:  cracking-the-systems-programming-interview/   (chapters in src/, tools in tools/)
  Code:  rust-interview-lab/                            (crate systems-lab; the chapters include it)
  Branch: prep-v2

Before you change anything, read these files in this order, in full:
  1. ../anti_ai_slop.md                      the banned writing patterns. Re-read before every prose edit.
  2. WRITING_GUIDE.md                        the reader, the section procedure, the voice.
  3. START_HERE.md                           this briefing: rules, standards, tools, checks, publishing.
  4. WORKLOG.md                              what is done, the per-chapter assessment, the next work.
  5. tools/ANIMATIONS.md                     the motion engine and its conventions.

Then pick the next item from WORKLOG.md ("Priority order"), read that chapter and its lab code, and
work to the standard in START_HERE.md. Run every check listed there before you commit. Commit with
the user as the only author. Publish GitHub Pages after each finished batch.
```

## Standing rules

These come from the user. They override any default habit.

- **No AI attribution.** No `Co-Authored-By` line, no mention of Claude or Anthropic in commits, PRs, or
  files. The user is the only author.
- **No employer.** Never name the user's employer, its products, or its hardware anywhere in the book or
  the repository.
- **No new chapters** unless the user asks. The book is ch01 to ch29 plus ch30 (drills). The work now is
  enrichment.
- **Leave the user's work in progress alone.** Do not commit, move, or delete `knowledge_gaps.md`,
  `rust-async-http-examples/`, `rust-interview-lab/src/1`, or `rust-interview-lab/src/bin/atomic_rate_limiter.rs`.
- **Trust existing results.** Write from the code, its tests, and the numbers already in the chapters.
  Do not rerun benchmarks or write scratch experiments. Run `cargo test` or `cargo run` only for output a
  listing needs. Docker is allowed only for Linux-only programs (epoll edge, futex, sendfile).
- **The HTML book is the target.** Ignore the PDF build.
- **Ask before outward-facing actions** you have not been asked for. Pushing, publishing Pages, and cutting a
  release after finished work are expected.

## The writing standard

- Follow `../anti_ai_slop.md` and `WRITING_GUIDE.md`. Plain teacher voice, "you" for the reader. No meta
  sentences about the book, the repository, or the writing. No "just", "worth", "matters", "important",
  "unlock", "it depends", no em dashes. Sentences of 24 words or fewer.
- Intuition first: the problem in plain words, an everyday analogy or a cost table, a hand-worked example.
  Then the code.
- Code comes in short `{{#include path:a:b}}` excerpts, each explained. Whole files go in a "complete
  files" section at the end of the chapter. No whole file over about 40 lines in the middle of a chapter.
- Introduce every type before an excerpt uses it. Show the signature, with each parameter explained, for
  every system call or library API the chapter relies on.
- Lab code: `cargo +nightly fmt` (rustfmt `chain_width = 40`, one call per line in long chains) and a clean
  `cargo clippy`.
- Report results honestly, including a fact that contradicts the text. Fix the text.

## The animation standard

Read `tools/ANIMATIONS.md`. In short:

- **One animation per code block that introduces behaviour**, placed right after that block.
- **The structure moves.** A node lifts out of a chain, and the neighbours' arrows swing to each other. The
  node travels to its new place. Numbers changing inside fixed boxes do not count.
- **Every animation has an unhappy path.** Strike a line of the real code, or feed a wrong input. Show the
  wrong result it produces, with captions of the `"fail"` kind.
- **Code panels show real code** through `motion_kit.Panel` or `Panels`: contiguous ranges of the lab file,
  indentation kept, gaps marked `// ...`. Never `lines_containing` or hand-typed code, except a
  counterfactual variant written in full and titled as one.
- Robots stand for threads, callers, and owners. Narration is paced for reading. Captions follow the
  writing standard.

## The figure standard

- Hand-drawn figures are `tools/draw_chNN.py` on `tools/svgkit.py`. Connect two boxes with
  `f.link(box_a, box_b)`, never with raw `f.arrow` coordinates. `link` runs edge to edge with a small gap,
  so a tip cannot float or bury itself in a box.
- Graphviz figures are `diagrams/*.dot`, rendered by `tools/figures.py`. With `rankdir=LR`, a record
  lays out sideways: put a vertical list in a record without braces. Draw a backward edge as a forward
  edge with `dir=back`, not with `constraint=false`. For a small fixed diagram, pin the nodes with
  `layout=neato` and `pos="x,y!"`.
- A label never sits in an arrow's path. A figure too wide for the page column is redrawn, not shrunk.

## Tools

Run from `cracking-the-systems-programming-interview/`.

| Command | What it does |
|---|---|
| `python3 tools/lint_prose.py src/*.md` | banned phrases and long sentences in chapter prose |
| `python3 tools/lint_figures.py` | labels that overflow or collide in figures |
| `python3 tools/lint_arrows.py` | skewed, floating, buried, or crossing arrows in hand-drawn figures |
| `python3 tools/excerpts.py check` | every include range still matches the lab code |
| `python3 tools/excerpts.py remap` | shifts include ranges after lab code changes (diffs against HEAD: run before committing the lab change) |
| `python3 tools/draw_chNN.py` | redraws one chapter's hand-drawn figures |
| `python3 tools/figures.py` | renders every `diagrams/*.dot` |
| `python3 /abs/path/tools/animations.py NAME ...` | renders animations; use the absolute path in background shells |
| `python3 tools/anim_markup.py` | turns each animation `<img>` into its `<video>`, refreshing chapter markers |
| `mdbook build` | builds the HTML book into `book/` |

## Checks before every commit

1. `python3 tools/lint_prose.py src/*.md` reports 0 findings.
2. `python3 tools/lint_figures.py` and `python3 tools/lint_arrows.py` report no new findings. The arrow
   linter's remaining hits are deliberate: arrows between before and after panels, and arrows to text labels.
3. `python3 tools/excerpts.py check` reports 0 problems.
4. `cargo test` passes for any lab file you touched, and `mdbook build` prints no error or warning.
5. Look at every figure and animation you changed: render a still and read it.

## Publishing

```sh
git push origin prep-v2
W=$(mktemp -d)/ghp
git fetch origin gh-pages && git worktree add "$W" origin/gh-pages
cd "$W" && git checkout -B gh-pages origin/gh-pages && rm -rf book
cp -R <book-dir>/book book && git add -A && git commit -m "Publish book: <what changed>" && git push origin gh-pages
cd - && git worktree remove --force "$W"
```

A release: zip `book/` and run `gh release create book-vX.Y <zip> --target prep-v2 --title ... --notes ...`.
The site is https://arpanpathak.github.io/cracking-the-systems-programming-interview/book/.

## Traps already hit

- **Rendering is slow** (3 to 6 minutes per animation): one `rsvg-convert` process per frame reloads fonts.
  Run renders in the background, in batches. Edit a module the render has loaded only with an atomic write
  of a file that compiles. The running render keeps the old code either way.
- **zsh** reads `$rev:path` as a modifier. Write `${rev}:path`.
- **Block replacement scripts**: end a replaced definition at its matching bracket, never at the next blank
  line. A blank-line cut deleted the constants that followed a definition twice.
- **`rm` with a variable** is blocked by the safety check. Use a literal path or `"${VAR:?}"`.
- **Numbering**: after inserting a listing, figure, or animation, renumber the captions in document order and
  map every reference by its old id. Check every "listing", "figure", and "section" reference resolves.
