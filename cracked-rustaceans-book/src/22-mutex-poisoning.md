# 22. Mutex Poisoning {#mutex-poisoning}

*Source file: [`src/bin/mutex_poisoning.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/mutex_poisoning.rs). Run it with
`cargo run --bin mutex_poisoning`.*

> A distributed system is one in which the failure of a computer you didn't
> even know existed can render your own computer unusable.
>
> Leslie Lamport, *Distribution*, 1987

## Problem Statement

Handle the case where a thread panics while holding a lock. The data behind the
lock may be half-updated, and the next thread to acquire it has to decide whether
to trust what it finds.

## Designing a Solution

A panic can happen in the middle of a sequence of writes that were meant to
succeed or fail together. If the lock were released and the data left as it was,
the next reader would see the partial update. Rust makes that failure visible
rather than silent: a `Mutex` whose guard was held during a panic is *poisoned*,
and later calls to `lock` return `Err(PoisonError)` instead of a guard.

```text
thread A                          thread B
--------                          --------
lock() -> guard
stock_value -= 1000
cash_on_hand += 1200
panic!  while guard is alive
                                  lock() -> Err(PoisonError)
the Mutex records that a panic     the guard is still reachable through
happened while the lock was held   PoisonError::into_inner(), so B can read the
                                  state, correct it, and release the lock
```

The recovery path in the file is a reconciliation: an audit prints the discrepancy,
corrects the cash figure, marks the transaction closed, and takes a copy of the
corrected state.

The important detail is what poisoning does *not* do. Poisoning is not access
control, and recovering the data does not clear the mark. Every later `lock()` on
that mutex still returns `Err`, so the decision to trust the repaired state is made
by each caller rather than by the act of repair.

## Implementation

<p class="listing"><span class="listing-label">Listing 22.1</span> The complete program, with its tests. <code>src/bin/mutex_poisoning.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/mutex_poisoning.rs">read the file on GitHub</a></p>

`recover_ledger` takes the `PoisonError` by value. That is the signature that makes
the type system enforce what the function needs: a `PoisonError<MutexGuard<...>>`
can only be produced by a failed `lock`, so the function cannot be called with a
healthy lock by mistake.

`poisoned.into_inner()` consumes the error and returns the guard. The lock is now
held by this thread, so the repair happens under the lock rather than beside it.

`guard.clone()` returns an owned copy of the state. `MutexGuard` is not `Clone`, so
the clone is of the inner value, taken through the guard. The guard is dropped when
the function returns, which releases the lock.

`handle_b.join().unwrap()` propagates a panic from the audit thread. `main` returns
`Result`, so an `unwrap` here would panic rather than return an error; the join
result is discarded for the first thread with `let _ = handle_a.join()`, and the
comment explains that the panic is the point of the demonstration.

The test calls `recover_ledger` with the error from a real poisoned lock, so the
recovery path is exercised rather than described.

## Intuition

```text
ledger after new:   { cash 10000, stock 5000, transaction_id 0, is_settled false }

thread A          lock() -> guard, the mutex is now marked as locked
                  stock_value -= 1000   -> 4000
                  cash_on_hand += 1200  -> 11200
                  panic! while the guard is alive

                  the guard is dropped during unwinding, the mutex is unlocked,
                  and the poison bit is set

join A            returns Err, which the code discards

thread B          lock() -> Err(PoisonError)
                  poisoned.get_ref() shows the partial update:
                    { cash 11200, stock 4000, transaction_id 0, is_settled false }
                  recover_ledger:
                    cash 11200 - 200 = 11000
                    is_settled = true
                    transaction_id = 1
                  the guard is dropped, the lock is released

after the run     the mutex is still poisoned, and the ledger inside it reads
                    { cash 11000, stock 4000, transaction_id 1, is_settled true }
```

## Time and Space Complexity

| Resource | Cost |
|---|---|
| Time | one lock acquisition per access; the recovery path prints four lines and clones the state once |
| Space | the ledger is four machine words; a `PoisonError` is the size of a guard |

## Limitations

**The repair rule is a constant in the code.** `guard.cash_on_hand -= 200` is the
audit's correction, and it is hardcoded. In a real reconciliation the correct
figure comes from an external source, a bank statement, a database, and the
function would take that source as a parameter. As written, the demonstration shows
the mechanism and not a policy.

**Recovering does not clear the poison mark.** The comment at the end of `main`
says so, and the line that would panic is left commented out. Every subsequent
`lock()` therefore returns `Err`, and a program whose recovery is complete has no
way to say so to the other threads without dropping the mutex entirely.
`Mutex::clear_poison` exists for that, and it is not used here.

**The failed thread's own recovery is absent.** Thread A panics and its work is
lost; nothing rolls back the partial update except thread B's audit. A system where
either thread might be the one to recover needs the repair to be idempotent and
runnable by any caller.

**`ledger_a.lock().unwrap()` panics if the mutex is already poisoned.** The comment
acknowledges it. In a program where several threads may touch the same lock,
`unwrap` on a `lock` result converts one thread's failure into a cascade of
panics, which is the opposite of what poisoning is for.

**The audit thread's panic would be propagated with `unwrap`.** `main` returns
`Result<(), Box<dyn Error>>`, so the error type on the happy path is unused here:
the only failure that can occur is a panic, and a panic cannot be converted into
`Box<dyn Error>` by `?`. `join()` returns `Result<T, Box<dyn Any + Send>>`, and
`Box<dyn Any + Send>` does not implement `Error`.

## Summary

- Poisoning records that a panic occurred while the guard was held. It repairs
  nothing and it does not deny access to the data.
- `PoisonError::into_inner()` returns the guard, so the thread that recovers also
  holds the lock while it repairs the state, and the repair does not race with
  other readers.
- Recovering is appropriate where the invariant can be re-established from data the
  program trusts, and propagating is appropriate where it cannot. In both cases the
  defect is a recovery with no stated repair rule.
- The repair rule here is a constant, `guard.cash_on_hand -= 200`. A reconciliation
  would take the correct figure from an external source and pass it in.
- Recovering does not clear the poison mark, so every later `lock()` returns `Err`
  and the other threads cannot be told that the repair is complete.
  `Mutex::clear_poison` exists for that purpose and is not used here.
- `ledger_a.lock().unwrap()` converts one thread's failure into a cascade of
  panics, which is the opposite of what poisoning is for.

## References

- Standard library, [`Mutex`](https://doc.rust-lang.org/std/sync/struct.Mutex.html), including the section on poisoning.
- Standard library, [`PoisonError::into_inner`](https://doc.rust-lang.org/std/sync/struct.PoisonError.html#method.into_inner).
- Standard library, [`Mutex::clear_poison`](https://doc.rust-lang.org/std/sync/struct.Mutex.html#method.clear_poison), stabilised in Rust 1.77.0.
- Standard library, [`JoinHandle::join`](https://doc.rust-lang.org/std/thread/struct.JoinHandle.html#method.join).
