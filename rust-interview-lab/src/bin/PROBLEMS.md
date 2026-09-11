# Problem index

Every problem in this lab, bucketed for revision, with the gaps marked.

`have` = code exists and runs. `partial` = the idea is covered somewhere but there is
no standalone problem. `gap` = nothing yet.

Drill rule: write a minimal correct version in 30-45 min, then explain the failure
modes and how you would test it. If you cannot do it without the file, it is not ready.

---

## A. SDK client mechanics — the JD's first bullet

| Problem | Where | Status |
|---|---|---|
| Retry with exponential backoff and cap | `problems/retry.rs` | have |
| Full jitter, so clients do not retry in lockstep | `problems/retry.rs` | have |
| `Retry-After` as a floor | `problems/retry.rs` | have |
| Typed error taxonomy with `is_retryable()` | `problems/state_machine.rs`, `problems/adt_idioms.rs` | have |
| Client-side rate limiting (token bucket) | `problems/rate_limiter.rs` | have |
| Batching / parallel requests | `problems/worker_pool.rs` | partial |
| Pagination as a lazy iterator | — | gap |
| Idempotency keys, client key + server replay | — | gap |
| Connection pool, keep-alive reuse | — | gap |
| Long-running operation polling, `202` + `Location` | — | gap |
| Cloneable thread-safe client (`Arc<Inner>`) | — | gap |
| Request timeout and cancellation across the call tree | — | gap |
| Token refresh / credential chain | — | gap |
| CLI arg parsing, config precedence (flag > env > file > default) | — | gap |
| CLI output modes (`-o json`), exit codes, stdout vs stderr | — | gap |

## B. REST and HTTP

| Problem | Where | Status |
|---|---|---|
| HTTP/1.1 request parsing, `Content-Length` vs chunked | `problems/http_request.rs` | have |
| Request smuggling checks | `problems/http_request.rs` | have |
| Server with keep-alive and routing | `src/bin/http_server.rs` | have |
| Status code semantics, 404 vs 405 | `src/bin/http_server.rs` | have |
| HTTP client over raw TCP | — | gap |
| Streaming responses (chunked read, SSE) | — | partial |
| Conditional requests and caching (`ETag`, `If-None-Match`) | — | gap |
| HTTP/2, HTTP/3, QUIC | — | gap |
| gRPC and protobuf | — | gap |

## C. Concurrency and synchronisation

| Problem | Where | Status |
|---|---|---|
| Scoped threads, `Send`/`Sync` bounds | `problems/threads.rs` | have |
| Atomic orderings as a contract | `problems/threads.rs` | have |
| Spin lock from `compare_exchange` | `problems/spin_lock.rs` | have |
| Counting semaphore (`Mutex` + `Condvar`) | `problems/semaphore.rs` | have |
| Bounded MPMC queue with `close()` waking waiters | `problems/bounded_queue.rs` | have |
| Lock-free SPSC ring | `problems/ring_buffer.rs` | have |
| Sharded cache | `problems/sharded_cache.rs` | have |
| Worker pool, results collected by index | `problems/worker_pool.rs` | have |
| Deadlock, then the fix | `src/bin/concurrency_deadlock.rs` | have |
| False sharing | `src/bin/concurrency_false_sharing.rs` | have |
| Amdahl's law | `src/bin/concurrency_amdahl.rs` | have |
| Mutex poisoning | `src/bin/mutex_poisoning.rs` | have |
| Bounded buffer | `src/bin/bounded_buffer.rs` | have |
| `RwLock` vs `Mutex` | — | gap |
| Lock-free MPMC (Vyukov-style) | — | partial |

## D. Async and executors

| Problem | Where | Status |
|---|---|---|
| `Future`, `Waker`, `Pin`, `block_on` | `problems/async_mini.rs` | have |
| Executor demo | `src/bin/async_demo.rs` | have |
| Async retry, timeout, cancellation | — | gap |
| Tokio worker pool alongside the thread one | — | gap |

## E. Operating systems and Linux

