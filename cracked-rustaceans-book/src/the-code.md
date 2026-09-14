# The Code {#the-code}

## Layout

The repository holds one Cargo package. The tree below lists the files this book
reads; the package also contains concurrency, asynchronous, networking and
benchmarking code that lies outside the scope of these chapters.

```text
rust-interview-lab/
├── Cargo.toml
├── README.md
├── BENCHMARKS.md
├── src
│   ├── lib.rs                       the crate root and its re-exports
│   ├── problems
│   │   ├── mod.rs                   the module list
│   │   ├── backtracking.rs          Chapter 13
│   │   ├── binary_search.rs         Chapter 9
│   │   ├── binary_tree.rs           Chapter 7
│   │   ├── dp.rs                    Chapter 12
│   │   ├── graph_topology.rs        Chapter 11
│   │   ├── linked_list.rs           Chapter 14
│   │   ├── lru_cache.rs             Chapter 17
│   │   ├── merge_intervals.rs       Chapter 5
│   │   ├── min_stack.rs             Chapter 3
│   │   ├── rate_limiter.rs          Chapter 20
│   │   ├── sliding_window.rs        Chapter 4
│   │   ├── state_machine.rs         Chapter 19
│   │   ├── top_k_frequent.rs        Chapter 6
│   │   ├── trie.rs                  Chapter 10
│   │   ├── two_sum.rs               Chapter 1
│   │   ├── valid_parentheses.rs     Chapter 2
│   │   └── worker_pool.rs           Chapter 21
│   └── bin
│       ├── append_to_file_open_options.rs   Chapter 26
│       ├── bounded_buffer.rs                Chapter 30
│       ├── bst_clean.rs                     Chapter 8
│       ├── command_line_args.rs             Chapter 29
│       ├── copy_rename_delete_file.rs       Chapter 28
│       ├── count_islands.rs                 Chapter 23
│       ├── file_error_handling.rs           Chapter 28
│       ├── idempotent_operation.rs          Chapter 34
│       ├── idempotent_operation_with_error_progagation.rs   Chapter 34
│       ├── list_directory.rs                Chapter 27
│       ├── ll.rs                            Chapter 16
│       ├── median_finder.rs                 Chapter 32
│       ├── mutex_poisoning.rs               Chapter 22
│       ├── parallel_sum.rs                  Chapter 31
│       ├── path_buff.rs                     Chapter 27
│       ├── read_write_file.rs               Chapter 26
│       ├── readfile_line_by_line.rs         Chapter 26
│       ├── recusrive_directory_walk.rs      Chapter 27
│       ├── reverse_string.rs                Chapter 33
│       ├── shadowing.rs                     Chapter 25
│       ├── singly_linked_list.rs            Chapter 15
│       └── syscall_overhead.rs              Chapter 24
└── benchmarking_examples/           the measured structures and the benchmark
```

One file in `src/problems/` is empty, `hash_map.rs`, and nothing in the crate refers to
it. Chapter 18 reads `lru_cache_easy.rs`, the array-backed cache that keeps its entries
in a `Vec` and links them by index.

## Modules and programs

Seventeen of the files above are library modules. Each holds one problem, one type,
or one pair of a type and its policy, and each ends with a `#[cfg(test)] mod tests`,
so the list printed by `cargo test` reads as an index of this book.

Twenty-two are programs. Files under `src/bin/` are separate crates that link the
library, and each has a `main` function that runs without arguments. Most of them
also carry the tests for the code they contain, so `cargo test` exercises the
programs as well as the library.

## What the files have in common

Four conventions run through the code. They are stated once here so that the
chapters need not repeat them.

**Enumerations instead of flags.** Where a value has a fixed set of states, the
code uses an `enum` and a `match` with no fall-through arm, so that adding a state
is a compile error at every place that must handle it. `WorkloadState` in Chapter
19 and `ApiError` beside it are examples.

**`Option` and `Result` instead of sentinels.** Absence is `Option` and failure is
`Result`, so the type states which. Chapter 12 keeps a sentinel inside the dynamic
program's table and translates it at the boundary, so a caller never sees it.

**Ownership written out.** The linked structures in Chapters 14 to 16 give three
different answers to the question of who owns the next node, namely `Box`, `Rc`
with `Weak`, and a vector of indices, and each answer is visible in the type rather
than in a comment.

**Tests beside the code.** A unit test that reaches a private item is a licence to
change that item. Each module keeps its own tests in a `#[cfg(test)] mod tests`, so
the list printed by `cargo test` reads as an index of the book.

## Files read by chapters 35 to 59

| File | Chapter |
|---|---|
| `src/problems/adt_idioms.rs` | 35 |
| `src/problems/smart_pointers.rs` | 36 |
| `src/bin/cs_fib.rs` | 37 |
| `benchmarking_examples/lists/`, `list_box.rs`, `list_enum.rs`, `list_drop.rs`, `benchmark.rs` | 38 |
| `src/problems/bump_allocator.rs` | 39 |
| `benchmarking_examples/cache/`, `benchmark.rs` | 40 |
| `src/problems/sharded_cache.rs` | 41 |
| `src/problems/consistent_hash.rs` | 42 |
| `src/problems/threads.rs` | 43 |
| `src/problems/spin_lock.rs` | 44 |
| `src/problems/semaphore.rs` | 45 |
| `src/problems/bounded_queue.rs` | 46 |
| `src/problems/ring_buffer.rs` | 47 |
| `src/bin/cs_locality.rs`, `src/bin/concurrency_false_sharing.rs` | 48 |
| `src/bin/concurrency_amdahl.rs`, `src/bin/concurrency_deadlock.rs` | 49 |
| `src/bin/os_paging.rs`, `src/bin/os_scheduler.rs` | 50 |
| `src/bin/net_ipv4.rs`, `src/bin/net_window.rs` | 51 |
| `src/bin/tcp_echo_server.rs` | 52 |
| `src/bin/epoll_echo.rs` | 53 |
| `src/problems/http_request.rs` | 54 |
| `src/bin/http_server.rs` | 55 |
| `src/problems/async_mini.rs`, `src/bin/async_demo.rs` | 56 |
| `src/problems/retry.rs` | 57 |
| `src/bin/fun_network_call.rs`, `src/bin/reqwest_and_tokio.rs` | 58 |
| `src/problems/drills.rs` | 59 |
| `src/bin/lru_cache_arena.rs` | 40 |
| `src/problems/graph_bfs.rs`, `src/problems/graph_dfs.rs` | 60 |
| `src/problems/graph_dijkstra.rs` | 61 |
| `src/bin/merge_k_sorted_lists_divide.rs` | 62 |
| `src/problems/three_sum.rs` | 63 |
| `src/bin/false_sharing.rs` | 48 |
