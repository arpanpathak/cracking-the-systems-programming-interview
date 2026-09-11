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
