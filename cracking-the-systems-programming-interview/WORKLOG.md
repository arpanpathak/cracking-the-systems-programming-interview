# Work log: depth pass and systems backlog

A new session starts with `START_HERE.md`: a prompt to paste, the rules, the standards, and the checks.

This file is the plan and the running log for the current round of work. If a
session is interrupted, read this file first, then continue from the first
unchecked item. Update it after every finished item, and commit with it.

## Rules for every item

- Read `../anti_ai_slop.md` (all of it) and `WRITING_GUIDE.md` before writing prose.
- Concept first: the problem in plain words, the machine or kernel mechanism, a
  block diagram, a small worked example. Code comes after, in small excerpts.
- Code in `rust-interview-lab` in the existing style: doc comments on items, short
  functions, `let ... else` for early exits, iterator chains broken one call per
  line, tests at the bottom, `cargo +nightly fmt`. No scratch comments.
- Every listing shows real output. Linux-only programs are compile-checked with
  `--target aarch64-unknown-linux-gnu` and run once in Docker for their output.
- One motion animation per new mechanism (`tools/ANIMATIONS.md`), preview with
  `tools/preview.py`, captions pass `tools/lint_prose.py`.
- New chapters get a plate in `tools/art.py`.
- No AI attribution in commits.

## Scope

The test for new material: does it explain a machine or resource constraint the
reader will hit in production? Puzzle techniques are out (sorting, quickselect,
monotonic stack, Bellman-Ford/A*/Floyd, string algorithms, bit tricks, reservoir
sampling, interval puzzles). This round covers the eight largest mechanism gaps
from `../knowledge_gaps.md`; the rest of that file stays as the backlog.

## Phase 1: depth pass on existing chapters

Sections that open on code get the concept, a diagram, and a worked example
first. Order: the network part, then the chapters with the most code-first
sections.

- [x] ch21 HTTP: what a request is on the wire, the parser and server as a
      block diagram, before 21.1
- [x] ch20 sockets: addresses, the window, the echo server, and epoll each get a
      concept section and diagram before their listings
- [x] ch16 threads and locks
- [x] ch18 thread pools
- [x] ch10 merge k lists
- [x] ch14 sharding
- [x] ch02 files
- [x] ch07 types
- [x] ch09 linked lists

## Phase 2: new material (the eight)

New parts go after Part 6. The drills chapter stays last: it is now ch30
(`src/ch30-drills.md`, plate 30), leaving 23 to 29 for the seven new chapters:
23 mmap, 24 fd table, 25 edge-triggered epoll, 26 futex, 27 TCP teardown,
28 TLS, 29 connection pool. Part numbers in SUMMARY.md: 7 kernel boundary,
then 8 and 9 as they are added, drills last.

- [x] Part 7, the kernel boundary
  - [x] mmap and zero-copy (MAP_SHARED vs MAP_PRIVATE, first-touch faults,
        msync; sendfile vs read/write; TLS forces bytes back to user space)
  - [x] the fd table, fork/exec, and pipes (dup2, FD_CLOEXEC, a leaked fd,
        `ls | wc -l`)
  - [x] edge-triggered epoll (EPOLLET, drain to EAGAIN, the stall when reading
        once; EPOLLONESHOT, EPOLLEXCLUSIVE)
- [x] Part 8, under the locks
  - [x] futex mutex and memory-ordering litmus tests
- [x] Part 9, production networking
  - [x] TCP teardown: states, TIME_WAIT, CLOSE_WAIT leak, half-close
  - [x] TLS and mTLS with rustls
  - [x] client connection pool (bounded, RAII return, idle eviction)
- [x] ch19: single-flight idempotency as a section

## Log

Newest entry last. One line per finished step: date, item, commit.