| Problem | Where | Status |
|---|---|---|
| Page faults and paging | `src/bin/os_paging.rs` | have |
| Scheduler and context switches | `src/bin/os_scheduler.rs` | have |
| Syscall cost, `getpid` loop | `src/bin/syscall_overhead.rs` | have |
| fork, copy-on-write, `/proc` | `docs/02` | have |
| File I/O: read, write, append, line by line | `src/bin/read_write_file.rs`, `readfile_line_by_line.rs`, `append_to_file_open_options.rs` | have |
| Paths, directory listing, recursive walk | `src/bin/path_buff.rs`, `list_directory.rs`, `recusrive_directory_walk.rs` | have |
| File copy, rename, delete, error handling | `src/bin/copy_rename_delete_file.rs`, `file_error_handling.rs` | have |
| Bump / arena allocator | `problems/bump_allocator.rs` | have |
| fd table, `dup2`, pipes, `FD_CLOEXEC` | — | gap |
| fd leak detection via `/proc/self/fd` | — | gap |
| `timerfd`, `signalfd`, `eventfd`, signals | — | gap |
| Free-list / size-class allocator | — | gap |
| `mmap` and zero-copy | — | gap |
| cgroups v2 and namespaces | `docs/02` | partial |
| Cache locality, AoS vs SoA | `src/bin/cs_locality.rs` | partial |

## F. Networking and sockets

| Problem | Where | Status |
|---|---|---|
| TCP echo server, thread per connection | `src/bin/tcp_echo_server.rs` | have |
| Readiness-based I/O with `epoll` | `src/bin/epoll_echo.rs` | have |
| Edge-triggered, non-blocking, drain to `EAGAIN` | `src/bin/epoll_echo.rs` | partial |
| IPv4 addressing and subnets | `src/bin/net_ipv4.rs` | have |
| TCP window and bandwidth-delay product | `src/bin/net_window.rs` | have |
| Server-side keep-alive | `src/bin/http_server.rs` | partial |
| DNS resolution and caching | — | gap |
| TLS, certificate verification, mTLS | — | gap |
| Proxy handling and `NO_PROXY` | — | gap |
| UDP | — | gap |

## G. Data structures and algorithms

| Problem | Where | Status |
|---|---|---|
| Two sum, valid parentheses, min stack | `problems/two_sum.rs`, `valid_parentheses.rs`, `min_stack.rs` | have |
| Sliding window, merge intervals, top k frequent | `problems/sliding_window.rs`, `merge_intervals.rs`, `top_k_frequent.rs` | have |
| Binary tree, BST, binary search | `problems/binary_tree.rs`, `src/bin/bst_clean.rs`, `problems/binary_search.rs` | have |
| Trie | `problems/trie.rs` | have |
| Topological sort (Kahn) | `problems/graph_topology.rs` | have |
| Coin change | `problems/dp.rs` | have |
| Subsets / backtracking | `problems/backtracking.rs` | have |
| Reverse linked list, singly linked list | `problems/linked_list.rs`, `src/bin/singly_linked_list.rs` | have |
| LRU cache, array-backed LRU | `problems/lru_cache.rs`, `src/bin/lru_cache_arena.rs` | have |
| Counting islands | `src/bin/count_islands.rs` | have |
| Smart pointers, `Weak`, `Cow` | `problems/smart_pointers.rs` | have |
| ADT idioms: newtype, enum, typed errors | `problems/adt_idioms.rs` | have |
| Shadowing, no-panic, fib, locality | `src/bin/shadowing.rs`, `dont_panic.rs`, `cs_fib.rs`, `ll.rs` | have |
| Dijkstra, Bellman-Ford | — | gap |
| Union-find | — | gap |
| Running median (two heaps) | — | gap |
| Insert interval, meeting rooms | — | gap |

## H. Kubernetes and controllers

| Problem | Where | Status |
|---|---|---|
| CRD types, generated deepcopy | `operator/api/v1/` | have |
| Reconciler with `CreateOrUpdate` and owner refs | `operator/internal/controller/` | have |
| Status conditions and phase | `operator/internal/controller/` | have |
| Watch and queue via `For` / `Owns` | `operator/cmd/main.go` | have |
| controller-gen manifests, CI drift check | `operator/Makefile`, `.github/workflows/ci.yaml` | have |
| Unit tests with the fake client | `gpuworkload_controller_test.go` | have |
| Kind end-to-end verification | `scripts/verify-kind.sh` | have |
| envtest suite | — | gap |
| Finalizers for owned objects | — | gap |
| Idempotent reconcile, change predicate on generation | — | gap |
| Server-side apply | — | gap |
| Admission webhook validating `gpuCount` | — | gap |
| Helm chart and kustomize overlays | — | gap |
| Device plugin advertising `nvidia.com/gpu` | `docs/03`, `docs/10` | partial |
| MIG, DCGM, GPU Operator, Triton | `docs/06`, `docs/10` | partial |

