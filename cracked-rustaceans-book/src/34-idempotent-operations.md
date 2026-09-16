# 34. Idempotent Operations {#idempotent-operations}

*Source files:
[`src/bin/idempotent_operation.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/idempotent_operation.rs) and
[`src/bin/idempotent_operation_with_error_progagation.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/idempotent_operation_with_error_progagation.rs).
Run them with `cargo run --bin idempotent_operation` and
`cargo run --bin idempotent_operation_with_error_progagation`.*

## Problem Statement

A client sends a request, the server performs the work, and the response is lost
before the client receives it. The client retries. If the server performs the work
again, a card is charged twice or an order is placed twice. An operation is
*idempotent* when performing it more than once has the same effect as performing
it once. The task here is to give an arbitrary fallible operation that property:
run it at most once for a given key, and return the same result to every later
call that presents the same key.

## Designing a Solution

Keep a map from key to the result already produced for that key. When a call
arrives, look the key up. On a hit, return a copy of the stored result and do not
run the operation. On a miss, run the operation, store the result, and return it.
The map sits behind a `Mutex`, so two threads cannot both observe a miss for the
same key.

Holding the lock across the operation is the decision that carries the design. It
is what makes the second of two concurrent callers wait on the lock, then find the
stored result instead of running the operation. The cost is that the lock is held
for the whole of the operation, so callers with *different* keys also wait for one
another. Only a successful result is stored: when the operation returns an error,
the key is left absent and a later retry runs it again.

The operation is passed as `FnOnce`, because the function may run zero times (on a
hit) or one time (on a miss), and never more than once. The error type is
`Box<dyn std::error::Error>`, which lets the caller supply any error without the
store naming it.

## Implementation

```rust
use std::collections::HashMap;
use std::hash::Hash;
use std::sync::Mutex;

pub struct Idempotent<K, V> {
    store: Mutex<HashMap<K, V>>,
}

impl<K, V> Idempotent<K, V>
where
    K: Eq + Hash + Clone,
    V: Clone,
{
    pub fn new() -> Self {
        Self { store: Mutex::new(HashMap::new()) }
    }

    pub fn execute<F>(&self, key: K, f: F) -> Result<V, Box<dyn std::error::Error>>
    where
        F: FnOnce() -> Result<V, Box<dyn std::error::Error>>,
    {
        let mut store = self.store.lock().map_err(|_| "lock poisoned")?;
        if let Some(v) = store.get(&key) {
            return Ok(v.clone());
        }
        let v = f()?;
        store.insert(key, v.clone());
        Ok(v)
    }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let idem = Idempotent::new();

    let charge = || -> Result<String, Box<dyn std::error::Error>> {
        println!("charging card...");
        Ok("txn_42".into())
    };

    assert_eq!(idem.execute("order-1", charge)?, "txn_42");
    assert_eq!(idem.execute("order-1", charge)?, "txn_42");
    Ok(())
}
```

The lock is taken first and held until `execute` returns. `store.get(&key)`
borrows the key, so the borrowed value is cloned out with `v.clone()` and the
borrow ends before `insert` moves the key into the map.

`let v = f()?` is where the operation runs. The `?` returns early on an error, so
the map is never written for a failed call. That is the choice that makes the store
*at-most-once for successes*: an error is treated as "the operation did not
happen", and a retry is allowed to run it again.

`store.insert(key, v.clone())` stores one copy and returns the other. The value is
cloned twice in all, once for the map and once for the caller. A version that
returned `v` and let the map own a clone, or that used the previous value
`insert` returns, would avoid one of the two.

The `K: Clone` bound is present but unused: `get` borrows the key and `insert`
moves it, and neither needs a copy. `V: Clone` is required, because both the hit
path and the store path copy the value.

### The variant with a named error type

The repository holds a second version of the same type,
`idempotent_operation_with_error_progagation.rs`. It differs in one way: the error
type is given a name, `RuntimeError`, and the alias is used in every signature.

```rust
use std::collections::HashMap;
use std::hash::Hash;
use std::sync::Mutex;

type RuntimeError = Box<dyn std::error::Error>;

pub struct Idempotent<K, V> {
    store: Mutex<HashMap<K, V>>,
}

impl<K, V> Idempotent<K, V>
where
    K: Eq + Hash + Clone,
    V: Clone,
{
    pub fn new() -> Self {
        Self { store: Mutex::new(HashMap::new()) }
    }

    pub fn execute<F>(&self, key: K, f: F) -> Result<V, RuntimeError>
    where
        F: FnOnce() -> Result<V, RuntimeError>,
    {
        let mut store = self.store.lock().map_err(|_| "lock poisoned")?;
        if let Some(v) = store.get(&key) {
            return Ok(v.clone());
        }
        let v = f()?;
        store.insert(key, v.clone());
        Ok(v)
    }
}

fn main() -> Result<(), RuntimeError> {
    let idem = Idempotent::new();

    let charge = || -> Result<String, RuntimeError> {
        println!("charging card...");
        Ok("txn_42".into())
    };

    assert_eq!(idem.execute("order-1", charge)?, "txn_42");
    assert_eq!(idem.execute("order-1", charge)?, "txn_42");
    Ok(())
}
```

