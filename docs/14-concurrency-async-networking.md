# 14: Concurrency, Async, and Networking

The systems modules in `rust-interview-lab` exist to prevent specific failure modes.
Each section below covers the mechanism behind one of them and the trade-offs it
encodes.

The modules it refers to:

| Module | Concept |
|---|---|
| `problems/threads.rs` | Threads, scopes, `Send`/`Sync`, atomics, `OnceLock` |
| `problems/smart_pointers.rs` | `Box`, `Rc`, `Arc`, `RefCell`, `Mutex`, `Weak`, `Cow` |
| `problems/adt_idioms.rs` | Newtype, enums with data, typed errors, `TryFrom` |
| `problems/semaphore.rs` | Counting semaphore, permits, RAII release |
| `problems/spin_lock.rs` | A lock built from an atomic, memory ordering |
| `problems/bounded_queue.rs` | Bounded MPMC queue, backpressure, shutdown |
| `problems/ring_buffer.rs` | Lock-free SPSC ring, atomic memory ordering |
| `problems/sharded_cache.rs` | Sharding to reduce lock contention |
| `problems/bump_allocator.rs` | Alignment, arena allocation |
| `problems/retry.rs` | Exponential backoff, jitter, `Retry-After` |
| `problems/consistent_hash.rs` | Virtual-node ring, minimal remapping |
| `problems/async_mini.rs` | `Future`, `Waker`, `Pin`, `block_on`, executor |
| `problems/http_request.rs` | HTTP/1.1 framing, parsing, smuggling checks |
| `bin/tcp_echo_server.rs` | Blocking sockets, thread per connection |
| `bin/http_server.rs` | REST routing, keep-alive, status codes |
| `bin/epoll_echo.rs` | Readiness notification, partial writes, backpressure (optional; niche) |

---

## Fundamentals in short form

One or two lines each. The sections after this one cover the mechanism.
Standalone runnable versions of several of these are in `rust-interview-lab/src/bin/`:
`os_paging`, `os_scheduler`, `concurrency_deadlock`, `concurrency_amdahl`,
`concurrency_false_sharing`, `net_ipv4`, `net_window`, `cs_fib`, `cs_locality`.

### Operating systems

- **Process vs thread.** A process owns an address space; threads in it share that
  space and differ only in registers and stack.
- **Context switch.** Save one task's registers, restore another's. Costs
  microseconds and disturbs caches and the TLB.
- **User vs kernel space.** User code cannot touch hardware or kernel memory. It
  asks through a system call.
- **System call.** A controlled trap into the kernel. Registers carry a number and
  arguments; the result comes back with `errno` on failure.
- **Virtual memory.** Page tables map virtual addresses to physical frames per
  process, which gives isolation and lazy allocation.
- **Page fault.** A mapping is missing or protected. Minor if the page is in RAM,
  major if it must be read from disk.
- **Copy-on-write.** `fork` shares pages read-only and copies one only when either
  side writes.
- **`fork` vs `exec`.** `fork` creates a child; `exec` replaces the current image
  and keeps the same PID.
- **Scheduling.** The kernel preempts runnable tasks on a timer, choosing by
  priority and fairness.
- **File descriptor.** A small per-process integer naming an open file, socket, or
  pipe. It is a capability, and 0/1/2 are stdin/stdout/stderr.
- **Buffering.** stdio buffers in user space. Without a flush, output is lost on
  `_exit` or a crash.
- **Interrupt vs polling.** An interrupt stops the CPU and runs a handler; polling
  checks a status register on a schedule.

### Concurrency

- **Race condition.** The result depends on timing because two threads touch
  shared state without synchronization.
- **Critical section.** The code that must run under mutual exclusion.
- **Mutex.** Blocks other threads and sleeps rather than spins. The default choice.
- **Spin lock.** Busy-waits on an atomic. Only for very short sections with no
  oversubscription.
- **Semaphore.** Counts permits. It bounds concurrency rather than protecting data.
- **Condition variable.** Waits until a predicate holds, and the predicate is
  rechecked in a loop because wakeups can be spurious.
- **Atomic and ordering.** An atomic read-modify-write is indivisible. Acquire and
  release orderings are what publish the surrounding data.
- **Deadlock.** Needs mutual exclusion, hold-and-wait, no preemption, and circular
  wait. Breaking any one prevents it.
- **Livelock vs starvation.** Livelock is active work with no progress; starvation
  is never being chosen.
