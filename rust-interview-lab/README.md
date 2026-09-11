# Rust Interview Lab

Rust examples for the **NVIDIA Senior Cloud Software Engineer** interview.

This is not a toy DSA dump. Every problem is written the way senior Rust reviewers
expect: `enum`/ADTs for state, `Option`/`Result` for optionality and errors,
`match`/guards instead of nested `if` soup, and tests that prove the code runs.

## Coverage

### LeetCode-style / DSA problems

| Problem | File | Core technique |
|---|---|---|
| Two Sum | `two_sum.rs` | HashMap, one pass |
| Valid Parentheses | `valid_parentheses.rs` | Stack, `match` |
| Merge Intervals | `merge_intervals.rs` | Sorting, clean `match last_mut()` |
| Top K Frequent Elements | `top_k_frequent.rs` | HashMap + BinaryHeap |
| Min Stack | `min_stack.rs` | Parallel stack, O(1) min |
| Binary Tree: depth, invert, traversals | `binary_tree.rs` | `enum Tree` ADT; methods `max_depth`, `invert`, `preorder`, `inorder`, `postorder` |
| Trie / Prefix Search | `trie.rs` | HashMap trie, SDK/CLI autocomplete |
| Longest Substring Without Repeating Characters | `sliding_window.rs` | Sliding window |
| Course-schedule style topological sort | `graph_topology.rs` | Kahn's algorithm, `Option<Vec<_>>` for cycles |
| Reverse Linked List | `linked_list.rs` | `Option<Box<ListNode>>`, borrow-safe pointer reversal |
| Search in Rotated Sorted Array | `binary_search.rs` | O(log n) binary search |
| Coin Change | `dp.rs` | Dynamic programming, `Option<i32>` instead of `-1` |
| Subsets | `backtracking.rs` | Backtracking, recursion + path push/pop |
| LRU Cache | `lru_cache.rs` | `HashMap` + `VecDeque`, lazy eviction, interview-friendly |

### Cloud / SDK / CLI systems problems

| Problem | File | Core technique |
|---|---|---|
| Thread-safe token bucket | `rate_limiter.rs` | `Mutex<BucketState>`, real-time refill |
| Bounded worker pool | `worker_pool.rs` | Channels, `Arc<Mutex<Receiver>>`, ordered results |
| Workload state machine | `state_machine.rs` | Rust `enum` ADT, exhaustive `match` transitions |
| Typed API errors | `state_machine.rs` | `enum ApiError`, `is_retryable()`, associated data |

### Systems, concurrency, and networking problems

| Problem | File | Core technique |
|---|---|---|
| Interview drills (short answers) | `drills.rs` | Compact versions of the classic prompts, 14 to 64 lines each |
| Threads and fearless concurrency | `threads.rs` | `thread::scope`, `Send`/`Sync`, atomics, `OnceLock` |
| Smart pointers and interior mutability | `smart_pointers.rs` | `Box`, `Rc`/`RefCell`, `Arc`/`Mutex`, `Weak`, `Cow` |
| ADT idioms | `adt_idioms.rs` | Newtype, enum with data, typed errors, `TryFrom` |
| Spin lock from scratch | `spin_lock.rs` | `compare_exchange_weak`, acquire/release, RAII guard |
| Counting semaphore | `semaphore.rs` | `Mutex` + `Condvar`, RAII guard, bounded fan-out |
| Bounded blocking queue | `bounded_queue.rs` | MPMC queue, backpressure, `close()` shutdown |
| Lock-free SPSC ring buffer | `ring_buffer.rs` | Atomic `head`/`tail`, release/acquire publication |
| Sharded concurrent cache | `sharded_cache.rs` | Per-shard locks to reduce contention |
| Retry with jittered backoff | `retry.rs` | Exponential backoff, full jitter, `Retry-After` floor |
| Consistent hashing ring | `consistent_hash.rs` | Virtual nodes, minimal remapping on membership change |
| Bump/arena allocator | `bump_allocator.rs` | Alignment, O(1) allocation, batch reset |
| HTTP/1.1 request parser | `http_request.rs` | `Content-Length` vs chunked, smuggling checks, `Host` |
| Minimal async runtime | `async_mini.rs` | `Future`, `Waker`, `Pin`, `block_on`, task queue |