- 2026-10-01 plan written
- 2026-10-01 ch21: new 21.1 (wire format, where a request ends, server parts), figures 21.1 and 21.2, sections and figures renumbered
- 2026-10-01 ch20: each section opens with the concept (addresses and private ranges, ACKs/RTT/window, the socket lifecycle, non-blocking + epoll lists), code in excerpts, complete programs in 20.5; new figures 20.3 and 20.4; real net_ipv4 output
- 2026-10-01 ch16: new 16.1.1 (what a thread is: shared memory, per-thread stack, scheduler, context switch) with figure 16.1; figures renumbered. The rest of ch16 already led with concepts.
- 2026-10-01 ch18: lead-ins before the version 1 listing and the three short pools; 18.1 already explained the parts
- 2026-10-01 ch10: lead-ins before eight code versions; 10.6 and 10.7 explain the strategy before the listing. 10.1-10.2 already taught the merge and the strategies.
- 2026-10-01 ch14, ch02, ch07, ch09: a lead-in sentence before every code-first subsection (19 in all); explanations after the code were already there
- 2026-10-01 lab: mmap_file.rs (macOS 64 first-pass faults; Linux 5, fault-around) and zero_copy.rs (Docker: read/write 8193 calls 809 MiB/s, sendfile 1 call 1318 MiB/s); commit 3b52d0b
- 2026-10-01 ch23 Mapping files and copying less: page cache, mmap faults, shared/private, SIGBUS, sendfile, TLS; figures 23.1-23.3, animation ch23-faults (anim_kernel.py), plate FOLIO; drills renamed to ch30, Part 7 added to SUMMARY
- 2026-10-01 lab: fd_table.rs (lowest free fd, ls | wc -l via pipe/fork/dup2/execvp, held write end, F_DUPFD vs F_DUPFD_CLOEXEC); macOS and Docker output match except wc padding
- 2026-10-01 ch24 File descriptors, fork, and pipes: three-level table, fork/exec, async-signal-safety, pipe rules, the five shell steps, close-on-exec; figures 24.1-24.3, animation ch24-pipe, plate RELAY
- 2026-10-01 lab: epoll_edge.rs (Docker: LT read-once 3 events, ET read-once 1 event 5904 left, ET drain 1 event; ONESHOT 1/0/1; EXCLUSIVE 4 vs 1 woken)
- 2026-10-01 ch25 Edge-triggered epoll: levels vs edges, ready list, the stall, EPOLLOUT under ET, drain caps, ONESHOT, EXCLUSIVE, SO_REUSEPORT; figures 25.1-25.2, animation ch25-edge, plate TRIP. Part 7 complete.
- 2026-10-01 lab: futex_mutex.rs (Docker, 2 CPUs: 0 syscalls uncontended; wakes > waits from the conservative state 2; std faster with its spin) and litmus.rs (SB ~1.5% Relaxed and Rel/Acq on x86 Mac, 0 SeqCst; MP 0 on x86)
- 2026-10-01 ch26 Futexes and memory ordering: futex wait/wake, lost wake-up, three-state mutex, measured syscalls, store buffers, TSO vs ARM, litmus tests; figures 26.1-26.3, animations ch26-futex and ch26-store-buffer, plate LATCH; Part 8 added to SUMMARY
- 2026-10-01 lab: tcp_close.rs (Docker: states from /proc/net/tcp; FIN_WAIT2/CLOSE_WAIT, TIME_WAIT on the active closer, 5 CLOSE_WAIT leak, EADDRINUSE without SO_REUSEADDR, ECONNRESET on unread data)
- 2026-10-01 ch27 Closing TCP connections: four-segment close, state table, TIME_WAIT purpose and port cost, SO_REUSEADDR, CLOSE_WAIT leaks, RST and lingering close; figure 27.1, animation ch27-close, plate TAPER; Part 9 started in SUMMARY
- 2026-10-01 lab: Cargo.toml gains rustls 0.23 (ring) and rcgen 0.13; tls_mtls.rs (macOS: TLS 1.3 records 231/1/69/31, name and CA failures, mTLS CertificateRequired vs 481-byte flight)
- 2026-10-01 ch28 TLS and mutual TLS: certificates and trust, TLS 1.3 handshake table, records on the wire, failures, mTLS, costs; figure 28.1, animation ch28-tls, plate SEAL
- 2026-10-01 lab: conn_pool.rs (2000 requests: 2000 conns 170 ms vs pool of 4 80 ms; TimedOut at the bound; idle eviction; check_alive catches server-closed connections)
- 2026-10-01 ch29 A client connection pool: connection costs, four rules, get/give_back/Drop guard, LIFO and stale connections, measured; figure 29.1, animation ch29-pool, plate DOCK. Part 9 complete.
- 2026-10-01 new chapters stopped at ch29 by request; the round moves to enriching existing chapters
- 2026-10-01 motion engine: code panels show code from the first frame, two lines ahead of the highlight, and fade new lines in (`Timeline.reached`, `code_panel`)
- 2026-10-01 lab: clippy-clean book sources (crate allows only `new_without_default`, `needless_range_loop`); scratch code removed from the recursion listing; chain_width 40
- 2026-10-01 ch03, ch12, ch13: every excerpted file ends the chapter in full
- 2026-10-01 types before use: ch07 (sections reordered), ch10-12, ch16, ch18, ch19 (`ApiError` shown again), ch26; type excerpts before whole-file listings in ch06, ch10-12, ch15, ch18, ch19
- 2026-10-01 ch22: both HTTP clients built in explained excerpts
- 2026-10-01 ch20, ch23-27: C declarations with parameter comments before first use
- 2026-10-01 all 46 animations re-rendered with the new code reveal

