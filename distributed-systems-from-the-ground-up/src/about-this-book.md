# About this book

A distributed system is a set of programs on separate machines that work together
over a network and present themselves to their users as a single service. The
machines are not reliable. Any of them may stop at any moment, a disk may be lost, and
a message may arrive late, twice, or not at all. This book is about designing services
that keep their promises while such things are happening, and about understanding
exactly which promises can be kept.

It has 2 parts, of different character.

The first part designs and builds a single system from its foundations, a key-value
store that runs on many machines. Chapter 1 is its system design: the requirements,
the interfaces, the components, and the reasoning about sharding, replication and
failure. Chapters 2 to 6 are its low-level design, in which each component is written
in Rust, measured, and subjected to the failures it is claimed to survive. These are
the chapters that print code. The ideas established here, the log, the majority, the
leader, the lease and the conditional write, are the vocabulary of everything that
follows.

The second part consists of system designs, each complete in itself: a rate limiter,
a cache, a message queue, a payment system, a chat service, an exchange and others.
Each begins from what the system is for, considers the algorithms and arrangements
that could serve, and explains why one is chosen and what it costs. Where an
algorithm proceeds in steps, a picture shows it step by step, at the reader's own
pace. These chapters print no code. Every one of them has a small simulation in the
book's repository, which produced the figures the chapter quotes, and which the
reader is encouraged to run and to alter.

## Running the code

The programs are in `code/`, a Cargo workspace. They use the Rust 2024 edition and are
built with Rust 1.99.0, which `code/rust-toolchain.toml` selects.

```console
$ cd code
$ cargo build --release
$ cargo run -p crashsim
$ cargo run -p ratelimit
```

The programs run on any Linux machine. A single small board is enough for all of
them, and 2 or 3 boards or cloud machines on a network make it possible to stop a
real machine and watch the system continue. The measurements quoted in the book were
taken on an NVMe disk, and timings on other machines will differ.

## What we assume

We assume that the reader has used a Linux shell, `curl` and HTTP. The first part
assumes in addition that the reader can read Rust. Every other term is explained
where it first appears, and each chapter ends with a table of the terms it
introduced.
