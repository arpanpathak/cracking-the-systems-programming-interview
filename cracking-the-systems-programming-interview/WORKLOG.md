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