### Standalone runnable programs

Standalone programs with verbose comments, so you can run them directly and
explain them in an interview. The measured structures and the programs that
measure them live in [`benchmarking_examples/`](benchmarking_examples/); captured
output is in [`BENCHMARKS.md`](BENCHMARKS.md), and the written report is
[`benchmarking-report.pdf`](benchmarking_examples/benchmarking-report.pdf).

| Problem | File | Run | Core technique |
|---|---|---|---|
| Benchmark (cache + lists) | `benchmarking_examples/benchmark.rs` | `cargo run --release --bin benchmark` | One main over `cache::*` and `lists::*`, best of 3, warmed allocator |
| Paging | `src/bin/os_paging.rs` | `cargo run --bin os_paging` | Page/offset split, fault classification |
| Round-robin scheduler | `src/bin/os_scheduler.rs` | `cargo run --bin os_scheduler` | Time slices, fair scheduling |
| Deadlock detection | `src/bin/concurrency_deadlock.rs` | `cargo run --bin concurrency_deadlock` | Wait-for graph cycle detection |
| Amdahl's law | `src/bin/concurrency_amdahl.rs` | `cargo run --bin concurrency_amdahl` | Serial fraction caps speedup |
| False sharing | `src/bin/concurrency_false_sharing.rs` | `cargo run --bin concurrency_false_sharing` | `#[repr(align(64))]` cache-line padding |
| IPv4 parsing | `src/bin/net_ipv4.rs` | `cargo run --bin net_ipv4` | Dotted quad, private ranges, byte order |
| TCP window math | `src/bin/net_window.rs` | `cargo run --bin net_window` | Effective window, bandwidth-delay product |
| Fibonacci three ways | `src/bin/cs_fib.rs` | `cargo run --bin cs_fib` | Recursion, iteration, memoization |
| Cache locality | `src/bin/cs_locality.rs` | `cargo run --bin cs_locality` | Sequential vs strided access |
| Count Islands | `src/bin/count_islands.rs` | `cargo run --bin count_islands` | Generic BFS connected-component counting |
| Syscall overhead | `src/bin/syscall_overhead.rs` | `cargo run --bin syscall_overhead` | `libc::getpid()`, unsafe FFI, benchmarking |
| Mutex poisoning | `src/bin/mutex_poisoning.rs` | `cargo run --bin mutex_poisoning` | `PoisonError`, recovery with `into_inner()` |
| Shadowing | `src/bin/shadowing.rs` | `cargo run --bin shadowing` | `let` shadowing, type changes, `mut` |
| Singly linked list | `src/bin/singly_linked_list.rs` | `cargo run --bin singly_linked_list` | `enum List<T>` + `type Link<T> = Box<List<T>>`, O(1) push/pop |
| List demos | `benchmarking_examples/list_box.rs`, `list_enum.rs`, `list_drop.rs` | `cargo run --bin list_box` | Thin demos; the four variants live in `benchmarking_examples/lists/` |
| Doubly linked list | `src/bin/ll.rs` | `cargo run --bin ll` | `Rc<RefCell>`, `Weak`, interior mutability |
| Binary search tree | `src/bin/bst_clean.rs` | `cargo run --bin bst_clean` | `enum BST<T>`, ordering invariant, three delete shapes |
| Arena LRU cache | `src/bin/lru_cache_arena.rs` | `cargo run --bin lru_cache_arena` | `Vec` arena with index links, the design the benchmark measures |
| TCP echo server | `src/bin/tcp_echo_server.rs` | `cargo run --bin tcp_echo_server` | Thread-per-connection, `TCP_NODELAY`, half-close |
| HTTP server | `src/bin/http_server.rs` | `cargo run --bin http_server` | REST routes, keep-alive loop, status codes |
| epoll echo server | `src/bin/epoll_echo.rs` | `cargo run --bin epoll_echo` | Non-blocking I/O, `EPOLLOUT` backpressure, `EINTR` |
| Async runtime demo | `src/bin/async_demo.rs` | `cargo run --bin async_demo` | Drives `block_on` and the mini executor |