- **Thread pool.** Fixed workers over a queue. Bounds concurrency and avoids
  per-task thread creation.
- **Producer/consumer.** A bounded queue between the two. The bound is what
  provides backpressure.
- **Amdahl's law.** Speedup is capped by the serial fraction of the work.
- **False sharing.** Two unrelated variables on one cache line cause the line to
  bounce between cores.

### Networking

- **Layers.** Link, internet, transport, application. Each adds addressing or
  reliability.
- **TCP vs UDP.** TCP is connection-oriented, ordered, and retransmits; UDP sends
  datagrams with no ordering or delivery guarantee.
- **Three-way handshake.** SYN, SYN-ACK, ACK. It agrees sequence numbers and
  confirms both directions work.
- **Teardown.** FIN and ACK in each direction. The side that closes first waits in
  `TIME_WAIT` so delayed packets expire.
- **Flow vs congestion control.** The receiver window protects the receiver; the
  congestion window protects the network. The effective window is the smaller.
- **Socket API.** `socket`, `bind`, `listen`, `accept`, `connect`. A connection is
  identified by the four-tuple of addresses and ports.
- **Blocking vs non-blocking.** A blocking read sleeps; a non-blocking read returns
  `EAGAIN`, and the caller retries later.
- **DNS.** Resolves names to addresses, usually over UDP, with caching and TTLs.
- **HTTP.** Request and response over TCP. Methods carry safe and idempotent
  semantics; the body is framed by `Content-Length` or chunked encoding.
- **TLS.** Encryption and authentication between TCP and the application. The
  handshake costs an extra round trip.
- **NAT.** Rewrites addresses and ports so many hosts share one public address.
- **Latency vs bandwidth.** Latency is delay per request, bandwidth is volume.
  Adding bandwidth does not reduce latency.
- **Load balancing.** Spreads connections across backends. Consistent hashing keeps
  keys pinned to a backend when membership changes.

### Data structures and complexity

- **Big-O.** Growth of cost with input size, ignoring constants and lower terms.
- **Amortized cost.** Occasionally expensive, cheap on average, as with `Vec`
  growth.
- **Array vs linked list.** Contiguous memory is cache-friendly; a list gives O(1)
  splice at the cost of pointer chasing.
- **Hash map.** O(1) average, O(n) worst case under collisions, and iteration
  order is unspecified.
- **Heap.** O(1) peek, O(log n) push and pop. Used for top-k and schedulers.
- **Balanced tree.** O(log n) lookup with sorted iteration and range queries.
- **Stack vs queue.** LIFO versus FIFO, the basis of DFS and BFS.
- **Recursion vs iteration.** Recursion uses the call stack; convert to iteration
  when depth is unbounded.
- **Memoization.** Cache subproblem results and turn exponential recursion into
  polynomial.
- **Cache locality.** Sequential access is far faster than random access because
  memory moves in cache lines.
- **Idempotency.** Repeating an operation has the same effect. It is what makes a
  retry safe.
- **CAP.** During a network partition, choose consistency or availability.

---

## 1. The execution model

A process has its own address space. A thread is a task that shares that address
space, the file-descriptor table, and signal handlers with the tasks in the same
thread group. On Linux both are the same kernel object, `task_struct`, which is
covered in `02-linux-concepts.md`. The practical consequence is that threads are
cheap to create relative to processes and expensive to switch relative to
function calls.

The operating system offers two ways to wait for I/O:

- **Blocking.** `read` returns when data is available, and the thread is not
  scheduled in the meantime. The code reads top to bottom and the kernel handles
  the waiting.
- **Non-blocking.** `read` returns `EAGAIN` when no data is available, and the
  caller must decide what to do next. The waiting is now the program's problem.

From that choice follow the two server architectures:

| Model | How it waits | Strength | Cost |
|---|---|---|---|
| Thread per connection | Blocking calls | Straightforward code, isolated failures | One stack per connection, context switches, hard limits at high concurrency |
| Event loop | Non-blocking calls plus a readiness API | One thread can manage many connections | State per connection, partial reads and writes, more complex control flow |

`bin/tcp_echo_server.rs` is the first model. `bin/epoll_echo.rs` is the second.
Neither is generally better; a bounded thread pool handles blocking work such as
DNS or disk well, while an event loop handles tens of thousands of mostly idle
connections that a thread stack per connection could not afford.

There is also a distinction in how the kernel reports I/O:

- **Readiness (reactor).** The kernel says a socket can be read or written; the
  program performs the transfer. This is `select`, `poll`, and `epoll`.
- **Completion (proactor).** The program submits an operation and the kernel
  reports when it is finished. This is `io_uring` and IOCP.

The two produce different code. A reactor loops until `EAGAIN` and owns the
buffers. A proactor is handed a buffer and a completion. Most progress in Linux
networking has been toward completion interfaces, but readiness is still the
default in production and in every mainstream runtime.

---

## 2. Threads and fearless concurrency

Rust's concurrency guarantee is specific: safe code cannot produce a data race.
Two marker traits encode the rule, and both are auto traits, meaning a type
implements them when its fields do.

- `Send`: a value may be moved to another thread.
- `Sync`: `&T` may be shared across threads, equivalently `&T: Send`.

The counter-examples are what make the rule useful. `Rc<T>` and `RefCell<T>` are
neither `Send` nor `Sync`, because their reference counting and borrow flag are
not atomic. Moving an `Rc` into `thread::spawn` does not compile, and that error
is a data race caught before it can run. When a type is only safe under a
documented contract, `unsafe impl Send` or `unsafe impl Sync` asserts that
contract; the safety comment then has to state exactly what the caller must not
do.

### Getting work onto a thread

`problems/threads.rs` shows the three levels of ceremony:

- **`thread::scope`** for work that borrows local data and finishes before the
  scope returns. The workers borrow the slice directly, so there is no `Arc` and
  no `'static` bound, and the scope joins automatically. This removes the
  forgotten-join bug by construction.
- **`thread::spawn`** for work that must own its data. The closure must be
  `'static`, so shared state is carried in an `Arc` and the result comes back
  through the `JoinHandle`.
- **A pool** when there are many small units of work. Creating a thread per task
  costs more than the task when the tasks are short.

`thread::available_parallelism` reports how many threads can run at once, which
is the appropriate basis for choosing a chunk count or a pool size.

### Choosing how to share

| Need | Tool |
|---|---|
| Immutable data, borrowed by workers | `thread::scope` and `&T` |
| A counter | `AtomicUsize` with `fetch_add` |
| A compound invariant across several fields | `Mutex<T>` or `RwLock<T>` |
| Transfer of ownership to another task | `mpsc` channel |
| One-time initialization | `OnceLock<T>` |

The distinction between an atomic and a mutex is not performance. An atomic
maintains a single value; a mutex maintains an invariant over a group of values
that must change together. Replacing a mutex with several atomics turns one
atomic update into several, and the intermediate states become observable.

### Failure modes that remain

The compiler removes data races, not every concurrency bug. The ones that
survive are logic errors:

- **Deadlock.** Two threads take two locks in opposite orders, or one thread
  takes a non-reentrant lock twice. A global lock order, and releasing locks
  before acquiring others, prevents both.
- **Lost updates at a higher level.** Read a value, compute, write it back
  without holding the lock for the whole sequence.
- **Blocking an async executor.** Blocking calls belong on a dedicated thread,
  which section 11 covers.
- **Unbounded growth.** A channel or queue with no bound converts a slow consumer
  into an out-of-memory kill, which section 7 covers.

---

## 3. Smart pointers and interior mutability

Ownership in Rust is single by default. Shared ownership and shared mutation are
added deliberately, with a pointer type that states which of the two is being
requested.

| Type | Ownership | Mutation | Across threads |
|---|---|---|---|
| `Box<T>` | single | through `&mut` | if `T: Send` |
| `Rc<T>` | shared, non-atomic count | no | no |
| `Arc<T>` | shared, atomic count | no | if `T: Send + Sync` |
| `RefCell<T>` | single | runtime checked | no |
| `Mutex<T>` | single | blocking lock | yes |
| `Weak<T>` | non-owning | no | as `Arc` |
| `Cow<'a, T>` | borrow or own | no | as the borrow |

`Rc` with `RefCell` covers graphs, trees, and caches confined to one thread;
`Arc` with `Mutex` covers state shared between threads. Mixing the two is a
compile error, which is the intended outcome.

`Box` is the indirection that makes a recursive type possible. An `enum` that
contains itself by value has no finite size, so the recursive arm holds a `Box`
instead.

`RefCell` moves the borrow check from compile time to run time. A `borrow_mut`
while another borrow is active panics rather than failing to compile, so borrows
are kept short and are not held across a call that might borrow again.

