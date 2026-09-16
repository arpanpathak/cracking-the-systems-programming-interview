# 24. Syscall Overhead {#syscall-overhead}

*Source file: [`src/bin/syscall_overhead.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/syscall_overhead.rs). Run it with
`cargo run --release --bin syscall_overhead`.*

> Latency lags bandwidth.
>
> David A. Patterson, *Latency lags bandwidth*, Communications of the ACM
> 47(10), 2004

## Problem Statement

The cost of crossing from user space into the kernel is measured on one machine,
and the figure is reported in a form that can be reproduced.

## Designing a Solution

Every system call is a controlled transfer of control: the processor switches to
kernel mode, the kernel validates the arguments, does the work, checks whether the
calling thread should be descheduled, and returns. For a call that does almost
nothing, that machinery is the entire cost.

`getpid` is such a call. It returns the caller's process identifier from a field
the kernel already holds, takes no arguments, and touches no user memory. Its cost
is therefore close to the irreducible price of the boundary itself, which is why it
is the standard probe.

The measurement has three parts, and each exists because of a way a benchmark can
lie.

```text
warm-up        run the call 100 000 times without timing it
               the first calls fault in pages and ramp the clock

timing         read the clock, run the call 10 000 000 times, read the clock
               the loop body is one call, so the elapsed time per iteration is
               the cost of the call plus the cost of the loop

division       elapsed nanoseconds / iterations
               the result is an average, and the spread is not reported
```

## Implementation

<p class="listing"><span class="listing-label">Listing 24.1</span> The complete program, with its tests. <code>src/bin/syscall_overhead.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/syscall_overhead.rs">read the file on GitHub</a></p>

Three parts of this file need comment.

**The `SAFETY` comments** state the obligation: no pointer arguments, no memory
side effects, and an FFI declaration that matches the kernel ABI. That is what an
`unsafe` block's comment is for, the reasoning that justifies the claim that the
block cannot cause undefined behaviour.

The comment in `measure_getpid_ns_per_call` also mentions `black_box`, and the code
does not call `black_box`. The call would be the right thing to do: without it, the
loop's result is unused, and the optimiser is entitled to remove work whose result
nobody observes. What prevents removal today is that a call through `libc` is
opaque to the optimiser, an external function call is a side effect it cannot
delete, so the loop survives, and the comment describes an intention rather than
the code. `std::hint::black_box(libc::getpid())` would make the code match its
comment.

**The trailing space after the `unsafe` block in the warm-up loop** is present in the
source and invisible on a rendered page. It is noted here because it is the kind of
difference a reader comparing the chapter with the file would otherwise stop at.

**The final projection** multiplies the measured cost by ten million calls per
second and divides by a billion, which yields a figure in CPU-seconds per second.
A result above 1.0 means that one core cannot sustain that rate: the arithmetic is
saying that the kernel crossing alone would need more than one core's worth of
time.

## Intuition

Run on an AArch64 Linux machine, release build, with `rustc` 1.96.0-nightly, while
no other work was running on the machine:

```text
Iterations:      10000000
Total time:      2.076s
Per syscall:     207.6 ns
At 10M calls/s, syscall overhead would consume: 2.08 CPU-seconds per second
```

The last line is the answer to the question this program exists to raise. A service
that makes one such call per request at ten million requests per second needs more
than two cores doing nothing but crossing the boundary.

Two qualifications belong with the number. The machine is a development board with
a specific kernel, and a different machine will produce a different figure; the
program prints its platform for that reason. And `getpid` is cheaper than most
system calls: a read or a write copies data and an `open` walks the file system, so
the number here is a floor for the boundary and not a typical cost.

## Time and Space Complexity

| Resource | Cost |
|---|---|
| Time | one clock read per measurement, one system call per iteration |
| Space | `O(1)`; nothing is allocated |

## Limitations

**The loop is not empty, so the measurement includes it.** A call, a bounds check
that the optimiser removes, and an increment are part of every iteration. For a
200-nanosecond system call the loop's own cost is a rounding error, and for the
control measurement of an empty loop it is the whole measurement. The program has
no control row, so the loop's cost is not reported separately.

**The average hides the distribution.** One number cannot show that a call takes
150 nanoseconds in the common case and a microsecond occasionally, which is what an
interference-heavy machine produces. The minimum of several batches is the value
least disturbed by other activity on the machine, and the program does not
compute it.

**`getpid` may be served without a trap on some architectures.** Some kernels
implement particular calls through a vDSO shared page that the process reads
directly, which turns a system call into a memory read. The program measures what
the call costs on this kernel, and the figure is a boundary cost only if the kernel
traps.

**The program builds the library it links against, and the library emits a
warning.** Running `cargo run --bin syscall_overhead` prints a `dead_code` warning
for an unused function in the library. The warning comes from `merge_intervals2`,
which Chapter 5 identifies, and it appears in this chapter's output because Cargo
compiles the whole crate.

## Summary

- `getpid` gives a floor for the cost of crossing the process boundary. It is not
  the cost a service would see per request.
- The first iterations pay for page faults, for lazy symbol resolution, and for a
  clock that has not reached its steady frequency, so the run includes a warm-up
  pass.
- The figure converts into a consequence. At 207 nanoseconds per call and ten
  million calls per second, the boundary alone consumes two cores.
- Two measurements would strengthen the result: a control measurement of the empty
  loop, and the minimum over several batches. Neither is present.

## References

- `libc`, [`getpid`](https://docs.rs/libc/latest/libc/fn.getpid.html).
- Standard library, [`std::time::Instant`](https://doc.rust-lang.org/std/time/struct.Instant.html).
- Standard library, [`std::hint::black_box`](https://doc.rust-lang.org/std/hint/fn.black_box.html).
- David A. Patterson, "Latency lags bandwidth", *Communications of the ACM* 47(10),
  2004, pages 71–75.
