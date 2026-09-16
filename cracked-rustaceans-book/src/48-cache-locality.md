# 48. Cache Locality and False Sharing {#cache-locality}

*Source files: [`src/bin/cs_locality.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/cs_locality.rs) and [`src/bin/concurrency_false_sharing.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/concurrency_false_sharing.rs). Run them with `cargo run --release --bin cs_locality` and `cargo run --release --bin concurrency_false_sharing`.*

## Problem Statement

Two experiments:

1. Sum 4,194,304 `u64` values once in index order and once in an order that jumps a
   million positions at each step. Both sums visit every element exactly once and must
   agree. Report both times.
2. Run four threads, each incrementing its own `AtomicUsize` two million times. Store
   the counters once packed next to each other and once padded to a cache line each.
   Report both times.

## Designing a Solution

**The memory hierarchy.** A processor reads memory through several levels of cache. On
the machine used for this book, a Cortex-A78AE, each core has 512 KiB of level-1 data
cache and 2 MiB of level-2 cache. Memory moves between main memory and the caches in
cache lines, 64 bytes at a time. A read of an address already in cache costs about a
nanosecond; a read that misses every level waits for main memory, which costs tens of
nanoseconds.

**Sequential access.** Walking an array in order touches one new cache line every eight
`u64` elements, and the hardware prefetcher recognises the pattern and loads the next
lines before they are needed. Almost every read is a cache hit.

**Strided access.** Stepping by 1,000,003 positions modulo the array length lands on an
unrelated cache line every time, and the prefetcher cannot predict the next address. For
an array of 32 MiB, far larger than the caches, most reads miss. Because the length is
a power of two and the stride is odd, the stride and the length are coprime, so the
walk visits every index exactly once before it repeats.

**False sharing.** Two threads that write different variables on the same cache line
still invalidate each other's cached copy of that line. Each write by one core forces
the other core to fetch the line again before its next write. Padding each counter to
64 bytes places each on its own line and removes the interference.

The diagram below shows the two counter layouts.

```text
unpadded, 8 bytes each                  padded, #[repr(align(64))], 64 bytes each

one 64-byte cache line                  line 0   [ c0 ........................ ]
[ c0 | c1 | c2 | c3 | ...... ]          line 1   [ c1 ........................ ]
  ^    ^    ^    ^                      line 2   [ c2 ........................ ]
  every write by any thread             line 3   [ c3 ........................ ]
  invalidates the line on the           each thread writes only its own line
  other three cores
```

## Implementation

### Sequential and strided sums

```rust
//! Cache locality: the same data is much faster to walk in order than to jump
//! around, because memory moves in cache lines and the prefetcher helps only the
//! sequential case.
//!
//! Run with: cargo run --bin cs_locality

use std::time::{Duration, Instant};

/// A power of two, so a stride must be odd to visit every index.
const ELEMENTS: usize = 4 * 1024 * 1024;

/// Odd, and therefore coprime with `ELEMENTS`: the walk visits every slot once.
const STRIDE: usize = 1_000_003;

fn sequential_sum(data: &[u64]) -> (u64, Duration) {
    let start = Instant::now();
    let sum = data.iter().sum();
    (sum, start.elapsed())
}

fn strided_sum(data: &[u64]) -> (u64, Duration) {
    let start = Instant::now();
    let mut index = 0usize;
    let mut sum = 0u64;
    for _ in 0..data.len() {
        index = (index + STRIDE) % data.len();
        sum = sum.wrapping_add(data[index]);
    }
    (sum, start.elapsed())
}

fn main() {
    let data: Vec<u64> = (0..ELEMENTS as u64).collect();
    println!(
        "{} elements, {} MiB",
        data.len(),
        data.len() * 8 / (1024 * 1024)
    );

    let (sequential, sequential_time) = sequential_sum(&data);
    let (strided, strided_time) = strided_sum(&data);

    println!("\n  sequential: {sequential} in {sequential_time:?}");
    println!("  strided:    {strided} in {strided_time:?}");

    // Both touch every element exactly once, so the sums must match; only the
    // access pattern differs.
    assert_eq!(sequential, strided);
    assert_eq!(sequential, ELEMENTS as u64 * (ELEMENTS as u64 - 1) / 2);

    println!("\nequal work, different pattern; timings vary by machine");
}
```

`sequential_sum` is `data.iter().sum()`. `strided_sum` advances `index` by `STRIDE`
modulo the length and adds with `wrapping_add`, which cannot overflow into a panic and
produces the same result as ordinary addition for this total.

The assertions check two facts: the two sums are equal, which proves the strided walk
visited every element once, and both equal `n(n - 1)/2` for the values `0..n`.

### Padded and unpadded counters

