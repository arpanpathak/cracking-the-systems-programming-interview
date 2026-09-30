# About this book

This book is about systems programming in Rust.

By systems programming I mean programs that work close to the computer's hardware and operating system.
Data structures that decide how bytes are laid out in memory are one example. Threads that share work are
another, and so are servers that read requests from a network connection. For programs like these, you
need to know what happens underneath your code. That includes how memory is allocated and how the
processor reads it. It also includes how the operating system runs threads and moves data across a network.

I use Rust because it lets you control these details. Its compiler also checks how your program uses
memory and threads before the program runs. When the compiler rejects a program in this book, I explain
what it found.

The book starts with small things and builds up. The first chapters cover bindings, files, and
collections. The middle chapters build data structures and look at how they use memory. The later
chapters add threads, and then the network. In each chapter I introduce an idea in plain terms and work
through a small example by hand. Only then do I show the code, a few lines at a time. Each chapter ends
with the complete program.

Some programs appear in more than one version. When an early version has a problem, I show how the
problem was found and what the next version changes.

## Who should read this book

This book is for a programmer who has written some Rust and wants to use it for systems work.

You should know `fn`, `let`, `if`, `match`, `struct`, `enum`, `Vec`, and `String`. You should have met
ownership and borrowing, for example in *The Rust Programming Language*. You do not need to know
lifetimes in signatures, trait implementations such as `TryFrom`, `Rc`, `Arc`, atomics, `unsafe`, or
async. Each of these is introduced in the chapter that first needs it.

No knowledge of operating systems or networking is assumed. When a chapter relies on a hardware or kernel
detail, such as a cache line or a page fault, it explains that detail first.

## What you will learn

After working through the book, you will be able to

- use Rust's collections and iterators to solve problems on arrays, strings, and maps
- design types that reject invalid values where input enters a program
- implement linked lists, trees, graphs, and caches in safe Rust
- choose between `Box`, `Rc`, and a `Vec` of nodes to store linked data
- measure a data structure with a benchmark you can trust
- explain how CPU caches, false sharing, and page faults affect a running program
- build locks, queues, and thread pools from atomics and condition variables
- parse a network protocol safely and write a server with threads and with epoll
- explain how an async executor runs a `Future` to completion

## How this book is organized

The book has seven parts. Each part builds on the ones before it.

**Part 1, First steps**

- Chapter 1 covers bindings, shadowing, functions, recursion, and loops, and times three ways of
  computing Fibonacci numbers.
- Chapter 2 covers files, directories, and command-line arguments, and introduces `Result` and `?`.

**Part 2, Collections and algorithms**

- Chapter 3 solves problems with vectors, strings, and hash maps.
- Chapter 4 explains iterators and references, and introduces lifetimes.
- Chapter 5 uses heaps and sorted collections.
- Chapter 6 covers recursion and dynamic programming.

**Part 3, Modeling data and ownership**

- Chapter 7 builds types that reject invalid values, with structs, enums, and error types.
- Chapter 8 covers the pointer types `Box`, `Rc`, `RefCell`, `Weak`, `Arc`, and `Cow`.
- Chapter 9 builds linked lists.
- Chapter 10 merges many sorted lists into one.
- Chapter 11 covers trees and tries.
- Chapter 12 covers graphs.

**Part 4, Memory and the machine**

- Chapter 13 builds an LRU cache and measures two ways of storing its nodes.
- Chapter 14 splits a cache across locks and across machines.
- Chapter 15 covers allocation, CPU caches, paging, scheduling, and system calls.

**Part 5, Concurrency**

- Chapter 16 covers threads, atomics, and locks.
- Chapter 17 builds queues that threads use to pass work.
- Chapter 18 builds thread pools.
- Chapter 19 covers rate limiting, retries, and operations that are safe to repeat.

**Part 6, The network**

- Chapter 20 covers addresses, TCP, and two designs for a server.
- Chapter 21 parses and serves HTTP/1.1.
- Chapter 22 builds an async executor and two HTTP clients.

**Part 7, Compact implementations**

- Chapter 23 compares short versions of earlier programs with their full versions.

Appendix A lists common Rust compile errors and their fixes. Appendix B is the report on the benchmarks in
chapters 9 and 13.

## Conventions

Code in the text looks like `this`. Programs are introduced in numbered listings, usually a few lines at a
time. Each caption names the source file and the lines it shows. At the end of each chapter, the complete
program appears as one listing.

Output from a program follows the command that produced it. Timings name the machine they were measured
on. They will differ on yours.

A term is printed in **bold** where it is defined.

Three kinds of callouts appear in the text:

<div class="callout note" markdown="1">

**NOTE:** Background or detail you do not need to follow the main text.

</div>

<div class="callout tip" markdown="1">

**TIP:** A technique you can apply directly.

</div>

<div class="callout warning" markdown="1">

**WARNING:** A mistake that compiles, or behavior that differs from what you might expect.

</div>

Each chapter ends with a summary and a few exercises.

## About the code

The programs are in the `rust-interview-lab` directory of the repository at
<https://github.com/arpanpathak/cracking-the-systems-programming-interview>. They use Rust edition 2024
and were built with `rustc 1.96.0`. The listings are taken from the source files without changes.

Library code with unit tests is in `src/problems/`. Runnable programs are in `src/bin/`. The data
structures measured in chapters 9 and 13 are in `benchmarking_examples/`.

Run the programs from the `rust-interview-lab` directory:

```bash
cargo test --lib                        # the library's unit tests
cargo test --bin http_server            # the tests inside one program
cargo run --bin tcp_echo_server         # run one program
cargo run --release --bin benchmark     # benchmarks, always in release mode
```

## Building the book

The book's source is in the `cracking-the-systems-programming-interview` directory:

```bash
make art        # the chapter plates and the cover (needs rsvg-convert)
make figures    # the diagrams (needs Graphviz)
make html       # the browser edition, in book/
make pdf        # the print edition, in build/
make serve      # the browser edition at http://localhost:3000
```
