# Rust Technical Reference — Cloud SDK Engineering

## 1. Idempotency

Idempotency means applying an operation multiple times yields the same result as applying it once. For HTTP APIs this is achieved with an idempotency key: the client generates a unique token per logical operation, sends it with the request, and reuses the same token on every retry. The server stores `key → result` and, on a duplicate, returns the cached result instead of re-executing the effect.

### 1.1 Single-Owner Implementation

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

**Mechanics.** `Mutex<HashMap<K, V>>` holds the cache behind a mutual-exclusion lock. `lock()` returns a `MutexGuard<HashMap<K, V>>`, which dereferences to `&mut HashMap`. The guard releases the mutex when it drops at the end of the enclosing block. The `?` operator on `map_err` converts a `PoisonError` into the string literal `"lock poisoned"`, which is coerced into `Box<dyn Error>` by the blanket `From<&str> for Box<dyn Error>` impl.

**Bounds.** `K: Eq + Hash + Clone` is the minimum for `HashMap` keys plus the `Clone` required to pass the key to `insert` after `get(&key)` borrows it. `V: Clone` allows the cached value to be returned without moving it out of the map. `F: FnOnce` is the correct closure bound because the closure is invoked at most once per call to `execute`.

**Trade-off.** The lock is held for the duration of `f()`. Unrelated keys serialize against each other for the entire duration of the effect. This is acceptable when the critical section is short, but degrades under contention.

### 1.2 Single-Flight Implementation

When multiple threads call `execute` with the same key concurrently, only one should run `f`. The others should block until the first finishes and then read the cached value.

```rust
use std::collections::HashMap;
use std::hash::Hash;
use std::sync::{Arc, Mutex};

type IdmptOpNode<V> = Arc<Mutex<Option<V>>>;

pub struct Idempotent<K, V> {
    store: Mutex<HashMap<K, IdmptOpNode<V>>>,
}

impl<K, V> Idempotent<K, V>
where
    K: Eq + Hash + Clone,
    V: Clone,
{
    pub fn execute<F, E>(&self, key: K, f: F) -> Result<V, E>
    where
        F: FnOnce() -> Result<V, E>,
    {
        let node = {
            let mut store = self.store.lock().unwrap_or_else(|e| e.into_inner());
            Arc::clone(store.entry(key).or_default())
        };

        let mut guard = node.lock().unwrap_or_else(|e| e.into_inner());
        if let Some(v) = guard.as_ref() {
            return Ok(v.clone());
        }
        let v = f()?;
        *guard = Some(v.clone());
        Ok(v)
    }
}
```

**Mechanics.** The outer `Mutex<HashMap<K, IdmptOpNode<V>>>` is held only long enough to fetch or create the node for the key. `entry(key).or_default()` returns `&mut IdmptOpNode<V>`; `or_default()` constructs `Arc::new(Mutex::new(None))` if the key is absent. `Arc::clone` increments the atomic reference count, producing a handle that outlives the outer lock. The outer lock is then released at the end of the block, allowing unrelated keys to proceed in parallel.

The per-key lock is then acquired. If the inner `Option<V>` is `Some`, the result was already computed and is cloned out. If `None`, `f()` runs while the node lock is held. Concurrent callers with the same key block on `node.lock()` and observe the cached value when the first caller releases the lock.

**`Option` as state.** `Option<V>` encodes two states in one field: `None` (in-flight or not started) and `Some(v)` (done). A separate enum (`enum State { InFlight, Done(V) }`) would be more explicit but is not necessary here because the presence of the node lock itself distinguishes "in-flight" from "not started."

**Poison recovery.** `unwrap_or_else(|e| e.into_inner())` calls `PoisonError::into_inner`, which returns the guard regardless of whether a prior thread panicked. The rationale: the inner map and nodes hold a simple cache whose invariants cannot be left broken by a panic mid-write, so recovering is safe. Library code that cannot make this guarantee should propagate the poison instead.

**Production mapping.** In a fleet, `HashMap` is replaced by a durable store (DynamoDB, Postgres, Redis). The `Mutex` disappears because the store provides atomicity via a conditional write. In DynamoDB, this is `PutItem` with `ConditionExpression: attribute_not_exists(idem_key)`. A `ConditionalCheckFailedException` indicates the key was already claimed; the caller then reads the stored result.

