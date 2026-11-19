
# Preface

An operating system is software that runs in privileged mode and controls the
hardware of a computer. Reading a file, starting a thread, sending a packet,
and allocating memory are all requests that a program makes to its operating
system. In this book, we explain how an operating system serves those
requests, starting from the hardware and working upward. We introduce each
mechanism with a problem that it solves, draw it as a figure, and then
demonstrate it with a program that you can compile and run.

## Who this book is for

You should be able to write a program in C++ or Rust and be comfortable with
pointers, arrays, and functions. No knowledge of operating systems is
required. Chapters 1 and 2 describe the machine model used in all later
chapters.

The book is intended for engineers who work on systems software and for
engineers who are preparing for systems interviews. Typical interview
questions ask what happens during a page fault, how a mutex differs from a
condition variable, and what a daemon does after it calls `fork()`. We answer
such questions by describing the mechanism involved.

## Organization of a chapter

1. **Problem.** What fails when the mechanism is absent.
2. **Model.** The mechanism, developed from first principles and drawn in a
   figure.
3. **Code.** One or two listings for each idea, in C++ and in Rust, each
   followed by its measured output.
4. **Summary.** The main ideas and common mistakes.

Three kinds of boxes appear in the text.

<div class="callout keyidea">
<span class="label">Key idea</span>

The main result of a section, in one or two sentences.

</div>

<div class="callout experiment">
<span class="label">Experiment</span>

A small change to a listing that you can try on your own machine. Each one
takes a few minutes.

</div>

<div class="callout caution">
<span class="label">Watch out</span>

A case in which actual behavior differs from what a first reading suggests,
or a mistake that is common in production systems.

</div>

Chapters 1, 2, 7, 8, and 9 form a core. After that core, most other chapters
can be read in any order.

## Languages, editions, and platforms

C++ listings target **C++20**. We compiled them with Apple Clang 21 and the
flags `-std=c++20 -O2 -Wall -Wextra -Werror`. Rust listings target the **2024
edition**. We compiled them with `rustc` 1.99 and the flags `-D warnings -O`.
C++ listings use the standard library and POSIX. Rust listings use the
standard library where it is sufficient, and the `libc` crate where the
operating system interface is itself the subject. Our verification machine
runs macOS on an x86-64 processor, and Appendix A records its full
environment.

For every program in this book, the POSIX interfaces involved (`fork`,
`mmap`, `sigaction`, `poll`, `socketpair`) behave identically on Linux and
macOS. A few behaviors do differ between the two systems. Examples are the
signal raised for a protection violation (`SIGSEGV` or `SIGBUS`), the service
manager (`systemd` or `launchd`), and the position of kernel memory in an
address space. We point out each such difference where it arises.

## Verification

We compiled and ran every file under `code/` with the flags listed above. A
script, `code/run_all.sh`, captured the output of each program, and those
captures are the outputs printed in this book. We changed only their line
width. Timing measurements vary from run to run and from machine to machine,
so we label each one as a single run on the verification machine. Appendix A
explains how to run all programs again.

## Sources

This book draws on five textbooks: *Operating Systems: Three Easy Pieces* by
Arpaci-Dusseau and Arpaci-Dusseau, *Computer Systems: A Programmer's
Perspective* by Bryant and O'Hallaron, *Operating System Concepts* by
Silberschatz, Galvin, and Gagne, *The Linux Programming Interface* by
Kerrisk, and *Programming Massively Parallel Processors* by Kirk, Hwu, and
El Hajj. Statements about standard behavior, such as the default action of a
signal, follow POSIX and what we observed on the two systems of Appendix A.

## Three recurring terms

Three terms recur in almost every chapter, and each builds on the one
before it. A *process* is a running program together with an address space
of its own. Inside that address space run one or more *threads*, each a
sequence of instructions that the scheduler can run independently of the
others. The memory that these threads share is divided into *pages*,
fixed-size blocks of virtual memory that the operating system maps and
protects individually.
