# 21. Worker Pool {#worker-pool}

*Source file: [`src/problems/worker_pool.rs`](../../rust-interview-lab/src/problems/worker_pool.rs). Test it with
`cargo test worker_pool`.*

## Problem Statement

Apply a function to every element of a vector using a bounded number of threads,
and return the results in the order of the input. Order matters because a caller
that reports per-item outcomes must be able to match an outcome with the item it
came from.

## Designing a Solution

Jobs carry their input index on a channel. Workers take jobs as they become free,
apply the function, and send `(index, result)` back on a second channel. Results
arrive in completion order, and the caller places each one at its index.

```text
                      job channel                result channel
inputs  ---> [(0,a), (1,b), (2,c), ...]     [(2,x), (0,y), (1,z), ...]

  worker 0 ---+
  worker 1 ---+---> take one job at a time ---> send (index, output)
  worker 2 ---+

  the caller collects the pairs and writes them into a slot vector:
  ordered[2] = x
  ordered[0] = y
  ordered[1] = z

  when every slot is filled, the ordered vector is the answer
```

The bound on concurrency is the number of workers. The bound on memory is the
number of jobs in flight, which is the input length plus the results not yet
collected.

## Implementation

```rust
//! Bounded worker pool with ordered results.
//!
//! Cloud CLIs/SDKs often fan out API calls across a bounded number of workers.
//! This example maps `Vec<T>` to `Vec<R>` with N threads and preserves input
//! order in the output. It demonstrates `Arc<Mutex<_>>`, channels, scoped
//! ownership, and panic-free dispatch.

use std::sync::{mpsc, Arc, Mutex};
use std::thread;

pub fn map_order<T, R, F>(worker_count: usize, inputs: Vec<T>, mapper: F) -> Vec<R>
where
    T: Send + 'static,
    R: Send + 'static,
    F: Fn(T) -> R + Send + Sync + 'static,
{
    assert!(worker_count > 0, "worker_count must be > 0");
    assert!(!inputs.is_empty(), "inputs must not be empty");

    let expected = inputs.len();
    let mapper = Arc::new(mapper);
    let (job_tx, job_rx) = mpsc::channel::<(usize, T)>();
    let job_rx = Arc::new(Mutex::new(job_rx));
    let (result_tx, result_rx) = mpsc::channel::<(usize, R)>();

    let mut handles = Vec::with_capacity(worker_count);
    for _worker_id in 0..worker_count {
        let mapper = Arc::clone(&mapper);
        let job_rx = Arc::clone(&job_rx);
        let result_tx = result_tx.clone();
        handles.push(thread::spawn(move || {
            loop {
                let job = {
                    let guard = job_rx.lock().expect("job_rx poisoned");
                    guard.recv()
                };
                match job {
                    Ok((idx, input)) => {
                        let output = mapper(input);
                        if result_tx.send((idx, output)).is_err() {
                            break;
                        }
                    }
                    Err(_) => break, // all senders dropped
                }
            }
        }));
    }

    // Send all jobs, then close the job channel so workers finish after draining it.
    for (idx, input) in inputs.into_iter().enumerate() {
        job_tx
            .send((idx, input))
            .expect("bounded by memory; channel only blocks until a worker receives");
    }
    drop(job_tx);

    // Drop our result sender. Only the worker clones remain, so `iter()` ends
    // after every worker exits.
    drop(result_tx);

    // Reassemble results in input order.
    let mut ordered: Vec<Option<R>> = Vec::new();
    for (idx, value) in result_rx.iter() {
        if ordered.len() <= idx {
            ordered.resize_with(idx + 1, || None);
        }
        ordered[idx] = Some(value);
    }

    for handle in handles {
        let _ = handle.join();
    }

    assert_eq!(
        ordered.len(),
        expected,
        "every job must produce exactly one result"
    );
    ordered
        .into_iter()
        .map(|value| value.expect("all results present"))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn maps_all_inputs_and_preserves_order() {
        let inputs: Vec<i32> = (0..100).collect();
        let results = map_order(4, inputs, |x| x * x);
        assert_eq!(results.len(), 100);
        for (i, value) in results.iter().enumerate() {
            assert_eq!(*value, (i as i32) * (i as i32));
        }
    }

    #[test]
    fn one_worker_works() {
        let results = map_order(1, vec![1, 2, 3], |x| x + 10);
        assert_eq!(results, vec![11, 12, 13]);
    }
}
```

`mpsc::Receiver` is single-consumer, so sharing it between workers requires
`Arc<Mutex<Receiver<_>>>`. The lock is taken inside a block and released before the
mapper runs:

```rust
let job = {
    let guard = job_rx.lock().expect("job_rx poisoned");
    guard.recv()
};
```

