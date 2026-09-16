# Preface {#preface}

> What you don't use, you don't pay for. What you do use, you couldn't hand code
> any better.
>
> Bjarne Stroustrup, *Foundations of C++*, ECOOP 2012

## About the book

It can be very hard to use Rust for coding interviews if you don't have guidance. I felt
the need of having a book, being a senior engineer, who can teach the language and its
idiomatic patterns effortlessly with code that you can reproduce under pressure.

This book prepares you for those interviews and solidifies your intuition.

The code is in `rust-interview-lab`, at
<https://github.com/arpanpathak/cracking-the-systems-programming-interview>.

## What you need to know

The book assumes that you can read Rust and that you know what `Vec`, `HashMap`,
`Option` and `Result` are. Every structure the text uses is built in the text.
Every cost claim is derived on the page or measured by a program printed beside it.

## How the chapters are built

**Problem Statement.** The input, the output, and the boundary cases.

**Designing a Solution.** The mechanism the solution rests on.

**Implementation.** The file the chapter reads, followed by a reading of its
decisions.

**Intuition.** The state of the program after each step on a concrete input.

**Time and Space Complexity.** The cost of each operation, with the condition
stated in the same row when a bound depends on an assumption.

**Limitations.** The cases the code does not handle and the resources it does not
bound.

A chapter that measures rather than traces prints the program that produced the
figure.

## How the book is organised

Chapters 1 to 13 cover arrays, strings, trees, graphs, recursion and search.
Chapters 14 to 18 cover linked structures and caches. Chapters 19 to 25 cover
concurrency and the operating system. Chapters 26 to 29 cover files, directories
and command-line arguments. Chapters 30 and 31 cover coordination and parallelism.
Chapters 32 and 33 cover a running median and an in-place reversal. Chapter 34
covers idempotent operations.

Chapters 35 to 59 cover the rest of the repository: types and smart pointers (35 and
36), recursion, memory layout, and caches (37 to 42), threads and synchronization
primitives (43 to 47), performance and the operating system (48 to 50), networking and
HTTP (51 to 55), an async runtime, retries, and an HTTP client (56 to 58), and the short
interview drills (59). Chapters 60 to 62 add breadth-first and depth-first search,
Dijkstra's shortest paths, and merging k sorted lists, and chapter 63 adds Three Sum. Chapter 64 builds a thread pool in four versions.

## The repository

The code is in `rust-interview-lab`:

<https://github.com/arpanpathak/cracking-the-systems-programming-interview>

```bash
cd rust-interview-lab
cargo test                          # library and program tests
cargo run --bin count_islands
cargo run --release --bin syscall_overhead
cargo run --bin mutex_poisoning
cargo run --bin shadowing
cargo run --bin read_write_file
cargo run --bin list_directory
cargo run --bin bounded_buffer
cargo run --release --bin parallel_sum
```

The listings reproduce the files as the repository holds them. Chapter 18 prints a
test with an assertion added, and says so.

## Conventions

A trace is a table with one row per step. Where a structure needs a picture rather
than a table, boxes inside a frame are values on the stack, and boxes to the right
of the frame joined by an arrow are values on the heap. A solid arrow is a pointer
that owns what it points at; a dashed arrow is a pointer that does not.

```text
stack                          heap
+------------------+           +------------------+
| variable: value  | ----->    |  owned value     |
+------------------+           +------------------+
```

Cost tables use the usual notation. A bound that holds only under an assumption
states the assumption in the same row:

| Resource | Cost | Condition |
|---|---|---|
| Time | `O(n)` expected | the hash function distributes keys evenly |
| Space | `O(n)` | up to `n` entries |

A measured figure names the machine that produced it.

## What this book does not cover

It is not a Rust tutorial, an ecosystem survey, or a catalogue of interview
questions. The operator and the cluster work are in the repository and in the study
guides beside it.

## Acknowledgments

The claims about the Rust language and its standard library rest on the
documentation the Rust Project Developers maintain: the *Rust Book*, the *Rust
Reference*, the *Rustonomicon*, the standard library reference, and the API
Guidelines. The algorithms are attributed in each chapter and listed with their
sources in the References.

*Arpan Pathak*
