<img class="plate" src="art/ch30.png" alt="Drill, the robot who is the sergeant of the timed round, beside a drill press over a workpiece stamped with a problem">

# Drills against the clock

<div class="covers" markdown="1">

This chapter covers

- Ten compact systems implementations sized for a 45-minute technical interview
- Cross-references mapping each compact drill to its full production-grade counterpart
- Deliberate engineering trade-offs omitted from the short forms, including a subtle lazy-iterator serialization defect
- Time-allocation discipline for a 45-minute live coding round and a structured rehearsal protocol

</div>

Production-grade systems primitives prioritize safety invariants, cache-line contention avoidance, and exhaustive failure handling; timed technical interviews impose a distinct constraint set: a blank buffer, a concise specification, and roughly forty minutes to deliver a verified implementation. The module `drills.rs` provides ten self-contained, interview-sized counterparts to the book's core concurrency, networking, and data-structure primitives, each paired with a unit test exercising primary behavior.

This reference guide indexes each drill against its full implementation, audits every deliberate simplification and behavioral divergence, and defines a repeatable rehearsal protocol for timed execution.

## 30.1 The drills

<p class="listing"><b>Listing 30.1</b> Ten answers sized for a live round. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/drills.rs">src/problems/drills.rs</a></p>

```rust
{{#include ../../rust-interview-lab/src/problems/drills.rs}}
```

The module header defines its architectural boundary: neighboring modules hold full reference implementations, while `drills.rs` isolates minimal versions achievable under time pressure. The table below maps each drill to its corresponding reference chapter and listing:

| Drill | Lines | Full version |
|---|---|---|
| `count_parallel`: `Arc<Mutex<usize>>` counter | 18 | chapter 8 (`total_with_arc_mutex`, listing 8.7), chapter 16 |
| `parallel_sum`: scoped threads | 12 | chapter 16, `threads::parallel_sum`, listing 16.5 |
| `SpinLock` and `SpinGuard` | 45 | chapter 16, listing 16.12 |
| `Semaphore` | 36 | chapter 16, listing 16.15 |
| `BlockingQueue` with `close` | 62 | chapter 17, listing 17.22 |
| `ThreadPool` with `Drop` | 45 | chapter 18, listing 18.7 |
| `retry` with backoff | 21 | chapter 19, listing 19.9 |
| `HashRing` | 33 | chapter 14, listing 14.9 |
| `parse_request_head` | 29 | chapter 21, listing 21.1 |
| `Port` newtype and `Route` enum | 32 | chapter 7 (the `GpuCount` newtype, listing 7.2); chapter 21, `route` |

## 30.2 What the short forms leave out

Omitting secondary features is acceptable under interview time constraints only when the author can articulate every omitted invariant and its production consequence during follow-up questioning.

**Test-and-set versus test-and-test-and-set in `SpinLock`.** The drill spins via `while self.locked.swap(true, Acquire) { spin_loop() }`, executing an atomic read-modify-write on every iteration. Under multicore contention, every spinning core repeatedly invalidates the lock's cache line across the interconnect (cache-line bouncing). The reference implementation in Chapter 16 uses `compare_exchange_weak` guarded by an inner `Relaxed` load loop, allowing waiting cores to spin on a shared read-only cache line until release. Both preserve mutual exclusion, but only the reference scales under contention. The drill also omits explicit `// SAFETY:` invariant documentation required in production reviews.

**Permit leakage in `Semaphore`.** Exposing bare `acquire` and `release` methods leaks a permit whenever a caller returns early or panics between calls. The reference design in Section 16.5 returns an RAII `SemaphoreGuard` whose `Drop` implementation releases the permit deterministically.

**Temporary drop order in `ThreadPool`.** Writing `let Ok(job) = receiver.lock().expect(..).recv() else { return; };` binds the job in a `let` statement, dropping the temporary `MutexGuard` at the semicolon prior to executing `job()`. Timing confirms true parallelism: four 200 ms tasks across four workers complete in 205 ms. Writing the identical receive inside `while let` would extend the `MutexGuard` lifetime across the loop body and serialize all worker threads (Chapter 18, Figure 18.2).

**Modulo wraparound and allocation in `HashRing`.** The drill maps past-the-end binary-search indices back to slot 0 via `partition_point(..) % self.points.len()` rather than an explicit branch, hashes `(input, replica)` directly without intermediate formatting, and stores an owned `String` per virtual node instead of sharing a single `Arc<str>`.

**Minimal validation in `parse_request_head`.** The drill enforces `HTTP/1.1`, splits headers on the first colon, and normalizes header names to lowercase, omitting header-size bounds, mandatory `Host` verification, and body framing. That scope matches a ten-minute parsing prompt; full HTTP server hardening requires the checks developed in Chapter 21.

**Concise domain validation in `Port` and `Route`.** `Port::new` encodes its range invariant in a single combinator pipeline: `(1..=u16::MAX).contains(&value).then_some(Self(value)).ok_or(..)`. `Route::parse` matches static paths directly and extracts parameterized IDs via `strip_prefix`, rejecting all unrecognized paths with `None`.

## 30.3 The drill that is slower than it looks

