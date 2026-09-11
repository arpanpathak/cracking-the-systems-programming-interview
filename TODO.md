# TODO

## Rust lab

- [ ] Add an arena-backed doubly linked list next to the `Rc<RefCell>` version
- [ ] Add a running-median finder (two heaps)
- [ ] Add Dijkstra and Bellman-Ford beside the topological sort
- [ ] Add union-find and re-solve Counting Islands with it
- [ ] Add insert-interval and meeting-rooms to `merge_intervals.rs`
- [ ] Resolve `lru_cache_easy.rs` and the empty `hash_map.rs`
- [ ] Add property tests with `proptest`
- [ ] Add doc examples for every public item
- [ ] Add `criterion` benchmarks, tracking regressions in CI

## Concurrency and systems

- [x] Add thread basics, scoped threads, and `Send`/`Sync` notes (`threads.rs`)
- [x] Add a spin lock built from an atomic (`spin_lock.rs`)
- [x] Add a smart-pointer reference with `Weak` and `Cow` (`smart_pointers.rs`)
- [x] Add interview-ready ADT idioms: newtype, enum, typed errors (`adt_idioms.rs`)
- [x] Add lean drill answers sized for a live round (`drills.rs`)
- [ ] Add a Tokio worker pool alongside the thread-based one
- [x] Add backpressure and shutdown to a queue (`bounded_queue.rs`)
- [x] Add a counting semaphore (`semaphore.rs`)
- [ ] Add an `RwLock` example
- [x] Add a sharded concurrent cache (`sharded_cache.rs`); contention measurement still open
- [x] Add retry with jittered backoff over `ApiError::is_retryable()` (`retry.rs`)
- [x] Add a program on `epoll` (`src/bin/epoll_echo.rs`); `io_uring` notes still open
- [x] Add a lock-free SPSC ring buffer (`ring_buffer.rs`)
- [x] Add a minimal async runtime (`async_mini.rs`): `Future`, `Waker`, `block_on`
- [x] Add an HTTP/1.1 parser (`http_request.rs`) and a REST server (`src/bin/http_server.rs`)
- [x] Add a TCP echo server (`src/bin/tcp_echo_server.rs`)
- [x] Add consistent hashing (`consistent_hash.rs`)
- [x] Add a bump/arena allocator (`bump_allocator.rs`)

## Book

- [ ] Move the full outline from `SUMMARY-drafts.md` into `SUMMARY.md`
- [ ] Add `01-what-an-abstraction-costs.md` to the table of contents
- [ ] Fix the chapter cross-references that assume the old numbering
- [ ] Run every fenced `rust` listing through `cargo check` in CI
- [ ] Replace the ASCII diagrams with SVG

## Operator

- [ ] Add status conditions with `observedGeneration`
- [ ] Add finalizers for owned `Deployment` / `Service` cleanup
- [ ] Add an admission webhook for `gpuCount` and runtime class
- [ ] Switch owned objects to server-side apply
- [ ] Detect the device plugin before scheduling `gpuCount > 0`
- [ ] Add an `envtest` suite
- [ ] Add a Helm chart and kustomize overlays
- [ ] Expose reconcile metrics and ship a Grafana dashboard

## CI and release

- [ ] Add coverage (`cargo-llvm-cov`, `go test -cover`) with a floor on `main`
- [ ] Add `cargo clippy -- -D warnings` and `cargo fmt --check`
- [ ] Add a Rust matrix: stable, pinned MSRV, `aarch64`
- [ ] Cache toolchains (`Swatinem/rust-cache`, `actions/cache`)
- [ ] Publish the PDF as a release asset on a `book-v*` tag
- [ ] Add Dependabot for Cargo, Go modules, and Actions

## Repository

- [x] Move tests into per-module test modules; removed the monolithic `tests/problems.rs`

- [ ] Add an index for `docs/`
- [ ] Add `rust-toolchain.toml` pinning the stable channel
- [ ] Add `cargo deny` / `cargo audit`
- [ ] Add `typos` and a link checker over `docs/` and the book
- [ ] Add `CONTRIBUTING.md`, issue templates, `CODE_OF_CONDUCT.md`, `SECURITY.md`
- [ ] Delete the stray build artifact `rust-interview-lab/src/bin/benchmark_cache`
- [ ] Decide which PDFs to keep in `cracked-rustaceans-book/build/`