```rust
//! False sharing: two independent counters that land on the same cache line make
//! each other slow, because every write moves the line between cores.
//!
//! Run with: cargo run --bin concurrency_false_sharing

use std::mem::size_of;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::thread;
use std::time::{Duration, Instant};

const THREADS: usize = 4;
const ITERATIONS: usize = 2_000_000;

/// Packed by default: consecutive counters share a cache line.
struct Unpadded(AtomicUsize);

impl Unpadded {
    fn new() -> Self {
        Self(AtomicUsize::new(0))
    }

    fn increment(&self) {
        self.0.fetch_add(1, Ordering::Relaxed);
    }
}

/// Padded to a cache line, so no two counters share one.
#[repr(align(64))]
struct Padded(AtomicUsize);

impl Padded {
    fn new() -> Self {
        Self(AtomicUsize::new(0))
    }

    fn increment(&self) {
        self.0.fetch_add(1, Ordering::Relaxed);
    }
}

/// Scoped threads borrow the vector directly, so there is no `Arc` and no clone.
fn run_unpadded() -> Duration {
    let counters: Vec<Unpadded> = (0..THREADS).map(|_| Unpadded::new()).collect();
    let start = Instant::now();
    thread::scope(|scope| {
        for counter in &counters {
            scope.spawn(move || {
                for _ in 0..ITERATIONS {
                    counter.increment();
                }
            });
        }
    });
    start.elapsed()
}

fn run_padded() -> Duration {
    let counters: Vec<Padded> = (0..THREADS).map(|_| Padded::new()).collect();
    let start = Instant::now();
    thread::scope(|scope| {
        for counter in &counters {
            scope.spawn(move || {
                for _ in 0..ITERATIONS {
                    counter.increment();
                }
            });
        }
    });
    start.elapsed()
}

fn main() {
    println!("atomic:   {} bytes", size_of::<AtomicUsize>());
    println!(
        "unpadded: {} bytes (several counters per 64 byte line)",
        size_of::<Unpadded>()
    );
    println!(
        "padded:   {} bytes (one counter per 64 byte line)",
        size_of::<Padded>()
    );

    let unpadded = run_unpadded();
    let padded = run_padded();

    println!("\n{THREADS} threads x {ITERATIONS} increments, each on its own counter");
    println!("  unpadded (shared lines): {unpadded:?}");
    println!("  padded   (own line):     {padded:?}");

    assert!(size_of::<Padded>() >= 64, "padding must fill a cache line");
    assert!(unpadded.as_nanos() > 0 && padded.as_nanos() > 0);

    println!("\ntimings vary by machine; the padded run is normally the faster one");
}
```

`#[repr(align(64))]` raises the alignment of `Padded` to 64 bytes. The size of a type is
always a multiple of its alignment, so `size_of::<Padded>()` becomes 64 even though the
field is 8 bytes. In a `Vec<Padded>`, every element starts on a 64-byte boundary.

Both runs use `thread::scope` so that the threads can borrow the vector. The `move`
closure captures `counter`, a `&Unpadded` or `&Padded`, by value.

`Ordering::Relaxed` is correct for independent counters, as chapter 43 explained. The
choice of ordering does not affect the false-sharing result, which comes from the
writes to memory, not from the atomic protocol.

### False sharing inside one struct

