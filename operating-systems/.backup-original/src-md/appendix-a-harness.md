# Appendix A. The Verification Harness

Every listing in this book is compiled and executed by one script:
`code/run_all.sh`. This appendix records the environment, the flags,
the special cases, and the procedure for reproducing every printed
output.

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

The warnings-as-errors flags matter: any listing that compiled with a
warning was corrected until it compiled clean. The outputs in the book
are the captures from the final run of the harness, printed verbatim
except where a line is wrapped by the page.

## A.2 How the harness works

The script compiles every C++ listing with the flags above and every
Rust listing with the Rust flags. The Rust listings that call raw
POSIX interfaces (`fork`, `mmap`, `sigaction`, and the rest) link the
`libc` rlib from `code/libc_bootstrap`; the rest use only the
standard library. Each binary then runs with its standard output and
error captured into `code/out/<name>.out`, the file the corresponding
chapter includes.

Three experiments need orchestration beyond "run and capture".

**The deadlock (Listing 6-5).** The program is expected to hang. The
harness starts it, waits one second, checks that the process is still
alive, appends that verdict to the capture, and kills it. The
"deadlocked" line in Output 6-5 is the harness's observation, not the
program's.

**The echo server (Listings 13-1 and 13-2).** The harness starts the
server in the background, runs the client twice, and waits for the
server to finish serving both. Output 13-1 is the server's log;
Output 13-2 is one client run.

**The daemons (Listings 15-1 and 15-2).** The harness starts each
daemon, polls for its pidfile, verifies the recorded PID is alive,
sends `SIGHUP`, then `SIGTERM`, and confirms the pidfile's removal
before printing the daemon's log. Outputs 15-1 and 15-2 interleave
the harness's own narration with the log.

Timing measurements (Listings 7-4, 9-1 through 9-4, 17-1, 17-2, 18-1,
18-2) vary between runs and between machines. The printed values are
one run on the machine in A.1; the chapters discuss the *shape* of
those outputs, which is stable.

## A.3 Reproducing the corpus

```bash
cd code
bash run_all.sh          # compiles everything, runs everything, writes out/*.out
```

The script requires `clang++`, `rustc`, `cargo` (once, for the `libc`
build), and a POSIX system. The macOS-specific observations are noted
where they appear: the `SIGBUS` protection fault in Chapter 7, the
`getpid` cache in Chapter 9, and the resolver order in Chapter 14.
Everything else behaves identically on Linux.

## A.4 Inventory

Fifty-four source files implement the book's listings: thirty-one
C++ files and twenty-three Rust files across chapters 3 through 18.
Chapters 1, 2, and 16 are conceptual and contain no listings; Chapter
17's accelerator section is conceptual but its false-sharing
experiment is measured. The complete map from chapter to listing is
the `code/chNN/` directory tree, one directory per chapter, with each
file named as the chapter cites it.