`Weak` exists to break cycles. If two `Rc` values point at each other, each count
stays above zero and neither is freed. A parent/child relationship therefore
stores the child strongly and the parent weakly, so an unreachable tree is
dropped. `TreeNode` in `problems/smart_pointers.rs` demonstrates the shape and a
test asserts that dropping the parent makes the child's `parent_value` return
`None`.

`Cow` is the return type for a function that usually passes its input through.
`normalize` returns a borrowed slice when no change is needed and an owned string
only when it changes, so the common path allocates nothing.

---

## 4. Algebraic data types and quick idioms

Several patterns are short to write and remove whole classes of error.
`problems/adt_idioms.rs` implements each one.

**Newtype for a validated primitive.** `struct GpuCount(u32)` has one constructor,
`GpuCount::new`, which rejects values outside `1..=64`. An invalid count cannot
exist, so no later function needs to re-check it. The field is private, and
`From<GpuCount> for u32` allows reading the value out.

**Enum with data for a closed set of alternatives.** `Command` has `List`, `Get`,
`Create`, and `Delete` variants, and `Create` carries the name and the validated
count. `match` forces every variant to be handled, so adding a variant later
produces compile errors at each place that needs updating rather than a silent
fallthrough.

**Typed errors instead of strings.** `CommandError` distinguishes an empty line,
an unknown verb, a missing argument, and an invalid count. A caller can match on
the case that matters and still print the others. An error type that is only a
`String` forces every caller to parse it.

**`TryFrom` at the boundary.** Validation belongs where data enters the program.
Implementing `TryFrom<u32> for GpuCount` means parsing and range checking happen
once, at the edge, and the rest of the code receives a value that is already
valid.

**Iterator chains over index loops.** `summarize` computes a count and a sum in a
single `fold`. The intent is stated once, there is no index to get wrong, and the
compiler can bound-check the access.

The same idea appears in `problems/state_machine.rs`, where lifecycle transitions
are an `enum` and an exhaustive `match` on `(current, next)` makes an illegal
transition impossible to forget.

---

## 5. Synchronization primitives

### Mutex

A mutex enforces mutual exclusion; the substance is in the discipline around the
lock and unlock calls.

- The lock is released by dropping the guard, so an early return or a panic does
  not leave the mutex locked. That property is the reason the guard type exists
  rather than separate `lock`/`unlock` functions.
- If a thread panics while holding the guard, the mutex is poisoned and later
  callers receive an error. The choice is to propagate the panic with `unwrap`,
  or to recover the data with `into_inner` when the invariant still holds.
- A `Mutex` protects data, not a code region. The data lives inside the mutex so
  that access without the lock is not expressible in the type system.

`std::sync::Mutex` is not reentrant. Locking it twice in one thread deadlocks.
This is a common cause of a hang that looks like an unrelated stall.

### Condition variable

A condition variable lets a thread sleep until a predicate becomes true. It is
always used with a mutex, and the mutex is what makes the predicate safe to read.

The correct pattern is a loop:

```rust
let mut state = mutex.lock().expect("poisoned");
while !predicate(&state) {
    state = condvar.wait(state).expect("poisoned");
}
// The predicate is now true and the lock is held.
```

Three details justify the loop and the mutex:

- The predicate is checked while holding the mutex, so a notification cannot
  arrive between the check and the wait and be lost.
- `wait` releases the mutex while sleeping and reacquires it before returning, so
  the notifier can take the lock.
- `wait` may return without a matching signal. Spurious wakeups are permitted, so
  the condition must be rechecked rather than assumed.

`problems/bounded_queue.rs` uses this pattern twice, once for waiting consumers
and once for waiting producers.

### Semaphore

A semaphore holds a count of permits. `acquire` takes one and blocks when none
are free; `release` returns one. It limits concurrency without protecting data.

`problems/semaphore.rs` returns a guard from `acquire_guard`, `try_acquire`, and
`try_acquire_timeout`, so the permit is returned on drop. Without the guard, an
error path that forgets to release leaks a permit and the pool slowly degrades to
zero throughput.

Choosing between the three:

| Primitive | Question it answers |
|---|---|
| Mutex | May I touch this data now? |
| Condition variable | Is this condition true yet? |
| Semaphore | May I proceed, given N slots are free? |

A channel is a semaphore plus a queue. One bounded queue serves both roles; a
queue guarded by a separate semaphore is how the two get out of step.

---