- 2026-10-01 ch19 section 19.4 single flight: concept, figure 19.6, excerpts, measured (1 execution for 8 callers; 103 ms vs 417 ms one-lock), panic case, animation ch19-single-flight, listing 19.12; exercise 4 replaced

## Phase 3: depth pass (requested 2026-10-01)

Each chapter below gets: intuition before code (the problem in plain words, a worked example by hand), more
block diagrams, at least one motion animation per core mechanism (with a failing case), and any whole-file
listing broken into explained excerpts. Order is by need, measured (words, figures, animations, dumps).

- [x] ch18 thread pools: version 1 and map_order in excerpts; animations pool-lock (205 vs 814 ms) and pool-panic; figure 18.4 bounded queue + result channel. The three short pools in 18.6 remain whole listings with type intros.
- [x] ch15 memory, caches, OS: animations mem-hierarchy and false-sharing
- [x] ch10 merge k: animations merge-two (with a no-attach failure) and merge-rounds (72 vs 105 moves)
- [x] ch08 pointers: animations rc-refcell (with a double-borrow panic) and weak-parent (with an Rc cycle leak)
- [x] ch04 iterators: animation lazy-chain
- [x] ch07 parse-trace, ch01 fib-calls, ch02 bufreader animations
- [x] ch23-ch29: more diagrams (ch23 address space, ch25 fair drain, ch27 ports, ch28 record, ch29 stale)
- [ ] whole-file dumps: done ch03 three_sum, ch12 graph_topology, ch16 deadlock, ch17 mpmc, ch18 worker_pool, ch22 clients; smaller ones remain (see Future work 2)

## Future work (draft for the next agent session)

Read the rules at the top of this file first. No new chapters unless asked: the book is ch01 to ch29 plus
drills (ch30). The work now is enrichment.

1. **ch19 single flight.** Done as section 19.4. `rust-interview-lab/src/bin/single_flight.rs` is written and tested (scenes:
   8 callers one key -> 1 execution, 4 keys in parallel, failure not stored, panic clears the claim). Add it as
   section 19.4 after idempotency keys: concept (thundering herd on a cache miss, why 19.3's single lock
   serializes all keys), a slot-state diagram (none -> InProgress -> Done; Err/panic -> none), excerpts
   (`Slot`, `SingleFlight`, `Claim` + `Drop`, `execute`), output, an animation (callers waiting on one key;
   fail case: a claim without Drop strands waiters after a panic), and replace exercise 4, which asks for this.
2. **Whole-file listings shown first.** These still appear whole before any excerpt; each needs the
   concept, then excerpts, then the full file: ch03 three_sum (87 lines), valid_parentheses, min_stack,
   binary_search; ch05 top_k_frequent; ch09 the four list variants; ch10 pairs/heap/chrush_lee; ch11
   test_tree, trie; ch12 graph_bfs, cyclic_graph_map, graph_topology (81), dependency_resolutiom, dijkstra,
   dijkstra_bruce_lee; ch15 false_sharing, os_scheduler; ch16 concurrency_amdahl, concurrency_deadlock (73);
   ch17 mpmc_bounded_buffer (83); ch18 thread_pool, the three short pools, worker_pool (107); ch19
   idempotent_operation(_with_error_progagation); ch22 async_demo. Find them with the script in the log of
   this round: a full `{{#include}}` that is a file's first appearance in its chapter, over 40 lines.
