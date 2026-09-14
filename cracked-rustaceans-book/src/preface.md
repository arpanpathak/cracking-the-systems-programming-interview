# Preface {#preface}

> What you don't use, you don't pay for. What you do use, you couldn't hand code
> any better.
>
> Bjarne Stroustrup, *Foundations of C++*, ECOOP 2012

## What this book is

This book reads one repository of Rust, `rust-interview-lab`, one file at a time.
Each chapter covers a single file: the problem it solves, the design it uses, the
code as the repository holds it, a trace of that code on a concrete input, the
cost of each operation, and the inputs it does not handle.

The files are working programs and modules rather than fragments written for the
page. Each is short enough to read in full, and each keeps its own tests.

The repository is at
<https://github.com/arpanpathak/cracking-the-systems-programming-interview>, and
every chapter links the exact source file it reads.

## Who this book is for

The book assumes that you can read Rust and that you know what `Vec`, `HashMap`,
`Option` and `Result` are. It assumes nothing else. Every structure the text uses
is built in the text, and every cost claim is either derived on the page or
measured by a program printed beside it.

Each chapter follows the same order: the problem statement, the design, the
implementation, a worked example, the cost, and the limits. Read straight through,
or read one chapter on its own; each stands alone.

## How the chapters are built

Most chapters have the same sections.

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
median and an in-place reversal. Chapter 34 covers idempotent operations.

Read straight through for the argument, or follow one part for a topic. The index
and the cross-references in each chapter are enough to read out of order.

## The repository

The code is in `rust-interview-lab`, in this repository:

<https://github.com/arpanpathak/cracking-the-systems-programming-interview>

To run it:

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
test with an assertion added, and says so where it appears.

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
