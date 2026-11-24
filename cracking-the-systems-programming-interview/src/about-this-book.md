# About this book

This book addresses systems programming in Rust.

Systems programming encompasses software that operates directly against hardware and operating system interfaces: data structures whose memory layout governs cache behavior, concurrent programs that coordinate shared state across threads, and network services that parse and transmit bytes over sockets. Writing reliable software at this layer requires understanding how memory is allocated and accessed by the processor, how the operating system schedules threads, and how data crosses the kernel and network boundaries.

Rust provides direct control over memory layout and execution cost while enforcing memory and thread safety at compile time. Whenever the compiler rejects an unsafe pattern in this text, we analyze the exact invariant that failed and the design change required to satisfy it.

The material progresses from foundational language mechanics to production systems primitives. The opening chapters establish bindings, file I/O, and standard collections. The middle chapters implement core data structures and analyze their memory footprints. The later chapters cover concurrency, networking, kernel interfaces, and production transport protocols. Each chapter introduces the underlying mechanism first, traces a concrete example by hand, walks through the implementation incrementally, and concludes with the complete, compilable program.

Several programs appear in multiple iterations. When an initial design exhibits a correctness bug or performance bottleneck, we diagnose the root cause and trace the structural change in the revised version.

## Who should read this book

This book is written for programmers who have basic familiarity with Rust and want to apply it to systems engineering.

Readers should be comfortable with `fn`, `let`, `if`, `match`, `struct`, `enum`, `Vec`, and `String`, and should have prior exposure to ownership and borrowing (for example, from *The Rust Programming Language*). Prior knowledge of explicit lifetime annotations, trait implementations such as `TryFrom`, smart pointers (`Rc`, `Arc`), atomics, `unsafe` Rust, or `async` runtimes is unnecessary; each mechanism is introduced in the chapter that first requires it.

No prior background in operating systems or networking is assumed. Whenever a chapter relies on a hardware or kernel mechanism, such as CPU cache lines, virtual memory paging, or file descriptors, that concept is derived from first principles before it appears in code.

## What you will learn

Working through this book builds the ability to:

- apply Rust collections and iterators to algorithmic problems over arrays, strings, and associative maps
- design domain types that enforce invariants and reject invalid state at program boundaries
- implement linked lists, trees, graphs, and caches in safe Rust
- choose between `Box`, `Rc`, and arena-backed vectors (`Vec`) for node-based data structures
- evaluate data structures with statistically sound, reproducible benchmarks
- analyze how CPU caches, false sharing, and page faults govern runtime performance
- construct locks, concurrent queues, and thread pools from atomics and condition variables
- parse network protocols safely and build servers backed by OS threads and `epoll`
- trace how an asynchronous executor drives a `Future` to completion

## How this book is organized

The book is organized into ten parts, each building on the mechanisms introduced earlier.

**Part 1, First steps**

- Chapter 1 covers bindings, shadowing, functions, recursion, and loops, and benchmarks three implementations of Fibonacci numbers.
- Chapter 2 covers files, directories, and command-line arguments, along with `Result` and the `?` operator.

**Part 2, Collections and algorithms**

- Chapter 3 applies vectors, strings, and hash maps to foundational array and text algorithms.
- Chapter 4 details iterators, references, and explicit lifetime annotations.
- Chapter 5 covers binary heaps and priority-ordered collections.
- Chapter 6 covers recursion and dynamic programming, concluding with workloads that leverage GPU memory and parallel cores.

**Part 3, Modeling data and ownership**

- Chapter 7 designs types that reject invalid values using structs, enums, and structured error types.
- Chapter 8 covers pointer and ownership types: `Box`, `Rc`, `RefCell`, `Weak`, `Arc`, and `Cow`.
- Chapter 9 implements linked lists and benchmarks four distinct storage layouts.
- Chapter 10 merges multiple sorted streams into a single ordered sequence.
- Chapter 11 covers trees and tries.
- Chapter 12 covers graph representations and traversals.

**Part 4, Memory and the machine**