3. **Audit tools.** Turn the two audits used this round into `tools/lint_code_intro.py`: (a) an excerpt
   that uses a type defined in the lab whose definition the chapter has not shown yet; (b) the whole-file
   rule above. Run both with `lint_prose.py` before every commit.
4. **Signatures.** ch15's `getpid` via FFI and any other `extern` call outside ch20-27 should get the same
   declaration-with-comments block.
5. **Backlog** from `../knowledge_gaps.md` that passed the scope test but was not built: see that file.
6. Republish gh-pages after each batch (`mdbook build`, copy `book/` to the gh-pages worktree) and cut a
   release when a batch of chapters is finished.

## Chapter depth assessment (for the next agent session)

The standard is the ch13 rework, done in response to "it feels like static boxes, shallow, and too much code".
A chapter meets the bar when it has:

- **(a) intuition before code.** Start with a plain-language model, an everyday analogy, or a cost table. It
  says why the structure exists. ch13's 13.1.1 is the template: what a hit saves, a hand trace, the fail case.
- **(b) one animation per core operation.** Robots or the structure itself move, with a fail case. A whole
  topic does not count as one operation. The structure must move on screen. A node lifts out of the chain,
  and the neighbours' arrows swing to each other. The node travels to its new place, and the head and tail
  markers follow. Numbers changing inside fixed boxes do not count: the user rejected that as "static boxes".
- **(c) excerpts first, then the complete file at the end.** No mid-chapter dump over about 40 lines.

The numbers below were measured on 2026-10-01: prose words, animations, and whole-file includes
mid-chapter. Re-measure with the script in the log before starting.

Priority order: ch14, ch04, ch02, ch11, ch12, then the rest.