## 6. Building a primitive: the spin lock

`problems/spin_lock.rs` implements a lock from a single `AtomicBool`. A lock has
two obligations, and a correct implementation satisfies both.

1. **Mutual exclusion.** At most one thread holds the lock, so handing out
   `&mut T` to the guard is sound.
2. **Memory visibility.** A thread that acquires the lock observes every write the
   previous holder made before releasing it.

The second obligation is the one that is easy to miss. The lock word alone is not
enough; the ordering on the atomic operations is what publishes the protected
data.

- Acquisition uses `compare_exchange_weak` with `Acquire` on success. An acquire
  pairs with a release, so the critical section sees the previous holder's writes.
- Release uses a plain `store` with `Release`. Every write in the critical
  section is ordered before the release, so the next acquirer will see it.
- The waiting loop spins on a `Relaxed` load and calls `spin_loop()`. A relaxed
  load does not claim the cache line exclusively, and `spin_loop` is a hint that
  the core is in a spin, so contention does not keep bouncing the line between
  cores.
- The guard derefs to `&T` and `&mut T` and releases the lock in `Drop`, so the
  lock cannot be leaked by an early return.
- `unsafe impl<T: Send> Sync for SpinLock<T>` is the assertion that the ordering
  discipline above is correct. `Send` is derived automatically, because an
  `UnsafeCell<T>` is `Send` when `T` is.

A spin lock is the wrong default. A waiting thread occupies a core, so it is only
appropriate when the critical section is very short and the threads are not
oversubscribed. On a machine with more runnable threads than cores it can invert
priorities and starve the lock holder, which is why `std::sync::Mutex` parks the
thread instead and is the correct choice in general code. The value of writing
one is that it makes the acquire/release contract explicit.

---

## 7. Queues and backpressure

An unbounded queue converts a slow consumer into an out-of-memory kill. The
producer never blocks, so memory grows at the rate of the difference between
arrival and service. A bounded queue instead makes the producer wait, which
propagates the slowdown to wherever it can be handled.

`problems/bounded_queue.rs` implements `BoundedQueue<T>` with one mutex and two
condition variables:

- `push` blocks while the queue is full and returns `Err(item)` once the queue is
  closed, so the caller keeps ownership of the value rather than losing it.
- `pop` blocks while the queue is empty and returns `None` once the queue is
  closed and drained, which is how a consumer loop terminates.
- `close` wakes both sides, so shutdown cannot hang behind a blocked producer or
  consumer.

The `close` method matters as much as the bounds. Without it, a consumer blocked
on an empty queue when the producer stops has no way to learn that no more work
is coming, and the shutdown path depends on a timeout.

Backpressure belongs at every layer that accepts unbounded input: the listener
stops accepting, the connection stops reading, the queue blocks the producer,
and the client honors `Retry-After`. Adding it at only one layer moves the growth
somewhere else.

---

## 8. Atomics and lock-free structures

An atomic operation is indivisible with respect to other threads. The ordering
argument is what makes atomics useful for communication rather than just for
counting.

- `Relaxed` gives atomicity with no ordering guarantees. It is correct for
  counters whose value is not used to publish other data.
- `Release` on a store means that all writes before it are visible to a thread
  that observes the store.
- `Acquire` on a load means that all writes published by a matching release store
  are visible after it.
- `SeqCst` adds a single total order across all such operations. It is the
  easiest to reason about and the most expensive.

The publication rule: write the data, then publish the
index with a release store; read the index with an acquire load, then read the
data. `problems/ring_buffer.rs` follows it exactly.

### Single-producer, single-consumer ring

`SpscRing<T, N>` keeps two indices. The producer owns `tail` and the consumer
owns `head`, so neither index needs a compare-and-swap. The slot at an index is
written before `tail` is published, and read only after the consumer's acquire
load of `tail` reaches it. One writer per slot is what makes the unsafe block
sound, and the code documents that obligation rather than hiding it.

Two producers would race on `tail`, and two consumers
would race on `head`. A multi-producer queue needs a different algorithm, and in
most cases a mutex around a `VecDeque` is fast enough that the lock-free version
is not worth the maintenance.

---

## 9. Contention and sharding

A single mutex around a map serializes every access, even when the accesses touch
different keys. `problems/sharded_cache.rs` splits the map into a power-of-two
number of shards, each with its own lock, and picks the shard from the hash of
the key. Independent keys then proceed in parallel.

Consequences:

