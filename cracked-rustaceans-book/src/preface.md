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
Every cost claim is derived on the page or measured by a program the chapter names,
with the figure it produced reproduced beside the claim.

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

A chapter that measures rather than traces prints the figure its program produced,
together with the conditions under which it was measured.

**Summary.** What the chapter establishes, and where the same mechanism appears
again.

## How the code is cited

A chapter does not reprint the file it reads. Each Implementation section opens with
one or more listing references, numbered by chapter, which name the file and link to
it in the repository:

<p class="listing"><span class="listing-label">Listing 11.1</span> The complete module, with its tests. <code>src/problems/graph_topology.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/graph_topology.rs">read the file on GitHub</a></p>

The reading that follows a reference quotes the expressions it discusses, so the
argument can be followed without the file open, and the file itself is the one the
compiler and the tests see. Nothing can drift between the two, which is the reason
for the arrangement: a printed copy of a program is out of date the first time the
program is changed. Short excerpts still appear in the text where a few lines make a
point that prose alone would labour.

## How the book is organised

The chapters are grouped into fifteen parts. Parts I to VI cover the data structures
and the algorithms: sequences and maps, stacks and queues, linked structures, trees
and tries, graphs, and recursion with dynamic programming. Part VII covers the type
system, ownership, and the smart pointers, which is where the language stops being
incidental to the answer. Part VIII covers caches and memory layout, and it is the
first part in which claims are measured rather than derived.

Parts IX and X cover threads, the synchronization primitives built from them, and what
the hardware and the operating system charge for both. Parts XI to XIII cover the
practical surfaces: files and directories, sockets and HTTP, and asynchronous Rust with
the clients built on it. Part XIV covers the behaviour expected of a service under
load and under failure. Part XV is a set of short drills.

The parts are ordered so that the book can be read from the front, but a chapter is
self-contained: it names the file it reads, states its own assumptions, and cites the
chapters it depends on. The chapter numbers are the order in which the chapters were
written rather than the order in which they are read, and they are kept stable so that
a reference to a chapter, from the index or from outside the book, continues to
resolve.

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
