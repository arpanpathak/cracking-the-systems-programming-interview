# Work log: depth pass and systems backlog

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

- [ ] Part 7, the kernel boundary
  - [x] mmap and zero-copy (MAP_SHARED vs MAP_PRIVATE, first-touch faults,
        msync; sendfile vs read/write; TLS forces bytes back to user space)
  - [ ] the fd table, fork/exec, and pipes (dup2, FD_CLOEXEC, a leaked fd,
        `ls | wc -l`)
  - [ ] edge-triggered epoll (EPOLLET, drain to EAGAIN, the stall when reading
        once; EPOLLONESHOT, EPOLLEXCLUSIVE)
- [ ] Part 8, under the locks
  - [ ] futex mutex and memory-ordering litmus tests
- [ ] Part 9, production networking
  - [ ] TCP teardown: states, TIME_WAIT, CLOSE_WAIT leak, half-close
  - [ ] TLS and mTLS with rustls
  - [ ] client connection pool (bounded, RAII return, idle eviction)
- [ ] ch19: single-flight idempotency as a section

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