A second program isolates the effect with two counters and no vector:
[`src/bin/false_sharing.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/false_sharing.rs). Run it with
`cargo run --release --bin false_sharing`.

```rust
use std::sync::atomic::{AtomicU64, Ordering};
use std::thread;
use std::time::{Duration, Instant};

const ITERS: u64 = 20_000_000;

/// Both counters are guaranteed to live inside one 64-byte cache line.
#[repr(align(64))]
struct SameLine {
    a: AtomicU64,
    b: AtomicU64,
}

/// Each of these occupies its own 64-byte block.
#[repr(align(64))]
struct Padded(AtomicU64);

fn time<F: FnOnce()>(f: F) -> Duration {
    let t = Instant::now();
    f();
    t.elapsed()
}

fn main() {
    // ---- 1. False sharing: two counters on the same cache line ----
    let same = SameLine { a: AtomicU64::new(0), b: AtomicU64::new(0) };

    let d1 = time(|| {
        thread::scope(|s| {
            s.spawn(|| for _ in 0..ITERS { same.a.fetch_add(1, Ordering::Relaxed); });
            s.spawn(|| for _ in 0..ITERS { same.b.fetch_add(1, Ordering::Relaxed); });
        });
    });

    // ---- 2. Padded: same work, but counters are on separate cache lines ----
    let p0 = Padded(AtomicU64::new(0));
    let p1 = Padded(AtomicU64::new(0));

    let d2 = time(|| {
        thread::scope(|s| {
            s.spawn(|| for _ in 0..ITERS { p0.0.fetch_add(1, Ordering::Relaxed); });
            s.spawn(|| for _ in 0..ITERS { p1.0.fetch_add(1, Ordering::Relaxed); });
        });
    });

    println!("same cache line (false sharing): {:?}", d1);
    println!("padded (separate lines):         {:?}", d2);
}
```

`SameLine` holds two `AtomicU64` fields, 8 bytes each, and `#[repr(align(64))]` aligns the
struct to a 64-byte boundary. Its size is rounded up to 64 bytes, so both fields are
guaranteed to start inside the same 64-byte cache line. The first experiment gives one
counter to each of two threads. The threads never touch each other's field, yet every
`fetch_add` by one thread invalidates the other core's cached copy of the line, and the
next write on that core must fetch the line again.

`Padded` wraps a single `AtomicU64` and is also aligned to 64 bytes, so `p0` and `p1` each
occupy their own 64-byte block and start on different cache lines. The second experiment
performs the same forty million increments with no shared line.

Both experiments use `thread::scope`, so the closures borrow `same`, `p0`, and `p1` from
the stack without `Arc`, and the scope joins both threads before `time` reads the clock.
`time` accepts any `FnOnce()` and returns the elapsed `Duration`.

A release build on the NVIDIA Jetson board, run three times, printed:

```text
same cache line (false sharing): 1.251460811s
padded (separate lines):         149.715657ms

same cache line (false sharing): 1.389555737s
padded (separate lines):         151.341589ms

same cache line (false sharing): 1.189698031s
padded (separate lines):         154.447719ms
```

The padded version was about eight times faster in every run, although both do exactly
the same work. The only difference is whether the two counters share a cache line.

The program assumes a 64-byte cache line, which holds for the Cortex-A78AE and most x86
processors. On a processor with 128-byte lines, such as Apple's M-series, `SameLine`
still shares a line, and `Padded` would need `#[repr(align(128))]` to separate the two
counters with certainty.

## Intuition

Release builds on the Cortex-A78AE printed:

```text
4194304 elements, 32 MiB

  sequential: 8796090925056 in 2.95291ms
  strided:    8796090925056 in 56.982884ms

equal work, different pattern; timings vary by machine
```

```text
atomic:   8 bytes
unpadded: 8 bytes (several counters per 64 byte line)
padded:   64 bytes (one counter per 64 byte line)

4 threads x 2000000 increments, each on its own counter
  unpadded (shared lines): 207.037319ms
  padded   (own line):     19.317951ms

timings vary by machine; the padded run is normally the faster one
```

The strided walk took about 19 times as long as the sequential walk, 13.6 ns per element
against 0.7 ns. The padded counters finished about 10.7 times faster than the packed
ones, although the program performs exactly the same eight million increments in both
runs.

## Time and Space Complexity

| Experiment | Time | Space |
|---|---|---|
| sequential sum | `O(n)`, about one cache miss per 8 elements before prefetching | `O(1)` |
| strided sum | `O(n)`, about one cache miss per element | `O(1)` |
| unpadded counters | `O(threads × iterations)`, with cache-line transfers on most writes | 8 bytes per counter |
| padded counters | `O(threads × iterations)` | 64 bytes per counter |

Both pairs have identical asymptotic cost. The measured differences are constant
factors, of 19 and 10.7 respectively on this machine.

## Limitations

**The locality experiment measures more than cache misses.** `data.iter().sum()` is a
loop the compiler vectorizes, adding several elements per instruction. The strided loop
cannot be vectorized, and it performs an integer division, `% data.len()`, on every
iteration because the divisor is not a constant. Part of the 19-times difference is
therefore vectorization and division. A control run that uses a stride of 1 through the
same code as `strided_sum` would separate the access-pattern cost from the loop's own
cost.

**Single runs without repetition.** Each experiment is timed once. The array is fully
written by `collect` before either timing begins, so page faults are not included, but
frequency scaling and interference from other processes are.

**The cache-line size is assumed.** 64 bytes is correct for the Cortex-A78AE and for
most x86 processors. Some processors, including Apple's M-series, use 128-byte lines,
where `align(64)` would not fully separate the counters. The `crossbeam-utils` crate's
`CachePadded` chooses the alignment per target.

**The two run functions duplicate each other.** `run_unpadded` and `run_padded` differ
only in the counter type. A generic function over a small trait with `new` and
`increment`, or over a closure that builds the counters, would remove the duplication,
as chapter 38 did for its list variants.

**Results vary with scheduling.** If the operating system places two of the four
threads on the same core, they no longer contend for a cache line in the same way. The
program does not pin threads to cores.

## Summary

- Visiting memory in order lets the prefetcher load cache lines before they are needed;
  a strided walk over a large array misses the cache on almost every read.
- On a Cortex-A78AE, the strided walk over 32 MiB took about 19 times longer than the
  sequential walk, a figure that includes vectorization and division as well as cache
  misses.
- Independent variables on the same cache line slow each other down when different
  threads write them; this is false sharing.
- `#[repr(align(64))]` puts each value on its own cache line, and made four independent
  counters about 10.7 times faster.
- Performance comparisons need a control that isolates the effect being measured.

## References

- Ulrich Drepper, "What every programmer should know about memory", 2007, Sections 3
  and 6.
- Mara Bos, *Rust Atomics and Locks*, O'Reilly Media, 2023, Chapter 2, "Understanding
  the Processor".
- The Rust Reference, [The `align` modifier](https://doc.rust-lang.org/reference/type-layout.html#the-alignment-modifiers).
- The `crossbeam-utils` crate, [`CachePadded`](https://docs.rs/crossbeam-utils/latest/crossbeam_utils/struct.CachePadded.html).
