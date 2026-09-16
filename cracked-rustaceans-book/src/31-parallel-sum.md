# 31. Parallel Sum {#parallel-sum}

*Source file: [`src/bin/parallel_sum.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/parallel_sum.rs). Run it with
`cargo run --release --bin parallel_sum`, optionally followed by the thread count
and the element count.*

## Problem Statement

Sum a large array twice, once on one thread and once on several, and check that
the two results agree. The program is a measurement as much as a demonstration:
the same work is done with three element types so that the effect of the element
size on the parallel speedup is visible.

## Designing a Solution

`thread::scope` creates a scope that waits for every thread spawned inside it,
and it lets those threads borrow values from the surrounding stack. That is why
the chunks can be `&[T]` slices of one array rather than `Arc<Vec<T>>` clones:
the scope's lifetime covers the borrow, so no `'static` bound is needed.

The work is divided by position, not by value. Each thread receives an index,
computes the half-open range `[start, end)`, and sums that slice. The last thread
takes everything after its start, which covers the array when its length is not a
multiple of the thread count. The partial sums are then reduced in order with
`sum()`.

The result is order-independent because integer addition is associative here. The
same structure with floating-point addition would not be bit-for-bit reproducible,
because the grouping would change the rounding.

## Implementation

```rust
use std::env;
use std::thread;
use std::time::{Duration, Instant};

const SIZE: usize = 1_000_000_000;

fn seq_i32(data: &[i32]) -> (i32, Duration) {
    let t = Instant::now();
    let sum = data.iter().sum::<i32>();
    (sum, t.elapsed())
}

fn par_i32(data: &[i32], n: usize) -> (i32, Duration) {
    let t = Instant::now();
    let sum = thread::scope(|s| {
        let handles: Vec<_> = (0..n)
            .map(|i| {
                s.spawn(move || {
                    let chunk = data.len() / n;
                    let start = i * chunk;
                    let end = if i == n - 1 { data.len() } else { start + chunk };
                    data[start..end].iter().sum::<i32>()
                })
            })
            .collect();
        handles.into_iter().map(|h| h.join().unwrap()).sum::<i32>()
    });
    (sum, t.elapsed())
}

fn seq_i64(data: &[i64]) -> (i64, Duration) {
    let t = Instant::now();
    let sum = data.iter().sum::<i64>();
    (sum, t.elapsed())
}

fn par_i64(data: &[i64], n: usize) -> (i64, Duration) {
    let t = Instant::now();
    let sum = thread::scope(|s| {
        let handles: Vec<_> = (0..n)
            .map(|i| {
                s.spawn(move || {
                    let chunk = data.len() / n;
                    let start = i * chunk;
                    let end = if i == n - 1 { data.len() } else { start + chunk };
                    data[start..end].iter().sum::<i64>()
                })
            })
            .collect();
        handles.into_iter().map(|h| h.join().unwrap()).sum::<i64>()
    });
    (sum, t.elapsed())
}

fn seq_i128(data: &[i128]) -> (i128, Duration) {
    let t = Instant::now();
    let sum = data.iter().sum::<i128>();
    (sum, t.elapsed())
}

fn par_i128(data: &[i128], n: usize) -> (i128, Duration) {
    let t = Instant::now();
    let sum = thread::scope(|s| {
        let handles: Vec<_> = (0..n)
            .map(|i| {
                s.spawn(move || {
                    let chunk = data.len() / n;
                    let start = i * chunk;
                    let end = if i == n - 1 { data.len() } else { start + chunk };
                    data[start..end].iter().sum::<i128>()
                })
            })
            .collect();
        handles.into_iter().map(|h| h.join().unwrap()).sum::<i128>()
    });
    (sum, t.elapsed())
}

fn main() {
    let n: usize = env::args()
        .nth(1)
        .and_then(|s| s.parse().ok())
        .unwrap_or(8);

    {
        let data: Vec<i32> = vec![1; SIZE];
        let (s1, t1) = seq_i32(&data);
        let (s2, t2) = par_i32(&data, n);
        assert_eq!(s1, s2);
        println!("i32   seq sum = {s1}, elapsed = {t1:?}");
        println!("i32   par sum = {s2}, elapsed = {t2:?}  (n = {n})");
    }

    {
        let data: Vec<i64> = vec![1; SIZE];
        let (s1, t1) = seq_i64(&data);
        let (s2, t2) = par_i64(&data, n);
        assert_eq!(s1, s2);
        println!("i64   seq sum = {s1}, elapsed = {t1:?}");
        println!("i64   par sum = {s2}, elapsed = {t2:?}  (n = {n})");
    }

    {
        let data: Vec<i128> = vec![1; SIZE];
        let (s1, t1) = seq_i128(&data);
        let (s2, t2) = par_i128(&data, n);
        assert_eq!(s1, s2);
        println!("i128  seq sum = {s1}, elapsed = {t1:?}");
        println!("i128  par sum = {s2}, elapsed = {t2:?}  (n = {n})");
    }
}
```

`assert_eq!(s1, s2)` is the correctness check. It is what makes the program a
test as well as a demonstration: if the chunk boundaries overlapped or left a gap,
the two sums would differ.

The three blocks are separate so that each array is dropped before the next is
allocated. `SIZE` is one billion, so the `i128` array alone is sixteen gigabytes;
the blocks keep the peak at one array rather than three.

## Intuition

With `n = 4` and `data.len() = 10`, the ranges each thread receives are:

```text
thread   chunk   start   end     elements
0        2       0       2       2
1        2       2       4       2
2        2       4       6       2
3        2       6       10      4        (the last thread takes the remainder)

partial sums   a  b  c  d
reduction      ((a + b) + c) + d
```

The four sub-slices partition `0..10`, and the last range is longer because it
absorbs the remainder.

## Time and Space Complexity

| Resource | Cost | Condition |
|---|---|---|
| Time | `O(n)` additions | independent of the thread count |
| Threads | `O(threads)` stacks | each thread has its own stack |
| Memory | `O(n)` elements in the array, `O(threads)` for the partial sums | the input is not partitioned |
| Speedup | at most `min(threads, cores)` | the reduction adds a small serial tail |

The sequential sum is memory-bound: each element is read once and nothing else is
done with it. Adding threads divides the arithmetic, but not the memory traffic,
so the speedup saturates once the bus or the cache hierarchy is saturated. The
three element types are in the file to make that visible: the `i128` pass does
more arithmetic per byte than the `i32` pass, so it scales differently even on the
same machine.

## Limitations

**The default size needs a large machine.** One billion elements is four gigabytes
for `i32`, eight for `i64`, and sixteen for `i128`. The program was written for a
workstation and it will exhaust memory on a smaller host; the size is not a
parameter, only the thread count is.

**The timing has no warm-up and one pass.** `Instant::now()` is called once per
function, so the first touch of each page and any frequency scaling are inside
the measurement. A measurement intended to be quoted needs a warm-up and several
repetitions, as the benchmark harness in this repository does.

**More threads than cores do not help.** The thread count defaults to eight and
is taken from the first argument. Nothing reads the available parallelism, so on
a smaller machine the extra threads contend for cores rather than adding work.

**The chunking is unbalanced.** `data.len() / n` is the same for every thread
except the last, which takes the remainder. When `n` is close to the length, the
last thread does most of the work. A balanced split would distribute the
remainder one element at a time.

**The array is not partitioned or aligned for the access pattern.** Each thread
reads a contiguous range, which is the friendly case. A false-sharing problem
would appear if threads wrote partial sums into adjacent fields of one object,
which this program avoids by returning each sum through `join`.

## Summary

- `thread::scope` allows the workers to borrow the input, which removes the
  `Arc<Vec<T>>` the naive version would need.
- Dividing by index gives each thread a disjoint half-open range, and the last
  range absorbs the remainder so that the whole array is covered.
- The correctness check is the equality of the two sums; a boundary error makes
  the program fail rather than print a wrong number.
- The measured speedup is bounded by memory bandwidth, which is why the element
  type is part of the experiment.

## References

- Standard library, [`thread::scope`](https://doc.rust-lang.org/std/thread/fn.scope.html).
- Standard library, [`Instant`](https://doc.rust-lang.org/std/time/struct.Instant.html).
- Standard library, [`Iterator::sum`](https://doc.rust-lang.org/std/iter/trait.Iterator.html#method.sum).
