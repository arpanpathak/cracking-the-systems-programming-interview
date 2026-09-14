# 22. Mutex Poisoning {#mutex-poisoning}

*Source file: [`src/bin/mutex_poisoning.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/mutex_poisoning.rs). Run it with
`cargo run --bin mutex_poisoning`.*

> A distributed system is one in which the failure of a computer you didn't
> even know existed can render your own computer unusable.
>
>, Leslie Lamport, *Distribution*, 1987

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

```rust
// ============================================================================
// Mutex poisoning: failed transaction and audit recovery
//
// Ported from the Rust playground repo (`scam_transaction.rs`).
//
// Story:
//   A branch executes a financial transaction that mutates shared state under
//   a `Mutex`. Mid-transaction the thread panics. In Rust, a `Mutex` whose
//   guard was held during a panic becomes **poisoned**. Future `lock()` calls
//   return `Err(PoisonError)` instead of silently letting another thread
//   observe an inconsistent partial update.
//
// Why this appears in cloud interviews:
//   - Controllers/reconcilers mutate shared state; a panic while holding a lock
//     is a real failure mode in worker pools, caches, and rate limiters.
//   - Rust chooses fail-fast over data corruption: a poisoned mutex tells
//     callers that the protected invariant may be broken. The caller must
//     decide whether to abort, recover, or reset state.
//   - `PoisonError::into_inner()` returns the `MutexGuard`, so a recovery path
//     can inspect/correct the last known state without waiting for the lock to
//     be released by the panicked thread.
//
// Run:
//   cargo run --bin mutex_poisoning
// ============================================================================

use std::error::Error;
use std::sync::{Arc, Mutex, MutexGuard, PoisonError};
use std::thread;

/// Shared ledger state. In a real system this would be behind a transactional
/// store; here it is plain in-memory state to illustrate lock poisoning.
#[derive(Debug, Clone)]
struct Ledger {
    cash_on_hand: i64,
    stock_value: i64,
    transaction_id: u32,
    is_settled: bool,
}

impl Ledger {
    fn new() -> Self {
        Ledger {
            cash_on_hand: 10_000,
            stock_value: 5_000,
            transaction_id: 0,
            is_settled: false,
        }
    }
}

/// Recovers from a poisoned mutex by taking ownership of the guard that the
/// panicked thread left behind.
///
/// `PoisonError::into_inner()` gives us the `MutexGuard`, which means we still
/// hold the lock while repairing state. The guard is dropped when this function
/// returns.
fn recover_ledger(poisoned: PoisonError<MutexGuard<'_, Ledger>>) -> Ledger {
    // into_inner() returns the MutexGuard. We own the lock exclusively even
    // though the previous holder panicked.
    let mut guard = poisoned.into_inner();

    println!("[Reconciliation] Physical audit reveals a cash discrepancy.");
    println!(
        "[Reconciliation] Digital cash: {} | Corrected cash: {}",
        guard.cash_on_hand,
        guard.cash_on_hand - 200
    );

    // Correct the data while we still hold the guard.
    guard.cash_on_hand -= 200;
    guard.is_settled = true;
    guard.transaction_id += 1;

    println!("[Reconciliation] Ledger corrected. Transaction marked failed and closed.");

    // Clone the inner data to return an owned value. The guard drops here and
    // releases the lock.
    guard.clone()
}

fn main() -> Result<(), Box<dyn Error>> {
    let ledger = Arc::new(Mutex::new(Ledger::new()));

    // Thread A: the faulty transaction. It mutates one side of the ledger and
    // then panics before marking the transaction settled.
    let ledger_a = Arc::clone(&ledger);
    let handle_a = thread::spawn(move || {
        // SAFETY-free normal code: if the mutex is already poisoned, unwrap()
        // panics; in a controlled demo this is the first lock so it is fine.
        let mut guard = ledger_a.lock().unwrap();

        println!(
            "[Branch A] Transaction {} commenced.",
            guard.transaction_id + 1
        );
        guard.stock_value -= 1_000;
        println!(
            "[Branch A] Stock deducted. New value: {}",
            guard.stock_value
        );
        guard.cash_on_hand += 1_200;
        println!(
            "[Branch A] Cash updated. New balance: {}",
            guard.cash_on_hand
        );

        // Panic while `guard` is still alive -> the Mutex becomes poisoned.
        panic!("[Branch A] Settlement failure: arithmetic overflow in reconciliation.");
    });

    // A panic in a spawned thread does not abort the process unless the panic
    // strategy is set to abort. `join()` returns Err, which is expected here.
    let _ = handle_a.join();

    // Thread B: the forensic audit. It sees Err(PoisonError), inspects the
    // recovered state, and repairs the ledger.
    let ledger_b = Arc::clone(&ledger);
    let handle_b = thread::spawn(move || {
        println!("\n[Audit] Attempting to access the ledger...");

        match ledger_b.lock() {
            Ok(guard) => {
                println!("[Audit] Ledger is not poisoned: {:?}", *guard);
            }
            Err(poisoned) => {
                println!("[Audit] Mutex is poisoned. Recovered state before correction:");
                println!("[Audit] {:?}", *poisoned.get_ref());

                let corrected = recover_ledger(poisoned);
                println!("[Audit] Corrected ledger: {:?}", corrected);
            }
        }
    });

    handle_b.join().unwrap();

    // Important: recovering the data does NOT clear the poison bit on the
    // Mutex itself. Subsequent lock() calls still return Err(PoisonError) so
    // callers can decide whether the repaired state is trustworthy.
    // Uncommenting the next lines would panic:
    //
    // let _guard = ledger.lock().unwrap();

    Ok(())
}

// ============================================================================
// Tests (cargo test --bin mutex_poisoning)
// ============================================================================
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ledger_starts_in_expected_state() {
        let ledger = Ledger::new();
        assert_eq!(ledger.cash_on_hand, 10_000);
        assert_eq!(ledger.stock_value, 5_000);
        assert!(!ledger.is_settled);
    }

    #[test]
    fn recovery_repairs_a_poisoned_ledger() {
        let ledger = Arc::new(Mutex::new(Ledger::new()));

        // Poison the mutex from a helper thread, exactly like the demo.
        let ledger_a = Arc::clone(&ledger);
        let handle = thread::spawn(move || {
            let _guard = ledger_a.lock().unwrap();
            panic!("boom");
        });
        let _ = handle.join();

        let lock_result = ledger.lock();
        assert!(lock_result.is_err(), "mutex should be poisoned");

        let recovered = recover_ledger(lock_result.unwrap_err());
        assert!(recovered.is_settled);
        assert_eq!(recovered.transaction_id, 1);
        assert_eq!(recovered.cash_on_hand, 10_000 - 200);
    }
}
```

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