- `len` and `clear` must visit every shard, so they are O(shards) and not
  instantaneous.
- There is no atomic snapshot of the whole map, so a caller cannot observe a
  consistent state across shards.
- The shard count is fixed at construction. Rehashing every key on resize would
  need a different structure.

The mask replaces a modulo because the shard count is a power of two. `with`
allows a read or update of a single key under its shard lock without cloning the
value, which matters when the value is large or not cheaply cloneable.

False sharing is the related hardware problem. Two unrelated atomics that land on
the same cache line cause the line to move between cores on every write, even
though the threads never touch the same variable. Padding or separating hot
counters by a cache line removes it. The cost is invisible in the source and
visible in `perf`.

---

## 10. Memory layout and arenas

Alignment is a contract with the hardware. An object of size `n` must begin at an
address that is a multiple of its alignment, and misaligned access is either slow
or illegal depending on the platform. For an allocator, the requirement is
expressed as `alloc(size, align)` returning a slice whose start address satisfies
the alignment.

`problems/bump_allocator.rs` implements the simplest allocator that meets the
contract. It keeps a cursor into a byte buffer, rounds the cursor up to the
requested alignment, and advances it by the size. Allocation is O(1), there is no
free list or bookkeeping, and memory is reclaimed all at once with `reset`.

The limitation follows from the design. Individual allocations cannot be freed,
so a long-lived arena that mixes short-lived and long-lived objects wastes the
space of the short-lived ones. Arenas fit request parsing, per-frame upload
buffers, and other phases where all objects have the same lifetime.

Alignment padding is part of the accounting. Allocating one byte and then a
sixteen-byte-aligned block consumes more than seventeen bytes, and `used` reports
the padded total, so the difference is visible in the accounting.

---

## 11. Async Rust

An `async` function is compiled into a state machine that implements `Future`.
The trait has one method:

```rust
fn poll(self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<Self::Output>;
```

The contract has three parts:

- A future does nothing until it is polled. Creating one has no effect.
- `Poll::Ready(value)` means the work is finished and the future must not be
  polled again.
- `Poll::Pending` means the work is not finished, and the future must arrange for
  the `Waker` in the `Context` to be called when progress becomes possible.

That last point is where implementations go wrong. A future that returns
`Pending` and never calls the waker is a silent hang, because the executor has no
reason to poll it again.

### Pin

Polling takes `Pin<&mut Self>` because a generated state machine can hold a
reference to its own local across an `await`. Moving such a future after polling
would invalidate that reference, so the value is pinned in place. `Unpin` is the
marker trait for types that are safe to move while pinned; most ordinary types
are `Unpin`, and generated futures frequently are not.

### Executor

`problems/async_mini.rs` implements the two pieces of a runtime:

- `block_on` pins one future, polls it in a loop, and parks the thread on
  `Pending`. The waker unparks it. Parking rather than spinning keeps the CPU free
  while the future waits.
- `MiniExecutor` keeps a queue of tasks. A task holds its future and a waker; the
  waker's job is to put the task back on the queue. `run` pops tasks, polls each
  one, and finishes when the queue is empty.

The re-enqueue step is why a task handle must be an `Arc`. Both `wake` and
`wake_by_ref` bump a reference count rather than copying the future.

### Where blocking fits

Blocking inside an async task starves the executor thread, because nothing else
runs while it waits. Blocking work is pushed to a separate thread pool
(`spawn_blocking` in Tokio), where one blocked thread costs one stack rather than
stalling every task on the executor.

`Send` decides what may be spawned on a multi-threaded executor. A future is
`Send` when every value held across an `await` is `Send`. Holding a
`std::sync::MutexGuard` across an `await` is the standard example that fails,
because the guard is not `Send`; the fix is to scope the lock so it is released
before the await, or to use an async-aware mutex when the lock must be held
across suspension.

### Async is readiness, wrapped

An executor is a readiness loop with a task queue in front of it. The executor
registers interest in the socket, the reactor reports readiness, the waker marks
the task runnable, and the executor polls it again. Understanding `epoll` makes
async runtimes predictable.

---

## 12. I/O multiplexing

`select`, `poll`, and `epoll` all report which file descriptors are ready.

| Interface | Cost per call | Limit |
|---|---|---|
| `select` | O(n) and copies the sets | Low descriptor ceiling |
| `poll` | O(n) | No practical ceiling |
| `epoll` | O(ready) for the wait | Linux only |