## I. Performance and measurement

| Problem | Where | Status |
|---|---|---|
| Benchmark harness: warm-up, best of three, control variant | `benchmarking_examples/benchmark.rs` | have |
| Arena vs `Rc<RefCell>` LRU | `benchmarking_examples/cache/` | have |
| Four linked-list storage and drop variants | `benchmarking_examples/lists/` | have |
| Recursive drop stack limit | `benchmarking_examples/list_drop.rs`, `BENCHMARKS.md` | have |
| `criterion` benchmarks tracked in CI | — | gap |
| `perf`, flamegraph, pprof | `docs/02` | partial |

## J. Reliability and distributed patterns

| Problem | Where | Status |
|---|---|---|
| Retry, backoff, jitter | `problems/retry.rs` | have |
| Consistent hashing with virtual nodes | `problems/consistent_hash.rs` | have |
| Token bucket rate limiting | `problems/rate_limiter.rs` | have |
| Workload state machine | `problems/state_machine.rs` | have |
| Health and readiness probes, graceful shutdown | `operator/cmd/main.go` | partial |
| Circuit breaker, bulkhead, timeout budget | — | gap |
| Distributed rate limit (Redis / GCRA) | — | gap |
| Outbox pattern for reliable publishing | — | gap |

## K. Cross-platform, codegen, distribution

| Problem | Where | Status |
|---|---|---|
| Codegen of CRD and deepcopy (controller-gen) | `operator/` | have |
| OpenAPI or protobuf to client codegen | — | gap |
| Windows/macOS paths, line endings, signals | — | gap |
| Config directories across platforms | — | gap |
| Packaging, signed binaries, release automation | — | gap |

## L. Design and behavioural

| Problem | Where |
|---|---|
| GPU cloud system design | `docs/06-system-design-cloud-gpu.md` |
| SDK, CLI, REST, concurrency | `docs/07-cli-sdk-rest-concurrency.md` |
| Testing, CI/CD, observability | `docs/08-testing-cicd-observability.md` |
| Behavioural and STAR stories | `docs/09-behavioral-interview.md` |
| GPU Operator and kubebuilder deep dive | `docs/10-gpu-operator-kubebuilder-deep-dive.md` |
| Linux deep dive | `docs/02-linux-concepts.md` |
| Kubernetes deep dive | `docs/03-kubernetes-concepts.md` |

---

## Gaps, in the order worth closing

Nothing here is large. Each is one file.

1. **Idempotency keys** — client key plus server replay store, showing the duplicate that a naive retry creates.
2. **Long-running operation polling** — `202` + `Location`, backoff, deadline, terminal failure.
3. **Pagination iterator** — cursor is opaque, lazy, stops on the absent token not an empty page.
4. **Connection pool** — bounded pool, RAII return of the connection, reuse across threads.
5. **Thread-safe client** — `Clone` + `Arc<Inner>`, and a test that asserts `Send + Sync`.
6. **Retry as a client** — the existing `retry` policy wired to a real call, not just the delay math.
7. **Reconcile idempotency** — fix the `LastTransitionTime` loop in `operator/` and explain the predicate that prevents it.
8. **OpenAPI → client codegen** — the JD lists code generation as a standout, and only controller-gen is represented.

## Coverage of the buckets against the JD

| JD line | Buckets | Readiness |
|---|---|---|
| Design, build, implement SDKs and CLIs | A, K | weak: patterns exist, no client and no CLI |
| Python, Go, or Rust | G, C | strong in Rust, weaker in Go (one operator), nothing in Python |
| Python client on Windows, Linux, macOS | K, A | gap |
| RESTful web services | B | strong server side, thin client side |
| CI/CD | H, I | have, minimal |
| Containers, Kubernetes | H | strong |
| Cloud platforms | J, H | partial |
| Code generation | K | partial |
| Open source, complex delivery | L | stories only |