### 1.3 SDK Retry with Idempotency Key

```rust
use std::collections::HashMap;
use std::sync::Mutex;
use std::time::Duration;

type RuntimeError = Box<dyn std::error::Error>;

struct IdemCache {
    store: Mutex<HashMap<String, String>>,
}

impl IdemCache {
    fn new() -> Self {
        Self { store: Mutex::new(HashMap::new()) }
    }

    fn get_or_insert<F>(&self, key: &str, f: F) -> Result<String, RuntimeError>
    where
        F: FnOnce() -> Result<String, RuntimeError>,
    {
        let mut store = self.store.lock().map_err(|_| "lock poisoned")?;
        if let Some(v) = store.get(key) {
            return Ok(v.clone());
        }
        let v = f()?;
        store.insert(key.to_string(), v.clone());
        Ok(v)
    }
}

struct RetryPolicy {
    max_attempts: u32,
    base_delay: Duration,
    max_delay: Duration,
}

impl RetryPolicy {
    fn new() -> Self {
        Self {
            max_attempts: 3,
            base_delay: Duration::from_millis(100),
            max_delay: Duration::from_secs(5),
        }
    }

    fn execute<F, T>(&self, mut f: F) -> Result<T, RuntimeError>
    where
        F: FnMut() -> Result<T, RuntimeError>,
    {
        let mut attempt = 0;
        loop {
            attempt += 1;
            match f() {
                Ok(v) => return Ok(v),
                Err(e) if attempt >= self.max_attempts => return Err(e),
                Err(_) => {
                    let delay = (self.base_delay * 2u32.pow(attempt - 1)).min(self.max_delay);
                    std::thread::sleep(delay);
                }
            }
        }
    }
}

fn create_item(item_name: &str) -> Result<String, RuntimeError> {
    println!("POST /v1/items name={item_name}");
    Ok(format!("item_{}", item_name.len()))
}

fn main() -> Result<(), RuntimeError> {
    let cache = IdemCache::new();
    let retry = RetryPolicy::new();

    let item = cache.get_or_insert("create-demo-001", || {
        retry.execute(|| create_item("demo"))
    })?;

    println!("created: {item}");
    Ok(())
}
```

**Mechanics.** `RetryPolicy::execute` takes `F: FnMut` because the closure is called multiple times. Backoff is computed as `base_delay * 2^(attempt - 1)`, clamped to `max_delay`. The `FnOnce` bound on `get_or_insert` is correct because the retry closure is consumed by the cache on the first miss.

**Key generation.** The caller generates a UUID per logical operation and passes it as `key`. On every retry, the same key is presented, so the cache short-circuits subsequent attempts after the first success. For actual production use, add jitter (`delay * random_factor`) to avoid thundering-herd effects when many clients retry in lockstep.

### 1.4 References