The guard is alive while `recv` blocks, so a worker waiting for work holds the
lock. The block ends before `mapper(input)` is called, so the mapper never runs
with the lock held, which is what keeps the pool from serialising all of its work.

`drop(job_tx)` is what tells the workers to stop. A receive on an empty channel
returns an error once every sender is dropped, so the loop breaks. `drop(result_tx)`
does the same job for the caller's own copy of the result sender: without it,
`result_rx.iter()` would wait for a sender that only the caller holds.

`ordered.resize_with(idx + 1, || None)` grows the vector on demand, so results that
arrive out of order for low indices still land in the right slots.

## Intuition

```text
map_order(2, vec![10, 20, 30], |x| x + 1)

jobs on the channel: (0, 10), (1, 20), (2, 30)

possible interleaving:
  worker 0 takes (0, 10), computes 11, sends (0, 11)
  worker 1 takes (1, 20), computes 21, sends (1, 21)
  worker 0 takes (2, 30), computes 31, sends (2, 31)

result channel delivers, in some order: (0, 11), (1, 21), (2, 31)

caller:
  ordered = []                  receives (0, 11)
  ordered.len() is 0 <= 0, so resize to 1; ordered[0] = Some(11)
  receives (1, 21)
  ordered.len() is 1 <= 1, so resize to 2; ordered[1] = Some(21)
  receives (2, 31)
  ordered.len() is 2 <= 2, so resize to 3; ordered[2] = Some(31)

every worker has dropped its result sender, so iter() ends
ordered.len() == 3 == expected
flattened: [11, 21, 31]
```

## Time and Space Complexity

| Resource | Cost |
|---|---|
| Time | `O(n)` mapper calls, `O(worker_count)` thread creations, `O(n)` lock acquisitions and `O(n)` sends |
| Space | `O(n)` for the jobs, the results, and the slot vector |

## Limitations

**The receivers are contended, and the lock is held while a worker waits.** A
worker that finds the queue empty holds the mutex while blocking in `recv`, so any
other worker that finishes a job and comes back for more waits for the mutex to be
released. `recv` releases the lock internally once it starts waiting, the standard
library's channel implementation releases the "blocking" case through a condition
variable, but the window between the lock being taken and the wait beginning is
real, and it is the part that a multiple-consumer channel exists to remove. The
`crossbeam-channel` crate provides such a channel, at the cost of one dependency.

**A panic in the mapper is invisible.** `let _ = handle.join()` discards the join
result, so a worker that panics mid-item leaves that item's slot empty. The
`assert_eq!(ordered.len(), expected)` in the common case does not fire, because
`ordered` was resized by the results that did arrive, so the failure that reaches
the caller is the `expect("all results present")` on the missing slot, which names
no item and no cause.

**The function asserts on empty input.** `assert!(!inputs.is_empty())` refuses a
call that has an obvious correct answer, an empty vector, and turns it into a
panic. That is a design choice rather than a necessity: the loop would send nothing,
the workers would exit, and the result would be empty.

**The order of results on the wire is unspecified, and only the reassembly makes
the output ordered.** A caller that wants results as they arrive, in completion
order, cannot use this function.

**The closure must be `'static`.** `F: Fn(T) -> R + Send + Sync + 'static` means the
mapper cannot borrow anything from the caller's stack. Scoped threads would lift
that restriction, and they would also let `T` and `R` borrow.

## Summary

- Two channels carry the work. The index recorded with each job and returned with
  each result is the mechanism that restores the input order.
- `Arc<Mutex<Receiver>>` is present because `mpsc` is single-consumer. The mutex
  makes the receiver shareable rather than protecting data.
- The lock is released before the mapper runs, so the workers execute in parallel
  rather than one at a time.
- A panic in the mapper is discarded by `let _ = handle.join()`. The slot for that
  item stays empty, and the failure surfaces as an `expect` that names neither the
  item nor the cause.
- `assert!(!inputs.is_empty())` turns a call with an obvious correct answer into a
  panic; the loop would send nothing and the result would be empty.
- The closure bound is `'static`, so the mapper cannot borrow from the caller's
  stack. Scoped threads would lift that restriction.

## References

- Standard library, [`std::sync::mpsc`](https://doc.rust-lang.org/std/sync/mpsc/index.html).
- Standard library, [`Mutex`](https://doc.rust-lang.org/std/sync/struct.Mutex.html).
- Standard library, [`std::thread::scope`](https://doc.rust-lang.org/std/thread/fn.scope.html), the alternative that removes the `'static` bounds.
- Standard library, [`JoinHandle::join`](https://doc.rust-lang.org/std/thread/struct.JoinHandle.html#method.join).
