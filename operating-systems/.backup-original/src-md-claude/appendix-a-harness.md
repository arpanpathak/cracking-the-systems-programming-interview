# Appendix A. The Verification Harness

One script, `code/run_all.sh`, compiles and runs every listing of this
book. In this appendix, we record the machine and the compiler flags that
we used, describe how the script handles the programs that need special
treatment, and explain how to produce all outputs again.

## A.1 The environment

| Item | Value |
|---|---|
| Machine | Intel Core i5-1038NG7 (Ice Lake, 4 cores / 8 threads, 2.00 GHz) |
| Memory | 16 GiB |
| System | macOS 26.6.1, Darwin kernel, x86-64 |
| Page size | 4,096 bytes |
| C++ compiler | Apple clang 21.0.0, `-std=c++20 -O2 -Wall -Wextra -Werror -pthread` |
| Rust compiler | rustc 1.99.1, `--edition 2024 -D warnings -O` |
| Rust FFI | `libc` 0.2 crate, built once by `code/libc_bootstrap` |

Both compilers treat warnings as errors, so every listing compiles without
warnings. Outputs printed in the chapters are files that our
script wrote. They are unchanged except where a long line is wrapped to
fit a page.

## A.2 How the script works

Our script first compiles every C++ listing and every Rust listing with
the flags of Section A.1. Some Rust listings call POSIX functions such as
`fork`, `mmap`, and `sigaction` directly, and these are linked with a
`libc` library that `code/libc_bootstrap` builds. All other Rust listings
use only the standard library. Next, the script runs each program and
stores its standard output and standard error in `code/out/<name>.out`.
Chapters include these files.

Three groups of programs need more than a single run.

**The deadlock (Listing 6-5).** This program is meant to hang. Our script
starts it and waits for 1 second. If the process is still alive, the
script appends a line that says so to its output and kills it. In Output
6-5, the line that contains "deadlocked" was therefore written by our
script and not by the program.

**The echo server (Listings 13-1 and 13-2).** Our script starts a server
in the background, runs a client twice, and waits until the server has
exited. Output 13-1 is the server's log, and Output 13-2 is what the first
client run printed.

**The daemons (Listings 15-1 and 15-2).** Our script starts each daemon
and waits for its pidfile to appear. It checks that a process with the
recorded PID is alive, sends `SIGHUP` and then `SIGTERM`, and checks that
the pidfile has been removed. Outputs 15-1 and 15-2 contain messages from
our script, followed by each daemon's log.

The following listings measure time: 7-4, 9-1 to 9-4, 17-1, 17-2, 18-1,
and 18-2. Their results differ from run to run and from machine to
machine. Each printed output is one run on the machine of Section A.1.

## A.3 Running the listings

```bash
cd code
bash run_all.sh          # compiles and runs every listing, writes out/*.out
```

The script needs `clang++`, `rustc`, and a POSIX system. It also needs
`cargo` once, to build the `libc` crate. Three results are specific to
macOS, and the chapters point them out: the `SIGBUS` signal for a
protection fault in Chapter 7, the stored result of `getpid` in Chapter
9, and the order of the addresses for `localhost` in Chapter 14. All
other programs behave in the same way on Linux.

## A.4 Inventory

The listings consist of 54 source files, of which 31 are C++ and 23 are
Rust. They belong to Chapters 3 to 15, 17, and 18. Chapters 1, 2, and 16
have no listings. The directory `code/chNN/` holds the files of Chapter
NN, under the names that the chapter uses.