| Ch | Animations | Gap against the bar | Suggested work |
|---|---|---|---|
| 01 bindings | fib-calls | (b) ownership moves and shadowing are static | A move-versus-copy robot hand-off: `let b = a` for `String` against `i32`, and the use-after-move compile error as the fail case |
| 02 files | bufreader | (c) 11 whole files mid-chapter (path_buff, read_write_file, copy/rename/delete, list_directory, recursive walk, pagination, command_line_args at 120 lines) | Excerpt each to the calls that matter, then move the files to a "2.9 The complete files". Optional animation: the recursive walk as a stack of directories |
| 03 collections | 10 | (c) about 10 whole files; three_sum and the others were noted earlier | Excerpts only; motion is already rich |
| 04 iterators | lazy-chain | (a) about 260 words before code; (b) no motion for `collect`, `fold`, or `zip` | An adapter-pipeline robot line with `fold` accumulating; the fail case is a chain with no consumer that does nothing |
| 05 heaps | heap-sift, top-k | (c) median_finder at 138 lines | A two-heaps animation for the median: balance and rebalance |
| 06 DP | coin-change, subsets | Fine. Job scheduling has no motion | Optional: a deadline-slots animation |
| 07 types | parse-trace | (c) adt_idioms at 236 lines and state_machine shown whole | Excerpt them. A state-machine animation in which an invalid transition does not compile (the typestate fail case) |
| 08 pointers | rc-refcell, weak-parent | (c) smart_pointers at 165 lines | Excerpt it. A `Box` on the heap against the stack size, as a small figure |
| 09 linked lists | reverse, list-replace, list-drop, list-doubly | Done 2026-10-01: treasure-hunt intuition, push/pop with `replace` (fail: E0507), drop as a growing stack (fail: overflow at 262,144 frames) against the loop, strong counts in the doubly list (fail: strong prev leaks); excerpts first, complete files in 9.9 | Reference for list-shaped chapters |
| 10 merge-k | merge-two, merge-rounds, merge-owned | Done 2026-10-01: listing 10.5 simplified by swapping the two lists by value (`(left, right) = (right, left)`), leaving `tail` as the only mutable reference, plus `left.or(right)`; the user's `while gap < size` loop kept; section 10.4.4 with a trace and an animation (fail: no `or`); time and memory table for all eleven | The user rejected a tuple of lists, a helper, `loop {}`, recursion, and a reverse pass. A heap-of-heads animation is still open |
| 11 trees | bst, trie | (c) binary_tree at 147 lines and test_tree; no traversal motion | An in-order, pre-order, and post-order traversal robot with a visit stack; a delete-with-two-children case |
| 12 graphs | 6 | (c) about 11 whole files mid-chapter | Excerpts only |
| 13 LRU | shelf, stamps, touch, put | Done 2026-10-01. The first arena animation changed numbers inside fixed boxes and was rejected as static. touch and put now lift the node out, re-route the arrows, and carry it to the front over a fixed Vec row | Reference: operations must move on screen |
| **14 sharding** | ring | (a) about 300 words before code; (b) no motion for lock contention on one map against N shards, or for remapping when a node joins | A "one lock, many robots queueing" against "16 shard locks" animation with throughput counters; a ring animation adding a node, where only one arc moves, against `hash % N` moving almost all keys as the fail case |
| 15 memory/OS | mem-hierarchy, false-sharing | The bump allocator and scheduler are static | A bump-pointer animation (alloc, alloc, reset); a round-robin scheduler animation |
| 16 threads/locks | spin-lock, deadlock | The condvar semaphore and poisoning are static | A semaphore with permits as tokens, sleeping and waking robots (`notify_one`); a poisoning sequence |
| 17 queues | bounded-buffer, queue-wait, queue-close, ring-spsc | Done 2026-10-01: animations for waiting on a Condvar (fail: no notify_one), closing (fail: no notify_all hangs shutdown), and the SPSC ring (fail: tail published before the slot is written); main excerpts in place, complete files in 17.8 | Reference for concurrency chapters |
| 18 pools | pool-lock, pool-panic | Backpressure and result channels are figures only | An animation of the bounded queue filling with the caller blocked, and per-job reply channels |
| 19 reliability | token-bucket, single-flight | Retry with backoff and jitter is static | A retry timeline: attempts on a time axis with exponential gaps and jitter, against a thundering herd of synchronized retries as the fail case |
| 20 sockets | bdp, handshake, epoll | Fine | None |
| 21 http | framing, keep-alive | (a) about 3,300 words; parsing limits are static | Optional: a header-size-limit animation (slowloris as the fail case) |
| 22 async | 4 | Fine | None |
| 23 to 29 (Linux) | 1 to 2 each | Excerpted already. Each has one animation. ch24 (dup2 and fork table), ch27 (TIME_WAIT), and ch29 (pool checkout and health check) would gain from a second | ch24: dup2 redirect with the fd table before and after; ch27: TIME_WAIT on the side that closes first; ch29: a stale connection discarded on checkout |
| 30 drills | none | A 522-line whole file at the top by design; stale references fixed 2026-10-01 | Optional: the lazy spawn/join animation (serial against parallel timelines), since 30.3 is the chapter's one surprise |

Process for each chapter, as done for ch13:

1. Read the chapter and the lab code. Write the intuition section first: an analogy, a cost table, and a
   hand-traced example.
2. Write `tools/anim_chNN.py` with the `motion` API: robots plus the structure, `code_panel` with
   `lines_containing`, and a fail-case chapter. Register it in `animations.py`.
3. Preview frames with `render(..., only=)`. Render in the background with the absolute script path. Run
   `anim_markup.py`.
4. Move whole files into "The complete files". Renumber captions sequentially. Fix references by hand.
   Run `excerpts.py check`, `lint_prose.py`, and `lint_figures.py`.
5. Build, commit (no attribution lines), push, and republish gh-pages.

## Code panels and unhappy paths (audit, 2026-10-01)

**Code panels.** Every animation's code panel now comes from `motion_kit.Panel` or `Panels`. Both read
contiguous ranges of the lab file with their indentation, and mark any gap with `// ...` at the right depth.
`lines_containing` and `lines_at` stripped indentation and showed `None =>` arms without their `match`. The
hand-typed panels in `anim_async`, `anim_http`, and `anim_sockets` paraphrased the code. All of these are gone.

- New panels must use `Panel(path, ranges, focus)`. The timeline keeps counting 0, 1, 2 through `focus`,
  and `Panel.at` maps those steps onto real lines.
- A panel group that walks several functions uses `Panels`. It shows the function holding the current line.
- A counterfactual variant, the code with a bug put in, is the one allowed hand-written panel. Write it in full
  with real indentation, and title it as a variant, such as "a version that advances after every node".