- [`std::sync::Mutex`](https://doc.rust-lang.org/std/sync/struct.Mutex.html)
- [`std::sync::Arc`](https://doc.rust-lang.org/std/sync/struct.Arc.html)
- [`std::collections::HashMap`](https://doc.rust-lang.org/std/collections/struct.HashMap.html)
- [`std::collections::hash_map::Entry`](https://doc.rust-lang.org/std/collections/hash_map/enum.Entry.html)
- [`std::sync::PoisonError`](https://doc.rust-lang.org/std/sync/struct.PoisonError.html)

---

## 2. Send and Sync

`Send` and `Sync` are unsafe marker traits with no methods. The compiler implements them automatically for any type whose fields are themselves `Send` or `Sync`. They do not affect code generation; they exist solely to constrain what the compiler will allow to cross thread boundaries.

### 2.1 Definitions

`T: Send` means a value of type `T` can be moved to another thread. Semantically, this is safe if no thread-local invariants of `T` are violated by the move.

`T: Sync` means `&T` can be shared across threads. Equivalently, `T: Sync` iff `&T: Send`.

A type can be `Send` but not `Sync` (e.g. `Cell<T>`), `Sync` but not `Send` (rare), both, or neither.

### 2.2 Example

```rust
use std::thread;

#[derive(Debug)]
struct Both {
    value: i32,
}

struct SendOnly {
    value: std::cell::Cell<i32>,
}

struct Neither {
    value: *mut i32,
}

fn main() {
    let both = Both { value: 42 };
    thread::spawn(move || {
        println!("moved into thread: {:?}", both);
    }).join().unwrap();

    let shared = Both { value: 7 };
    thread::scope(|s| {
        s.spawn(|| {
            println!("shared reference: {:?}", &shared);
        });
        s.spawn(|| {
            println!("shared reference again: {:?}", &shared);
        });
    });
}
```

`Both` is `Send + Sync` because `i32` is. `thread::spawn(move || ...)` consumes `both` by move — this requires `Both: Send`. The closure itself must also be `Send`. `thread::scope` allows borrowing `&shared` because the scope joins all threads before returning; `&Both` must be `Send`, which follows from `Both: Sync`.

`SendOnly` wraps `Cell<i32>`. `Cell<T>` provides interior mutability without synchronization: `set` and `get` take `&self` and mutate through it. Moving `Cell` to another thread is safe (nothing shared), so it is `Send`. Sharing `&Cell` across threads would allow two threads to mutate the same cell without synchronization, so `Cell: !Sync`.

`Neither` contains a raw pointer. Raw pointers are `!Send` and `!Sync` because the compiler cannot verify what they point to.

### 2.3 Marker Trait Table

| Type | `Send` | `Sync` | Reason |
|---|---|---|---|
| `i32`, `String`, `Vec<T: Send>` | Yes | Yes | Owned data, no shared state |
| `&T` where `T: Sync` | Yes | Yes | Sharing a reference is safe if `T: Sync` |
| `&mut T` where `T: Send` | Yes | Yes if `T: Sync` | Exclusive borrow; no aliasing |
| `Rc<T>` | No | No | Non-atomic reference count; racing clones corrupt it |
| `Arc<T>` | Yes if `T: Send + Sync` | Yes if `T: Send + Sync` | Atomic reference count; sharing requires `T: Sync` |
| `Mutex<T>` | Yes if `T: Send` | Yes if `T: Send` | Internal lock serializes access |
| `RwLock<T>` | Yes if `T: Send` | Yes if `T: Send + Sync` | Reads require `T: Sync` |
| `Cell<T>`, `RefCell<T>` | Yes | No | Non-atomic interior mutability |
| `*mut T`, `*const T` | No | No | Unverified provenance |
| `MutexGuard<'a, T>` (`std`) | No | — | Tied to the locking thread's stack |
| `JoinHandle<T>` | Yes | Yes | Owns the thread handle |

### 2.4 How the Compiler Uses These Traits

`thread::spawn` is declared:

```rust
pub fn spawn<F, T>(f: F) -> JoinHandle<T>
where
    F: FnOnce() -> T + Send + 'static,
    T: Send + 'static,
```

Both the closure `F` and its return type `T` must be `Send`. The `'static` bound means the closure cannot borrow local data whose lifetime ends before the thread finishes; `thread::scope` relaxes this.

`tokio::spawn` is similar:

```rust
pub fn spawn<F>(future: F) -> JoinHandle<F::Output>
where
    F: Future + Send + 'static,
    F::Output: Send + 'static,
```

The future itself must be `Send`. A future captures all values held across `.await` points. If any of those values is `!Send`, the future is `!Send` and the compiler rejects the spawn.

### 2.5 The `MutexGuard` Case

```rust
// use std::sync::Mutex;
//
// async fn bad() {
//     let m = Mutex::new(0);
//     let _guard = m.lock().unwrap();
//     some_async_call().await;
// }
```

Error: `future cannot be sent between threads safely`. Reason: `std::sync::MutexGuard` is `!Send` because it must be unlocked by the same thread that locked it, and a future may resume on a different worker thread after `.await`. The compiler detects that the guard is held across an `.await` point and rejects the future as `!Send`.

The fix is either to drop the guard before `.await` or to use `tokio::sync::Mutex`, whose guard is `Send` because it uses a task-aware queue instead of a thread-parking primitive.

### 2.6 References

- [`Send`](https://doc.rust-lang.org/std/marker/trait.Send.html)
- [`Sync`](https://doc.rust-lang.org/std/marker/trait.Sync.html)
- [The Rust Book: Extensible Concurrency](https://doc.rust-lang.org/book/ch16-04-extensible-concurrency-sync-and-send.html)
- [The Rustonomicon: Send and Sync](https://doc.rust-lang.org/nomicon/send-and-sync.html)

---

## 3. Concurrency Primitives

### 3.1 Mutex

```rust
use std::sync::{Arc, Mutex};
use std::thread;

fn shared_counter() -> i32 {
    let counter = Arc::new(Mutex::new(0i32));

    let handles: Vec<_> = (0..10)
        .map(|_| {
            let counter = Arc::clone(&counter);
            thread::spawn(move || {
                for _ in 0..100 {
                    let mut n = counter.lock().unwrap();
                    *n += 1;
                }
            })
        })
        .collect();

    for h in handles {
        h.join().unwrap();
    }

    *counter.lock().unwrap()
}

fn main() {
    assert_eq!(shared_counter(), 1000);
    println!("counter = 1000");
}
```

**Mechanics.** `Arc::new(Mutex::new(0))` allocates the mutex on the heap and returns an atomically reference-counted handle. `Arc::clone` produces a new handle to the same allocation and increments the strong count from 1 to 2 (and so on). Each thread owns one handle; the allocation is dropped when the last handle is dropped.

`Mutex::lock` blocks the calling thread until the lock is acquired, then returns `LockResult<MutexGuard<T>>`. `MutexGuard` is a smart pointer that derefs to `&mut T`. Dropping the guard releases the lock.

**Scope discipline.** The guard should be dropped as soon as the critical section ends. In `for _ in 0..100 { let mut n = counter.lock()...; *n += 1; }`, the guard `n` is scoped to the loop body, so the lock is released at the end of each iteration. Holding the guard across the loop would serialize every increment with the lock held and defeat parallelism.

**Contention.** Under high contention, a `Mutex` degrades to a serialized workload. Alternatives: sharding the counter (one `Mutex` per shard, keyed by thread ID), using `AtomicUsize` for a single integer, or using a channel to funnel updates to a single owner.

References: [`Mutex`](https://doc.rust-lang.org/std/sync/struct.Mutex.html), [`MutexGuard`](https://doc.rust-lang.org/std/sync/struct.MutexGuard.html), [`Arc`](https://doc.rust-lang.org/std/sync/struct.Arc.html).

### 3.2 RwLock

```rust
use std::sync::{Arc, RwLock};
use std::thread;
use std::time::Duration;

fn main() {
    let data = Arc::new(RwLock::new(5));

    for i in 0..3 {
        let lock = Arc::clone(&data);
        thread::spawn(move || {
            let value = lock.read().unwrap();
            println!("Reader {}: {}", i, *value);
            thread::sleep(Duration::from_millis(50));
        });
    }

    {
        let mut w = data.write().unwrap();
        *w = 10;
        println!("Writer: set to 10");
    }

    thread::sleep(Duration::from_millis(200));
    assert_eq!(*data.read().unwrap(), 10);
}
```

**Mechanics.** `RwLock::read` returns `RwLockReadGuard`, which permits concurrent access from any number of readers. `RwLock::write` returns `RwLockWriteGuard`, which grants exclusive access and blocks until all readers release. The three reader threads hold read guards for 50 ms each; while they hold them, the writer blocks.

**Fairness.** `std::sync::RwLock` does not guarantee writer preference. A continuous stream of readers can starve writers indefinitely. Platform implementations vary: on Linux, the default is reader-preferred unless writers have been waiting; on macOS and Windows, behavior differs. For latency-sensitive write paths, prefer `Mutex`, which has no such starvation mode.

**Mutation while reading.** Reading `RwLock` does not allow mutation of `T` through the read guard. The guard derefs to `&T`, so fields cannot be modified. `RwLock` is suitable when the read set is much larger than the write set.

Reference: [`RwLock`](https://doc.rust-lang.org/std/sync/struct.RwLock.html).

### 3.3 Atomic

```rust
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;
use std::thread;

fn main() {
    let counter = Arc::new(AtomicUsize::new(0));

    let handles: Vec<_> = (0..10)
        .map(|_| {
            let counter = Arc::clone(&counter);
            thread::spawn(move || {
                for _ in 0..1000 {
                    counter.fetch_add(1, Ordering::Relaxed);
                }
            })
        })
        .collect();

    for h in handles {
        h.join().unwrap();
    }

    assert_eq!(counter.load(Ordering::Relaxed), 10_000);
    println!("atomic counter = {}", counter.load(Ordering::Relaxed));
}
```

**Mechanics.** `AtomicUsize` wraps a `usize` and provides lock-free operations via CPU instructions such as `lock xadd` on x86. `fetch_add` atomically reads the value, adds the operand, and stores the result in one indivisible step. The previous value is returned.

**Memory ordering.** `Ordering` selects the fence strength around the atomic operation:

| Ordering | Guarantee |
|---|---|
| `Relaxed` | Atomicity only; no cross-variable ordering |
| `Acquire` | Loads after this operation see writes released by a matching `Release` |
| `Release` | Writes before this operation are visible to a matching `Acquire` |
| `AcqRel` | Both `Acquire` and `Release` |
| `SeqCst` | Total order across all `SeqCst` operations |

`Relaxed` is correct for a counter where no other data is published through the atomic. If the atomic is used as a flag whose release publishes writes to other fields, use `Release` on the store and `Acquire` on the load. `SeqCst` is the safest default when reasoning is uncertain.

**Scope.** Atomics are defined only for primitive types (`AtomicBool`, `AtomicU8` through `AtomicU64`, `AtomicUsize`, `AtomicIsize`, `AtomicPtr`). For compound types, use `Mutex` or a lock-free crate.

References: [`AtomicUsize`](https://doc.rust-lang.org/std/sync/atomic/struct.AtomicUsize.html), [`Ordering`](https://doc.rust-lang.org/std/sync/atomic/enum.Ordering.html).

### 3.4 Channels

```rust
use std::sync::mpsc;
use std::thread;

fn main() {
    let (tx, rx) = mpsc::channel::<u32>();

    for id in 0..3u32 {
        let tx = tx.clone();
        thread::spawn(move || {
            for i in 0..5 {
                tx.send(id * 100 + i).unwrap();
            }
        });
    }
    drop(tx);

    let mut sum = 0u32;
    for v in rx {
        sum += v;
    }
    println!("sum = {sum}");
}
```

**Mechanics.** `mpsc::channel` returns a `(Sender<T>, Receiver<T>)` pair. `Sender::send` enqueues a value; `Receiver::recv` blocks until a value is available or all senders are dropped. `Receiver` also implements `Iterator<Item = T>`, which yields values until the channel closes.

**Closure by drop.** `Sender` holds a strong reference to the shared queue. The channel closes when the last `Sender` is dropped. Cloning a sender for each thread gives three senders; the original `tx` is still alive in `main`. Without `drop(tx)`, the `for v in rx` loop would block after consuming all sent values because the original sender would still be alive. The explicit `drop(tx)` releases the main thread's sender, and the channel closes once all thread-local clones are dropped at the end of each thread.

**Alternatives.** `mpsc` is single-consumer. For multiple consumers, use `crossbeam_channel::unbounded` or `tokio::sync::mpsc`. For synchronous backpressure, use `sync_channel` with a bounded capacity; `send` then blocks when the buffer is full.

Reference: [`mpsc::channel`](https://doc.rust-lang.org/std/sync/mpsc/fn.channel.html).

### 3.5 Scoped Threads

```rust
use std::thread;

fn main() {
    let mut a = vec![1, 2, 3];
    let mut x = 0;

    thread::scope(|s| {
        s.spawn(|| {
            println!("first scoped thread");
            x += a[0] + a[2];
        });
        s.spawn(|| {
            println!("second scoped thread");
            a[1] = 42;
        });
        println!("main thread");
    });

    println!("a = {a:?}, x = {x}");
}
```

**Mechanics.** `thread::scope` is declared:

```rust
pub fn scope<'env, F, T>(f: F) -> T
where
    F: for<'scope> FnOnce(&'scope Scope<'scope, 'env>) -> T,
```

The `Scope<'scope, 'env>` API guarantees that all threads spawned through it are joined before `scope` returns. Because the threads cannot outlive the scope, the borrow checker permits them to capture references to data with lifetime `'env` — here `&mut a` and `&mut x`. The `move` keyword is not used: the closures borrow `a` and `x` instead of consuming them.

**Aliasing rule.** The two closures mutate disjoint parts of `a` (`a[0]`, `a[2]` in the first; `a[1]` in the second) and `x` in only one. The borrow checker treats the mutable captures as potentially aliasing, but the compiler proves the closures have distinct borrow sets. If both closures needed mutable access to `a`, the code would be rejected; `Mutex` or `Arc<Mutex<_>>` would be required.

**Use case.** `thread::scope` eliminates the `Arc` requirement for spawned threads whose lifetime is bounded by the enclosing function. This is often the cleanest formulation for short-lived parallel work.

Reference: [`std::thread::scope`](https://doc.rust-lang.org/std/thread/fn.scope.html).

---

## 4. Async Rust

### 4.1 `std::sync::Mutex` vs `tokio::sync::Mutex`

| | `std::sync::Mutex` | `tokio::sync::Mutex` |
|---|---|---|
| Blocking primitive | OS thread parking | Task queue |
| Guard is `Send` | No | Yes |
| Hold across `.await` | Compile error if future must be `Send` | Permitted |
| Overhead per uncontended lock | Low | Higher |
| Suitable for | Short critical sections without `.await` | Critical sections that span `.await` |

`std::sync::MutexGuard` is `!Send` because the guard must be released by the same thread that acquired it, and a task may resume on a different worker thread after `.await`. Holding the guard across `.await` makes the future `!Send`, which prevents passing it to `tokio::spawn`.

`tokio::sync::MutexGuard` is `Send` because the lock is implemented as a queue of woken tasks rather than a parking primitive. When a task cannot acquire the lock, it yields to the runtime; when the lock is released, the runtime schedules the waiting task on whichever worker is available.

### 4.2 Async Example

```rust
use std::sync::Arc;
use tokio::sync::Mutex;
use std::collections::HashMap;

type Store = Arc<Mutex<HashMap<String, String>>>;

async fn handle_command(store: Store, key: String, value: String) -> String {
    let mut map = store.lock().await;
    map.insert(key.clone(), value);
    map.get(&key).cloned().unwrap_or_default()
}

#[tokio::main]
async fn main() {
    let store: Store = Arc::new(Mutex::new(HashMap::new()));

    let result = handle_command(store.clone(), "foo".into(), "bar".into()).await;
    assert_eq!(result, "bar");

    println!("async store works");
}
```

**Mechanics.** `store.lock().await` yields to the runtime if the lock is held by another task. The guard is `Send`, so the future returned by `handle_command` is `Send` and can be spawned. `Arc` is required because `tokio::spawn` requires `'static` and the store must outlive any individual task.

**Guidance.** Use `std::sync::Mutex` when the critical section contains no `.await`. The lock is faster and the guard cannot accidentally be held across a suspension point. Use `tokio::sync::Mutex` only when the guard must be held across `.await` — for example, when the protected resource is an I/O handle whose operations are themselves async.

### 4.3 References

- [`tokio::sync::Mutex`](https://docs.rs/tokio/latest/tokio/sync/struct.Mutex.html)
- [`tokio::sync::MutexGuard`](https://docs.rs/tokio/latest/tokio/sync/struct.MutexGuard.html)
- [`std::sync::MutexGuard`](https://doc.rust-lang.org/std/sync/struct.MutexGuard.html)
- [Tokio Tutorial: Shared State](https://tokio.rs/tokio/tutorial/shared-state)

---

## 5. Error Handling

### 5.1 Type Alias

```rust
type RuntimeError = Box<dyn std::error::Error>;
```

A type alias introduces a shorter name for an existing type. `Box<dyn Error>` is a trait object: a heap allocation containing a value of any type implementing `Error`, plus a vtable for dynamic dispatch of `Debug` and `Display` methods. The blanket impl `impl<E: Error + 'static> From<E> for Box<dyn Error>` allows `?` to convert any `E: Error` into `Box<dyn Error>`. `&str` and `String` implement `Error` through dedicated impls, so string literals can be used as error values.

### 5.2 Custom Error with Downcast

```rust
use std::error::Error;
use std::fmt;

#[derive(Debug)]
struct NetworkError {
    code: u16,
}

impl fmt::Display for NetworkError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "network error {}", self.code)
    }
}

impl Error for NetworkError {}

fn might_fail() -> Result<(), Box<dyn Error>> {
    Err(Box::new(NetworkError { code: 503 }))
}

fn handle(e: &dyn Error) {
    if let Some(net) = e.downcast_ref::<NetworkError>() {
        if net.code == 503 {
            println!("retrying after 503");
            return;
        }
    }
    eprintln!("unhandled: {e}");
}

fn main() -> Result<(), Box<dyn Error>> {
    if let Err(e) = might_fail() {
        handle(&*e);
    }
    Ok(())
}
```

**Mechanics.** `Box<dyn Error>` loses the concrete type; `downcast_ref::<T>()` inspects the vtable's `TypeId` and returns `Option<&T>` if the concrete type matches `T`. This enables typed handling of dynamic errors without an explicit enum.

**Trade-off.** Downcasting pushes the type check to runtime. A structured error enum with `match` enforces the same dispatch at compile time and prevents forgetting to handle a variant. Use `Box<dyn Error>` for application code where the error set is open; use an enum for library code where the error set is known and stable.

References: [`Error`](https://doc.rust-lang.org/std/error/trait.Error.html), [`Box`](https://doc.rust-lang.org/std/boxed/struct.Box.html).

### 5.3 Mutex Poison

```rust
use std::sync::Mutex;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let m = Mutex::new(0);

    let _guard = m.lock().map_err(|_| "lock poisoned")?;

    let _guard = m.lock().unwrap_or_else(|e| e.into_inner());

    Ok(())
}
```

**Mechanics.** When a thread panics while holding a `MutexGuard`, the mutex is marked poisoned. Subsequent calls to `lock` return `Err(PoisonError<MutexGuard<T>>)`, preventing other threads from observing a partially mutated `T`. `PoisonError::into_inner` extracts the guard, discarding the poison flag.

**Choice of strategy.** Propagating poison is correct when a panic could leave `T` in an inconsistent state (e.g. an `Invariant`-maintaining data structure). Recovering is correct when the protected data is simple enough that a panic cannot violate its invariants (e.g. a `HashMap` cache). Document the choice in code comments.

Reference: [`PoisonError`](https://doc.rust-lang.org/std/sync/struct.PoisonError.html).

### 5.4 `thiserror` and `anyhow`

```rust
// Cargo.toml:
// thiserror = "1"
// anyhow = "1"

#[derive(Debug, thiserror::Error)]
enum ApiError {
    #[error("network failed: {0}")]
    Network(String),
    #[error("not found: {0}")]
    NotFound(String),
}

use anyhow::{Context, Result};

fn load_config(path: &str) -> Result<String> {
    std::fs::read_to_string(path)
        .context("failed to load config")?
        .parse()
        .context("failed to parse config")
}
```

**`thiserror`.** A procedural macro that generates `Display` (from `#[error("...")]`) and `Error` (with `source` propagation from `#[source]` or `#[from]`) implementations for an enum or struct. Use it in libraries where the error type is part of the public API and callers may want to match on it.

**`anyhow`.** Provides `anyhow::Error`, a type-erased error with a chain of contexts. `Context::context` attaches a human-readable message to the underlying error, producing a stack of messages rather than a single string. Use it in binary crates or internal modules where the error is only logged or displayed.

**Interaction.** A library can return `thiserror`-based errors and the binary can convert them into `anyhow::Error` via `?`, since `anyhow::Error` implements `From<E: Error + Send + Sync + 'static>`.

References: [`thiserror`](https://docs.rs/thiserror/), [`anyhow`](https://docs.rs/anyhow/).

---

## 6. SDK and CLI Design

### 6.1 Platform Configuration Directories

```rust
// Cargo.toml: directories = "5"
use directories::ProjectDirs;

fn main() {
    if let Some(proj) = ProjectDirs::from("com", "NVIDIA", "GPU Cloud CLI") {
        println!("config: {:?}", proj.config_dir());
        println!("cache:  {:?}", proj.cache_dir());
        println!("data:   {:?}", proj.data_dir());
    }
}
```

**Mechanics.** `ProjectDirs::from(qualifier, organization, application)` constructs OS-specific paths following the platform conventions:

| Platform | Config directory |
|---|---|
| Linux | `$XDG_CONFIG_HOME/<app>/` or `~/.config/<app>/` |
| Windows | `%APPDATA%\<org>\<app>\config\` |
| macOS | `~/Library/Application Support/<qualifier>.<org>.<app>/` |

The `directories` crate returns `PathBuf`, which handles path separators and encoding per platform. Never construct config paths by string concatenation; use `PathBuf::join` and `Path::exists`.

Reference: [`directories`](https://crates.io/crates/directories).

### 6.2 CLI Structure

```rust
// Cargo.toml: clap = { version = "4", features = ["derive"] }
use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "gpu-cloud")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    List,
    Create {
        #[arg(long)]
        name: String,
        #[arg(long, default_value = "a100")]
        gpu_type: String,
    },
    Get {
        id: String,
    },
}

fn main() {
    let cli = Cli::parse();
    match cli.command {
        Commands::List => println!("listing instances..."),
        Commands::Create { name, gpu_type } => {
            println!("creating {name} with {gpu_type}");
        }
        Commands::Get { id } => println!("getting {id}"),
    }
}
```

**Mechanics.** `#[derive(Parser)]` generates `Cli::parse`, which reads `std::env::args_os`, performs tokenization and validation, and prints usage on error. `#[command(subcommand)]` nests the `Commands` enum. `#[derive(Subcommand)]` turns each variant into a subcommand; `--long` flags map to `#[arg(long)]`, positional arguments to plain fields. `default_value` supplies a fallback when the flag is omitted.

**Extensibility.** Subcommands map to a `match` expression; adding a variant to `Commands` produces a compiler error at the `match`, forcing the developer to handle the new case. This is preferable to string-based dispatch, which fails silently.

Reference: [`clap`](https://docs.rs/clap/).

### 6.3 HTTP Status Handling

| Status | Action |
|---|---|
| 200, 201, 204 | Success |
| 400 | Do not retry; malformed request |
| 401, 403 | Do not retry; refresh credentials or fail |
| 404 | Do not retry; resource does not exist |
| 409 | Conflict; duplicate idempotency key or state conflict |
| 429 | Retry after `Retry-After` seconds |
| 500, 502, 503, 504 | Retry with exponential backoff and jitter |

Retry only when the request is idempotent. GET, PUT, DELETE, and HEAD are idempotent by definition. POST is not, unless an idempotency key is attached; when retrying POST, reuse the same key. Non-idempotent retries without a key risk duplicate side effects (double charges, duplicate records).

---

## 7. Reference Tables

### 7.1 Type Selection

| Requirement | Type | Link |
|---|---|---|
| Shared mutable state (sync) | `Mutex<T>` | [Mutex](https://doc.rust-lang.org/std/sync/struct.Mutex.html) |
| Concurrent reads, exclusive writes | `RwLock<T>` | [RwLock](https://doc.rust-lang.org/std/sync/struct.RwLock.html) |
| Shared ownership across threads | `Arc<T>` | [Arc](https://doc.rust-lang.org/std/sync/struct.Arc.html) |
| Async lock | `tokio::sync::Mutex` | [tokio Mutex](https://docs.rs/tokio/latest/tokio/sync/struct.Mutex.html) |
| Error propagation | `Box<dyn Error>` | [Error](https://doc.rust-lang.org/std/error/trait.Error.html) |
| Scoped threads | `thread::scope` | [scope](https://doc.rust-lang.org/std/thread/fn.scope.html) |
| Map with entry API | `HashMap` | [HashMap](https://doc.rust-lang.org/std/collections/struct.HashMap.html) |
| Lock-free counter | `AtomicUsize` | [AtomicUsize](https://doc.rust-lang.org/std/sync/atomic/struct.AtomicUsize.html) |
| Channel | `mpsc::channel` | [mpsc](https://doc.rust-lang.org/std/sync/mpsc/) |
| Platform config dirs | `directories` | [directories](https://crates.io/crates/directories) |
| CLI parsing | `clap` | [clap](https://docs.rs/clap/) |
| Library errors | `thiserror` | [thiserror](https://docs.rs/thiserror/) |
| Application errors | `anyhow` | [anyhow](https://docs.rs/anyhow/) |

### 7.2 Ownership and Sharing

| Scenario | Required wrapper |
|---|---|
| Single thread, single owner | None |
| Single thread, shared | `Rc<T>` |
| `thread::scope`, borrow local data | None |
| `thread::spawn`, data outlives scope | `Arc<T>` |
| `tokio::spawn`, data outlives task | `Arc<T>` |
| Interior mutation, sync context | `Mutex<T>` or `RwLock<T>` |
| Interior mutation, async context | `tokio::sync::Mutex<T>` |

Convention: place `Mutex` or `RwLock` inside the data structure; place `Arc` at the call site. `Arc<Inner>` inside a `#[derive(Clone)]` handle type is the standard pattern for client types that are designed to be cloned and shared freely.