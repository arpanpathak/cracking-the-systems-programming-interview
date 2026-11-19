# Preface

An operating system is the software that runs in privileged mode and owns the
machine. Everything your programs do — reading a file, starting a thread,
sending a packet, allocating memory — passes through the operating system on
the way down. This book explains that machinery from the bottom up, and it
explains it the way an engineer would: each idea is introduced as an answer to
a concrete problem, drawn as a diagram, and then demonstrated with a program
you can compile and run.

<div class="callout glance">
<span class="label">At a glance</span>

- Every chapter opens with the problem, develops the mechanism from first
  principles, and closes with a summary you can reread in two minutes.
- Every listing is real code, compiled with strict warnings-as-errors flags,
  executed on the machine described in Appendix A, with the captured output
  printed beneath it.
- Both implementation languages appear throughout: modern C++ (C++20) and
  Rust (2024 edition). The C++ listings use the standard library and POSIX;
  the Rust listings use the standard library where it reaches, and the `libc`
  crate where the operating system interface itself is the subject.

</div>

## Who this book is for

The book assumes you can write a program in one of the two languages and that
you are comfortable with pointers, arrays, and functions. It assumes nothing
about operating systems. The first two chapters build the machine model that
the rest of the book leans on; if you know that model already, read them
quickly, because later chapters refer to their diagrams by name.

The book is written for interview preparation and for working systems
engineers in the same measure. The questions an interviewer asks — what
happens in a page fault, why a mutex is not a condition variable, what a
daemon does after `fork()` — are answered here with mechanism, not slogans.

## How to read this book

Each chapter follows the same skeleton, because a consistent shape is easier
to hold in attention than a stream of prose.

1. **The problem.** A short statement of what breaks without the mechanism
   the chapter describes.
2. **The model.** First-principles development, with a diagram placed next to
   the paragraph that needs it.
3. **The code.** One or two listings per idea, alternating between C++ and
   Rust, each followed by its measured output.
4. **The summary.** Key ideas, common pitfalls, and a pointer to the next
   chapter.

Boxes are used sparingly and always mean the same thing:

<div class="callout keyidea">
<span class="label">Key idea</span>

One sentence that the surrounding section exists to justify. If you remember
nothing else from the section, remember this box.

</div>

<div class="callout experiment">
<span class="label">Experiment</span>

A small change to try against a listing. Experiments are optional but
fast; they turn reading into checking.

</div>

<div class="callout caution">
<span class="label">Watch out</span>

A place where the real behavior differs from the obvious reading, or where
production systems commonly fail.

</div>

Read in 25-minute sessions, one chapter at a time. The chapters build on each
other, but Chapters 1–2 and 7–9 form a core that the rest of the book can be
read around.

## Languages, editions, and platforms

The C++ listings target **C++20** and compile with Apple Clang 21 under
`-std=c++20 -O2 -Wall -Wextra -Werror`. The Rust listings target the **2024
edition** and compile with `rustc` 1.99 under `-D warnings -O`. The verification
machine runs macOS on an x86-64 processor; the appendix records the full
environment.

POSIX interfaces (`fork`, `mmap`, `sigaction`, `poll`, `socketpair`) behave the
same on Linux and macOS for everything this book demonstrates. Where the two
systems genuinely differ — `SIGSEGV` versus `SIGBUS` for a protection
violation, `launchd` versus `systemd`, the layout of the kernel's share of the
address space — the text says so explicitly.

## Verification

No listing in this book is illustrative. Every file under `code/` was compiled
with the flags above, executed, and its output captured by `code/run_all.sh`;
the printed outputs are those captures, reformatted only by line width. Timing
measurements vary between runs and machines, and are labeled as one run on the
verification machine. Appendix A explains how to rerun the entire corpus.

## Sources and style

The prose follows the register of the books this one draws on: Arpaci-Dusseau
and Arpaci-Dusseau's *Operating Systems: Three Easy Pieces*, Bryant and
O'Hallaron's *Computer Systems: A Programmer's Perspective*, Silberschatz,
Galvin, and Gagne's *Operating System Concepts*, Kerrisk's *The Linux
Programming Interface*, and Kirk, Hwu, and El Hajj's *Programming Massively
Parallel Processors*, whose practice of building each idea from a concrete
computation to a complete program shaped the structure of the code sections.
Where this book states a convention — a signal's default action, a file
system's on-disk order — the statement follows POSIX and the observable
behavior of the two systems in the appendix's environment, not folklore.

Terms are defined where they first appear and used with that meaning
afterward. The word *process* always means a running program with its own
address space. The word *thread* always means a schedulable stream of
instructions inside a process. The word *page* always means a fixed-size block
of virtual memory. Precision in these three words carries most of the book.