The alias names the error in one place, so a change to the error type is a change
to one line and the signatures stay short. The behaviour is the same in both
files: the early return on an error, the lock held across the operation, and the
rule that only successes are stored.

## Intuition

Two sequential calls with the same key, tracing the map:

```text
execute("order-1", charge)          store = {}
  lock
  get("order-1")                    miss
  charge()                          prints "charging card..."  -> "txn_42"
  insert("order-1", "txn_42")       store = {order-1: "txn_42"}
  unlock
  return "txn_42"

execute("order-1", charge)          store = {order-1: "txn_42"}
  lock
  get("order-1")                    hit
  return "txn_42"                   charge() is not called
  unlock

output:
  charging card...
```

The program prints the line once. The two assertions both hold, but they would
hold even without caching, because the same closure produces the same value; the
evidence that the closure ran once is the single line of output.

Two concurrent calls with the same key show what the lock is for:

```text
thread A                          thread B
  lock
  get: miss
  charge()  (runs)
                                    lock  (blocks)
  insert
  unlock
                                    get: hit
                                    unlock
                                    return stored value

charge() ran once; thread B returned the value thread A stored.
```

Without the lock held across `charge`, both threads would miss, both would run the
operation, and the effect would happen twice.

## Time and Space Complexity

| Operation | Time | Space |
|---|---|---|
| `execute`, hit | `O(1)` expected | one clone of the stored value |
| `execute`, miss | `O(1)` expected, plus the cost of `f` | one map entry and one clone |
| store | `O(k)` entries | one entry per distinct key, held for the life of the value |

`O(1)` expected for the map rests on the usual assumption that the hash function
distributes keys evenly. The store is linear in the number of distinct keys and is
never pruned.

## Limitations

**The lock is held across the operation.** Every call, for every key, is serialised
for the duration of `f`. A slow `f` blocks unrelated keys as well as duplicates of
its own. An operation that calls back into the same store deadlocks, because the
lock is not reentrant.

**The store has no bound and no expiry.** Entries live until the process exits, so
the map grows with the number of distinct keys. A production store needs a
time-to-live and an eviction policy, because the set of keys is not bounded by
anything the client controls.

**The store is in memory.** A restart forgets every key, so a retry after a crash
runs the operation again. Durability requires persisting the key and the result, or
relying on a unique constraint in the datastore that performs the effect.

**Only successes are stored.** A failed call leaves the key absent, so a retry runs
the operation again. For an operation that can partially succeed, that is the wrong
default; the record of the attempt has to be written before the effect, not after
it.

**The error type erases the concrete error.** Callers receive
`Box<dyn std::error::Error>` and cannot match on the failure without downcasting.
The lock-poisoning case is a string, which is the least informative variant in the
file.

**A panic while the lock is held poisons the mutex.** Every later call returns the
`"lock poisoned"` error, and the store never recovers. The error is reported rather
than panicking the caller, which is the better of the two available choices, but
the store is unusable from that point on.

**The key is not scoped.** A production idempotency key is scoped to a client and
an endpoint, so that two callers cannot collide by choosing the same string. This
store treats the key as global.

**`K: Clone` is an unused bound.** It constrains callers without buying anything.
The bound can be removed with no other change to the implementation.

## Summary

- A `Mutex<HashMap<K, V>>` gives at-most-once execution per key and a cached
  result for every later call with that key.
- Holding the lock across the operation is what prevents two concurrent callers
  from running it twice; the price is that different keys are serialised too.
- Only success is recorded, so failure leaves the key absent and a retry is
  permitted.
- The store is in memory, unbounded, and without expiry or scope, so it is a
  faithful model of the pattern rather than a production idempotency layer.

## References

- Rust standard library, [`Mutex`](https://doc.rust-lang.org/std/sync/struct.Mutex.html) and [`HashMap`](https://doc.rust-lang.org/std/collections/struct.HashMap.html).
- Rust standard library, [`FnOnce`](https://doc.rust-lang.org/std/ops/trait.FnOnce.html), for a closure that runs at most once.
- RFC 9110, [HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html), Section 9.2.2, on idempotent methods.