Unlike the intentional simplifications above, the drill version of `parallel_sum` alters asymptotic concurrency relative to the Chapter 16 reference:

```rust
// drills.rs
values
    .chunks(chunk_size)
    .map(|chunk| scope.spawn(move || ...))
    .map(|handle| handle.join().expect("worker panicked"))
    .sum()

// threads.rs
let handles: Vec<_> = values.chunks(chunk_size).map(|chunk| scope.spawn(...)).collect();
handles.into_iter().map(|handle| handle.join().expect("worker panicked")).sum()
```

Rust iterators are lazy. In `drills.rs`, `sum` pulls one element completely through both `map` adapters before requesting the next chunk. Consequently, the first worker thread is spawned and immediately *joined* before the second worker thread is even created, executing all four chunks strictly sequentially. The reference implementation forces eager spawning by collecting all `JoinHandle`s into a `Vec` before joining any of them.

Because sequential execution produces the identical arithmetic sum, a value-only unit test passes without flagging the bug. Timing four workers that each sleep for 200 ms exposes the serialization immediately:

```text
lazy spawn/join chain, four 200 ms workers: 809.402756ms (sum 4)
collect first, then join:              203.482125ms (sum 4)
```

Inserting a single `.collect::<Vec<_>>()` between the two `map` stages restores full parallelism. As established in the thread-pool analysis of Chapter 18, verifying concurrency requires either a synchronization barrier (such as `thread_pool_v2`'s `jobs_run_at_the_same_time`) or a wall-clock timing assertion rather than output-value equality alone.

## 30.4 Running a round

A 45-minute technical round follows five predictable phases. Allocating time deliberately protects the final seven minutes, where systems design maturity is evaluated, from last-minute debugging (Figure 30.1).

<figure>
<img src="figures/ch23-round.svg" alt="A bar split into 0 to 5 minutes clarify, 5 to 10 types first, 10 to 30 happy path then edge cases, 30 to 38 tests, 38 to 45 failure modes">
<figcaption><b>Figure 30.1</b> One way to spend a 45-minute round. The proportions matter more than the exact minutes.</figcaption>
</figure>

- **Clarify (0 to 5 min).** Lock down input contracts, invalid-input semantics, and operational bounds (capacity, concurrency, latency). Every constraint translates directly into a type invariant or guard clause.
- **Types first (5 to 10 min).** Specify enums, newtypes, and public function signatures before writing implementation bodies. Selecting `Result<T, ParseError>` early prevents structural rewrites mid-round.
- **Happy path, then edge cases (10 to 30 min).** Compile and pass one end-to-end path first, then layer in boundary checks, concurrency shutdown paths, and error variants.
- **Tests (30 to 38 min).** Write targeted unit tests covering empty inputs, capacity bounds, concurrent contention, and error returns rather than only the prompt's nominal example.
- **Failure modes (38 to 45 min).** Articulate scaling bottlenecks, kernel limits, and production hardening steps, drawing directly from the book's reference implementations.

## 30.5 Practicing with this repository

The repository supports a closed-loop rehearsal workflow for building timed fluency: implement a minimal correct structure within 30 to 45 minutes, then audit its failure modes and tests against the reference solution.

1. Select one drill and review its reference chapter once.
2. Close the chapter and reference source, then implement the primitive from a blank file in a scratch binary under `src/bin/`.
3. Execute `cargo test` on the implementation alongside the corresponding reference suites (`cargo test thread_pool`, `cargo test bounded_queue`, `cargo test --bin http_server`).
4. Diff the implementation against the reference module, cataloging every omission as either an intentional scope reduction or a correctness gap.
5. Verbalize the production failure modes and concurrency proofs aloud as if addressing a design review.

The "Questions that come up" sections at the end of each chapter supply targeted follow-up prompts for step 5. The iterative progressions preserved across the repository (eleven merge variants, nine pools, and six ring buffers) illustrate how minimal prototypes evolve into hardened systems components.

## 30.6 Questions that come up

**"A parallel sum returns the exact expected total. How can parallelism be verified?"**
Inspect thread lifecycle ordering to verify that all worker threads are spawned before any handle is joined; a lazy iterator chaining `spawn` and `join` executes serially. Confirm concurrency empirically with a `Barrier` test or a wall-clock timing assertion.

**"What changes are required to harden this spin lock for production?"**
Guard the atomic exchange with an inner `Relaxed` load spin loop to avoid cache-line bouncing, add backoff or thread yielding under sustained contention, document explicit `// SAFETY:` invariants on `unsafe impl Sync`, and prefer `std::sync::Mutex` unless profiling proves a spin lock is necessary.

**"A caller panics while holding a semaphore permit. What happens to the permit?"**
With bare `acquire`/`release` methods, the permit leaks permanently and reduces effective concurrency. Returning an RAII `SemaphoreGuard` whose `Drop` releases the permit guarantees leak-free cleanup across panics and early returns.

**"What criterion governs what to omit in a timed drill?"**
Match omissions strictly to the interview prompt's stated scope, while explicitly naming every omitted production invariant (such as `// SAFETY:` proofs, RAII guards, cache-line optimization, or bounds enforcement) and noting where an omission alters asymptotic or concurrency behavior.