## Run

```bash
cargo test          # runs library tests and every binary's unit tests
cargo run --release --bin benchmark                 # cache, then all four lists
cargo run --release --bin benchmark cache           # arena vs Rc<RefCell> list
cargo run --release --bin benchmark list            # recursive drop vs iterative
cargo run --bin list_box                            # Option<Box<Node<T>>>
cargo run --bin list_enum                           # enum ListNode<T>
cargo run --release --bin list_drop                 # 5M nodes, iterative drop
cargo run --bin os_paging
cargo run --bin os_scheduler
cargo run --bin concurrency_deadlock
cargo run --bin concurrency_amdahl
cargo run --bin concurrency_false_sharing
cargo run --bin net_ipv4
cargo run --bin net_window
cargo run --bin cs_fib
cargo run --bin cs_locality
cargo run --bin count_islands
cargo run --bin syscall_overhead
cargo run --bin mutex_poisoning
cargo run --bin shadowing
cargo run --bin singly_linked_list
cargo run --bin ll
cargo run --bin bst_clean
cargo run --bin lru_cache_arena
cargo run --bin async_demo        # hand-written async runtime
cargo run --bin http_server       # binds 127.0.0.1:8080
cargo run --bin tcp_echo_server   # binds 127.0.0.1:0, prints the port
cargo run --bin epoll_echo        # binds 127.0.0.1:9000 (Linux only)
```

## Companion study guides

| Guide | What it covers |
|---|---|
| `../docs/11-rust-guide-part1-collections-adt-smart-pointers.md` | All standard collections, API guidelines, ADTs/pattern matching, smart pointers |
| `../docs/12-rust-guide-part2-errors-concurrency-sdk.md` | Error handling, async/concurrency, CLI/SDK, Docker/Kubernetes/CI design |
| `../docs/13-rust-guide-part3-gotchas-linkedlist-interview.md` | Rust gotchas, full doubly linked list, phone-screen tactics |
| `../docs/14-concurrency-async-networking.md` | Synchronisation primitives, backpressure, lock-free ordering, `Future`/`Waker`/`Pin`, epoll, TCP lifecycle, HTTP/1.1 framing, retries, consistent hashing |

## Idiomatic Rust patterns intentionally used

### No nested `if` soup — use flat guards and `match`

```rust
match merged.last_mut() {
    Some(previous) if start <= previous.1 => previous.1 = previous.1.max(end),
    _ => merged.push((start, end)),
}
```

### State machines as `enum`

```rust
match (current, next) {
    (WorkloadState::Pending, WorkloadState::Provisioning) => Ok(()),
    (WorkloadState::Running, WorkloadState::Running) =>
        Err("cannot transition from Running to Running".into()),
    _ => Err(...),
}
```

Invalid states are unrepresentable; `match` forces you to handle all arms.

### `Option` and `Result` instead of sentinel values

```rust
pub fn two_sum(nums: &[i32], target: i32) -> Option<(usize, usize)>
pub fn parse_gpu_count(raw: &str) -> Result<u32, ApiError>
```

## How to talk about it in an interview

- **Complexity**: state time/space for each problem before coding.
- **Rust ownership**: explain why tree/list recursion is clean with `Box` + `Option`.
- **Error handling**: `Result` for fallible ops, `Option` for absence.
- **Cloud tie-in**: LRU for token/response caches, token bucket for API quotas,
  trie for CLI autocomplete, topological sort for job dependency graphs.
- **Clean code**: prefer early returns, guards, `match`, and small pure functions
  over nested branches.
