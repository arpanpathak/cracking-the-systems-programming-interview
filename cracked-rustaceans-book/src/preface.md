# Preface {#preface}

> What you don't use, you don't pay for. What you do use, you couldn't hand code
> any better.
>
> Bjarne Stroustrup, *Foundations of C++*, ECOOP 2012

## Why this book

An interview for a systems role rarely turns on whether a candidate can name the
right data structure. It turns on the sentence that follows. Why is this
representation cheaper than the other one? What does the abstraction hide, and
what does it charge for hiding it? Which input does it not survive?

Those questions are hard to practise from a list of exercises, because a list
gives the answer and leaves the reasoning out. This book works from the other
direction. It takes one repository of running Rust — data structures, caches,
concurrency primitives, and the file and network code a service needs — and reads
it the way an interviewer reads an answer: one file at a time, with the cost of
every operation and the inputs that break it written down.

## Who this book is for

The book assumes that you can read Rust and that you know what `Vec`, `HashMap`,
`Option` and `Result` are. It assumes nothing else. Every structure the text uses
is built in the text, and every cost claim is either derived on the page or
measured by a program printed beside it.

If you are preparing for a senior systems or cloud engineering interview, the
chapters are the interview slowed down: the problem statement, the design, the
implementation, the intuition, the cost, and the limits, in that order. If you are
reading for the code alone, each chapter stands on its own.

## How the chapters are built

Most chapters follow the same movements.

**Problem Statement.** The input, the output, and the boundary cases that decide
whether an answer is complete.

**Designing a Solution.** The mechanism the solution rests on, and the reason it
is correct.

**Implementation.** The file the chapter reads, followed by a reading of its
decisions.

**Intuition.** The state of the program after each step on a concrete input, as a
table or a diagram.

**Time and Space Complexity.** The cost of each operation, with the condition
stated in the same row when a bound holds only under an assumption.

**Limitations.** The cases the code does not handle, the assumptions it makes about its
input, and the resources it does not bound.

A chapter that measures rather than traces prints the program that produced the
figure, so that the number can be reproduced.

## How the book is organised

The chapters are grouped by subject. Chapters 1 to 13 cover the problems of the
standard interview repertoire: array and string work, trees, graphs, recursion and
search. Chapters 14 to 18 cover linked structures and caches, in which the deciding
question is ownership. Chapters 19 to 25 cover concurrency and the operating
system, including a program that measures the cost of a system call. Chapters 26
to 29 cover files, directories and command-line arguments. Chapters 30 and 31 cover
coordination and parallelism. Chapters 32 and 33 return to sequences with a running
median and an in-place reversal. Chapter 34 covers idempotent operations, and
Chapter 35 closes the book with the integration tests.

Read straight through for the argument, or follow one part for a topic. The index
and the cross-references in each chapter are enough to read out of order.

## The repository

The code is the repository `rust-interview-lab`. To run it:

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

The listings reproduce the files as the repository holds them. Two chapters depart
from that. Chapter 18 prints a test with an assertion added, and Chapter 35 prints
an integration test file that is no longer in the repository; both chapters say so
where they appear.

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

A measured figure names the machine that produced it, because a measurement
without its environment cannot be reproduced.

## What this book does not cover

It is not a Rust tutorial. It does not teach the language from the beginning, and
it does not survey the ecosystem. It is not a catalogue of interview questions:
the subject is the reasoning around each program, not the answer to it. And it is
not a Kubernetes or GPU manual; the operator and the cluster work live in the
repository and in the study guides beside it, not in these chapters.

## Acknowledgments

The claims about the Rust language and its standard library rest on the
documentation the Rust Project Developers maintain: the *Rust Book*, the *Rust
Reference*, the *Rustonomicon*, the standard library reference, and the API
Guidelines. The algorithms are attributed in each chapter and listed with their
sources in the References. The epigraph is Bjarne Stroustrup's statement of the
zero-overhead principle, and the quotations that follow it in the chapters are
attributed where they appear.

*Arpan Pathak*