- Chapter 13 implements an LRU cache and compares the performance of two node storage layouts.
- Chapter 14 partitions a cache across sharded locks and distributed nodes.
- Chapter 15 covers memory allocation, CPU caches, virtual memory paging, CPU scheduling, and system calls.

**Part 5, Concurrency**

- Chapter 16 covers operating system threads, atomic operations, and synchronization locks.
- Chapter 17 implements concurrent queues for inter-thread work distribution.
- Chapter 18 implements bounded and work-stealing thread pools.
- Chapter 19 covers rate limiting, bounded retries, and idempotent operations.

**Part 6, The network**

- Chapter 20 covers network addressing, TCP sockets, and two server architectures.
- Chapter 21 parses and serves HTTP/1.1 traffic.
- Chapter 22 implements an asynchronous executor alongside two HTTP clients.

**Part 7, The kernel boundary**

- Chapter 23 maps files into virtual memory, compares `mmap` against `read`, and transfers file data directly to sockets with `sendfile`.
- Chapter 24 inspects the process file descriptor table and constructs `ls | wc -l` using `pipe`, `fork`, `dup2`, and `execvp`.
- Chapter 25 covers edge-triggered `epoll`, the readiness stalls caused by missed edges, and kernel modes that share a single listener across threads.

**Part 8, Under the locks**

- Chapter 26 implements a futex-backed mutex, counts its kernel transitions, and runs two memory-ordering litmus tests.

**Part 9, Production networking**

- Chapter 27 traces TCP connection teardown and the socket states left behind under heavy server load.
- Chapter 28 adds TLS and mutual TLS using certificates generated at startup.
- Chapter 29 implements a bounded client connection pool with connection reuse.

**Part 10, Compact implementations**

- Chapter 30 provides ten concise implementations sized for timed technical interviews, each cross-referenced to the chapter containing its full treatment.

Appendix A provides a Rust reference sheet covering common compiler diagnostics and idioms. Appendix B contains the complete benchmark report. Appendix C preserves the extended borrow-checker derivation for Chapter 10.

## Conventions

Inline code appears in monospace font, such as `this`. Programs are presented in numbered listings, typically a few lines at a time, with each caption citing the source file and line range. Every chapter concludes with the complete listing for each program.

Program output follows the command that produced it. Benchmark measurements state the hardware on which they were recorded; absolute timings will vary across machines.

Key technical terms appear in **bold** where first defined.

Three callout styles appear throughout the text:

<div class="callout note" markdown="1">

**NOTE:** Supplementary background or implementation detail that is optional for following the main narrative.

</div>

<div class="callout tip" markdown="1">

**TIP:** A practical engineering technique ready for direct application.

</div>

<div class="callout warning" markdown="1">

**WARNING:** A subtle failure mode that compiles cleanly, or runtime behavior that diverges from common expectations.

</div>

Each chapter concludes with a concise summary and a set of exercises.

## About the code

All source code resides in the `rust-interview-lab` directory of the repository at
<https://github.com/arpanpathak/cracking-the-systems-programming-interview>. The codebase targets Rust edition 2024
and builds with `rustc 1.96.0`. Listings in the text are included directly from the source files without modification.

Library modules with unit tests live under `src/problems/`, runnable binaries live under `src/bin/`, and the data
structures benchmarked in Chapters 9 and 13 live under `benchmarking_examples/`.

Execute the test suites and binaries from the `rust-interview-lab` directory:

```bash
cargo test --lib                        # the library's unit tests
cargo test --bin http_server            # the tests inside one program
cargo run --bin tcp_echo_server         # run one program
cargo run --release --bin benchmark     # benchmarks, always in release mode
```

## Building the book

The book sources reside in the `cracking-the-systems-programming-interview` directory:

```bash
make art        # the chapter plates and the cover (needs rsvg-convert)
make figures    # the diagrams (needs Graphviz)
make html       # the browser edition, in book/
make pdf        # the print edition, in build/
make serve      # the browser edition at http://localhost:3000
```