**Unhappy paths.** These animations had no failure chapter. All twelve now have one, built as listed, with a
struck line in the real panel. Two deviate from the plan. ch12-dijkstra shows an unreachable node: the
lazy-deletion loop re-processes a node after a negative edge, so it does not return a wrong answer. ch16-spin-lock
shows a leaked guard (`mem::forget`) in place of a Relaxed release:

| Animation | Unhappy path to add |
|---|---|
| ch03-three-sum | no skip of duplicate values: the same triplet is reported twice |
| ch03-kmp-search | a pattern that is absent: the scan reaches the end, and no restart is wasted |
| ch03-kmp-lps | resetting `len` to 0 on a mismatch instead of `lps[len - 1]`: a shorter border is missed |
| ch05-top-k | keeping every count in a max-heap: O(n log n) and n entries, against k in the min-heap |
| ch12-dfs | no visited set on a graph with a cycle: the walk revisits nodes |
| ch12-dijkstra | a negative edge: a settled node gets a shorter path later, and the answer is wrong |
| ch12-islands | not marking land as visited: one island is counted from each of its cells |
| ch12-kruskal | no union-find check: an edge inside one component closes a cycle |
| ch16-spin-lock | `Relaxed` on unlock: the next holder can read stale data (drawn as the missing pair) |
| ch17-bounded-buffer | `if` instead of `while` around `wait`: a woken consumer pops from an empty queue |
| ch19-token-bucket | no cap on refill: a long idle period allows a burst far above the rate |
| ch26-store-buffer | already a failure demo; mark its Relaxed outcome as `fail` for consistency |

**One animation per snippet.** Each code block that introduces behaviour gets a short animation after it. One
animation per section is not enough. ch09 now has eight: build, reverse, remove, replace, layouts, drop, doubly, and
pop_back. Apply the same rule to the chapters in the depth table above.

## Arrows in figures (audit, 2026-10-01)

The user reported arrows that were misaligned across the book. The ch03 Vec figure was one: its pointer left
the bottom of `ptr` at a slant, cut under `len` and `cap`, and hit the heap block at an odd angle.

**Causes.**
- Hand-drawn figures placed arrows with raw `f.arrow(x1, y1, x2, y2)` coordinates: 83 arrows in 16
  scripts, and none used `f.link`, which runs edge to edge.
- Graphviz figures with `rankdir=LR` laid records sideways, so edges looped around them. `constraint=false`
  back edges swept across the whole diagram.

**Fixed.**
- Hand-drawn figures, all now using `f.link` or rerouted:
  - `ch03-vec-layout`: the heap block now sits under the stack fields, so `ptr` points straight down at `[0]`.
  - `lru-rc-layout`: nodes zigzag, so no link crosses a node.
  - `syscall`: arrows meet box edges.
  - `graph-layout`: the pointer reaches the row-0 box; row labels moved to the right of each row.
  - `iter-dangling`: the error box moved under the code it covered.
- Graphviz figures:
  - `ch01-borrow-layout` and `ch01-lifetimes`: vertical records, straight edges into port edges.
  - `ch02-syscall`, `ch22-contract`, `ch29-pool`: back edges drawn as forward edges with `dir=back`.
  - `ch01-state-machine`: pinned with `layout=neato`.
  - `ch16-threads`: shared memory on the left, scheduler on the right.
  - `ch20-models`: a duplicate return edge removed.
  - `ch21-connection`: two parallel edges merged into one double-headed edge.

**New check.** `tools/lint_arrows.py` flags arrows that are slightly skewed, that float short of a box, that
are buried inside one, or that cross an unrelated box. The remaining hits are deliberate: arrows between
before and after panels, and arrows that point at a text label.

**Still to do.**
- The other 78 raw `f.arrow` calls pass the linter but should move to `f.link` when their chapters are
  revisited.
- Several Graphviz files are no longer used by any chapter. They are drafts:
  - ch04: `ch04-doubly`;
  - ch05: `ch05-interval`, `ch05-tail`;
  - ch06 and ch07: `ch06-serialize`, `ch06-trie`, `ch07-sample`;
  - ch08 and ch09: `ch08-jobs`, `ch08-subsets`, `ch09-arena`, `ch09-generations`;
  - ch12 to ch14: `ch12-poison`, `ch13-condvars`, `ch14-pool`.

  Delete them, or fix them before reuse.