`epoll` keeps the interest list in the kernel, so registering a descriptor is
separate from waiting for events. `kqueue` is the BSD and macOS equivalent, and
IOCP is the Windows completion model.

### Level and edge triggered

- **Level triggered** reports an event for as long as the condition holds. A
  socket with unread data is reported again on the next call.
- **Edge triggered** reports only when the state changes. It requires reading
  until `EAGAIN`, because a single notification covers all the data that arrived.

Edge triggering is more efficient and easier to get wrong. A missed drain leaves
a connection idle with data still buffered, and the bug appears only under load.

### Partial writes

A non-blocking write may accept fewer bytes than it was given. `bin/epoll_echo.rs`
keeps an output buffer per connection and tracks how much has been written.
Interest in `EPOLLOUT` is registered only while bytes remain and is dropped once
the buffer drains.

The alternative, writing until the socket accepts everything, blocks the loop.
One slow client then stalls every other connection. This is the single most
common defect in a hand-written event loop, and it is a correctness bug rather
than a performance detail.

### Errors and shutdown

- `EAGAIN` means try later, not failure.
- `EINTR` means the call was interrupted by a signal and is retried.
- A write to a socket whose peer has closed raises `EPIPE`, and the default
  action for `SIGPIPE` is to terminate the process. Servers ignore `SIGPIPE` and
  handle the error.
- Graceful shutdown stops accepting, stops reading new requests, drains
  in-flight work, and closes idle connections. Connections that outlive a
  deadline are closed forcibly. A shutdown that waits for every connection
  without a deadline never completes.

---

## 13. TCP for server work

The connection lifecycle matters because most production surprises are state
transitions rather than data transfer.

- **Setup.** A three-way handshake establishes the connection. `listen` sets a
  backlog; completed handshakes wait in the accept queue until `accept` returns
  them. If `accept` is slow and the queue fills, new connections are dropped or
  `SYN` cookies engage. A server that accepts more slowly than it is probed
  reports failures that look like network problems.
- **Teardown.** A close sends `FIN`, the peer acknowledges, and the side that
  initiated the close enters `TIME_WAIT` for twice the maximum segment lifetime.
  That state lets delayed packets expire before the port is reused.
- **Half close.** `shutdown` with `SHUT_WR` sends `FIN` while leaving the read
  direction open. A peer that has finished sending is not necessarily finished
  receiving, and treating the end of input as the end of the connection truncates
  replies.

Socket options that come up in practice:

| Option | Effect |
|---|---|
| `SO_REUSEADDR` | Bind while a previous socket is in `TIME_WAIT`, or to a different address on the same port |
| `SO_REUSEPORT` | Let several sockets bind the same port; the kernel balances incoming connections |
| `TCP_NODELAY` | Disable Nagle's algorithm, which otherwise coalesces small writes |
| `SO_KEEPALIVE` | Enable TCP keepalive probes; the default interval is far too long to detect a dead peer promptly |

Nagle's algorithm trades latency for fewer packets, which is the wrong trade for
an interactive protocol. It interacts with delayed acknowledgements to produce
latency spikes with no obvious cause, so request-response servers disable it.

Detection of dead peers is usually an application concern. A heartbeat at a
chosen interval, with a deadline for a response, is more predictable than tuning
the kernel's keepalive timers.

---

## 14. HTTP/1.1 and REST

### Message framing

An HTTP/1.1 message is a request line, a set of headers, an empty line, and an
optional body. Deciding where the body ends is the part with security
consequences.

- `Content-Length` gives the exact byte count.
- `Transfer-Encoding: chunked` sends the body in length-prefixed pieces and ends
  with a zero-length chunk, which is how a length is sent when it is not known in
  advance.
- If neither is present, a request has no body.

Two framing rules are mandatory:

1. A message that carries both `Content-Length` and `Transfer-Encoding` is
   ambiguous. Two servers in the path may disagree about where the body ends, and
   the smuggled remainder is parsed as a second request. The safe response is to
   reject the message.
2. Multiple `Content-Length` values that disagree are also rejected. Equal
   duplicates are tolerated by some parsers, but strict rejection avoids relying
   on that.

`problems/http_request.rs` enforces both and returns a typed `ParseError`
(`AmbiguousBodyLength`, `MissingHost`, `Malformed`, `UnsupportedTransferEncoding`,
`PayloadTooLarge`, or `Incomplete`). `Incomplete` is separate from the error
cases because it is not a failure: it means more bytes are needed, so the caller
reads and parses again.

Two further checks belong in the parser:

- HTTP/1.1 requires exactly one `Host` header, and a request without one is
  rejected.
- A header line that begins with a space is the obsolete line-folding syntax.
  Implementations disagree about how to interpret it, so it is rejected.

Limits are part of the parser's job. Bounded header and body sizes prevent a
client from holding a connection open by sending a few bytes at a time.

### Connection reuse

HTTP/1.1 keeps a connection open by default; HTTP/1.0 requires
`Connection: keep-alive`. The server loops, reads the next request from the same
buffer, and closes when the client asks for it, when the protocol is 1.0 without
keep-alive, or when an error makes the connection state uncertain.

Responses on one connection are written in request order. Pipelining sends
several requests before the first response and is rarely worth supporting; the
practical failure is head-of-line blocking, where a slow first request delays
everything behind it.

### REST semantics

The method carries a contract that clients and proxies rely on:

| Method | Safe | Idempotent |
|---|---|---|
| `GET`, `HEAD`, `OPTIONS` | Yes | Yes |
| `PUT`, `DELETE` | No | Yes |
| `POST` | No | No |
| `PATCH` | No | Not necessarily |

`bin/http_server.rs` returns `405` for a known path with the wrong method and
`404` for an unknown path. A `404` for a supported path with an unsupported
method hides a routing bug from the client.

For operations that are not idempotent, an idempotency key on the request lets
the server recognise a retry and return the original result rather than creating
a duplicate. This is the mechanism that makes client-side retries safe, and it
belongs to the API design rather than to the retry loop.

---

## 15. Retries and consistent hashing

### Retry

`problems/retry.rs` separates the policy from the operation.

- The delay grows exponentially and is capped, so an attempt sequence is bounded
  in time.
- Jitter spreads clients out. Full jitter picks a delay uniformly between zero
  and the capped backoff. Without it, every client that failed at the same moment
  retries at the same moment, and the server receives the same load spike again.
- `Retry-After` is a floor, not a suggestion. When the server states a delay, the
  client waits at least that long.
- Only retryable errors are retried. A request rejected with `InvalidRequest` or
  `NotFound` produces the same result on every attempt, so retrying it wastes the
  client's remaining budget.

Two rules keep retries from making an outage worse: only operations that are
idempotent, or that carry an idempotency key, are retried; and the total effort is
bounded by a deadline or attempt budget, so a failing dependency does not
accumulate unbounded work in the client.

Injecting the random source as a closure (`unit_random`) keeps the delay
computation deterministic under test while the production path uses a system
generator.

### Consistent hashing

Hashing a key to `hash(key) % N` and then changing `N` remaps nearly every key.
Caches lose their contents and sharded queues move almost all of their work.

`problems/consistent_hash.rs` places each node at several points on a ring and
sends a key to the first point at or after the key's hash. Adding or removing a
node moves only the keys that the changed node owns. Each physical node is
placed at `replicas` points, called virtual nodes, because a single point per
node produces an uneven split; more replicas give a smoother distribution.

The test in the module asserts the property directly: after adding a node, every
key either keeps its previous owner or moves to the new node. That invariant is
the reason the structure is used.

---

## 16. How the pieces fit

A request arriving at a GPU control plane touches most of these mechanisms in
sequence.

1. The listener accepts a connection. `SO_REUSEADDR` allows a restart while old
   sockets are in `TIME_WAIT`, and the accept queue determines how many pending
   connections survive a burst.
2. The request is parsed with bounded sizes. Framing ambiguity is rejected, and
   incomplete data returns to the read path rather than failing.
3. Routing decides the handler. The method contract determines whether a retry
   is safe.
4. The handler acquires a permit from a semaphore so that concurrent work stays
   within a known limit, and may read through a sharded cache.
5. Work that can fail transiently is wrapped in the retry policy. The random
   source provides jitter, and a server hint raises the delay floor.
6. Downstream calls are distributed across backends with consistent hashing, so
   a membership change moves a fraction of the keys rather than most of them.
7. The response is written through an output buffer. Partial writes are buffered
   and completed when the socket is writable, so one slow client does not stall
   the server.
8. Shutdown closes the queue, which wakes blocked producers and consumers, and
   signals the event loop to stop accepting.

Each step has a failure mode that the corresponding module addresses. The same
structure appears in production systems at a larger scale.
