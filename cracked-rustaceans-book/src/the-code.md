# The Code {#the-code}

## Layout

The repository holds one Cargo package, `rust-interview-lab`. Three directories in it
hold everything the chapters read.

```text
rust-interview-lab/
├── Cargo.toml
├── README.md
├── BENCHMARKS.md
├── src
│   ├── lib.rs                the crate root and its re-exports
│   ├── problems/             the library modules, one problem to a file
│   └── bin/                  the programs, each its own crate with a `main`
└── benchmarking_examples/    the measured structures and the benchmark
```

A module under `src/problems/` holds one problem, one type, or one pair of a type and
its policy, and ends with a `#[cfg(test)] mod tests`, so the list printed by
`cargo test` reads as an index of this book. A file under `src/bin/` is a separate
crate that links the library and has a `main` that runs without arguments; most of
them carry their own tests as well, so `cargo test` exercises the programs too.

The files under `benchmarking_examples/` are declared as library modules by `src/lib.rs`
rather than included by each program, so the shared code is compiled once and an unused
variant is not reported as dead code in the programs that do not measure it.

The package also contains files that no chapter reads. They are working notes rather
than finished material, and they are left out of the table below.

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

## Every file and the chapter that reads it

The table is the whole of the correspondence between the repository and the book. A
chapter cites its files again at the head of the chapter and in its listing
references, and a file read by more than one chapter is listed once with each
chapter that reads it.

| File | Chapter |
|---|---|
| `src/bin/append_to_file_open_options.rs` | 26 |
| `src/bin/async_demo.rs` | 56 |
| `src/bin/bounded_buffer.rs` | 30 |
| `src/bin/bst_clean.rs` | 8 |
| `src/bin/command_line_args.rs` | 29 |
| `src/bin/concurrency_amdahl.rs` | 49 |
| `src/bin/concurrency_deadlock.rs` | 49 |
| `src/bin/concurrency_false_sharing.rs` | 48 |
| `src/bin/copy_rename_delete_file.rs` | 28 |
| `src/bin/count_islands.rs` | 23 |
| `src/bin/cs_fib.rs` | 37 |
| `src/bin/cs_locality.rs` | 48 |
| `src/bin/dependency_resolutiom.rs` | 65 |
| `src/bin/epoll_echo.rs` | 53 |
| `src/bin/false_sharing.rs` | 48 |
| `src/bin/file_error_handling.rs` | 28 |
| `src/bin/fun_network_call.rs` | 58 |
| `src/bin/http_server.rs` | 55 |
| `src/bin/idempotent_operation.rs` | 34 |
| `src/bin/idempotent_operation_with_error_progagation.rs` | 34 |
| `src/bin/list_directory.rs` | 27 |
| `src/bin/ll.rs` | 16 |
| `src/bin/lru_cache_arena.rs` | 40 |
| `src/bin/median_finder.rs` | 32 |
| `src/bin/merge_k_sorted_lists_divide.rs` | 62 |
| `src/bin/mutex_poisoning.rs` | 22 |
| `src/bin/net_ipv4.rs` | 51 |
| `src/bin/net_window.rs` | 51 |
| `src/bin/os_paging.rs` | 50 |
| `src/bin/os_scheduler.rs` | 50 |
| `src/bin/parallel_sum.rs` | 31 |
| `src/bin/path_buff.rs` | 27 |
| `src/bin/read_write_file.rs` | 26 |
| `src/bin/readfile_line_by_line.rs` | 26 |
| `src/bin/recusrive_directory_walk.rs` | 27 |
| `src/bin/reqwest_and_tokio.rs` | 58 |
| `src/bin/reverse_string.rs` | 33 |
| `src/bin/shadowing.rs` | 25 |
| `src/bin/singly_linked_list.rs` | 15 |
| `src/bin/syscall_overhead.rs` | 24 |
| `src/bin/tcp_echo_server.rs` | 52 |
| `src/bin/thread_pool.rs` | 64 |
| `src/problems/adt_idioms.rs` | 35 |
| `src/problems/async_mini.rs` | 56 |
| `src/problems/backtracking.rs` | 13 |
| `src/problems/binary_search.rs` | 9 |
| `src/problems/binary_tree.rs` | 7 |
| `src/problems/bounded_queue.rs` | 46 |
| `src/problems/bump_allocator.rs` | 39 |
| `src/problems/consistent_hash.rs` | 42 |
| `src/problems/dp.rs` | 12 |
| `src/problems/drills.rs` | 59 |
| `src/problems/graph_bfs.rs` | 60 |
| `src/problems/graph_dfs.rs` | 60 |
| `src/problems/graph_dijkstra.rs` | 61 |
| `src/problems/graph_topology.rs` | 11 |
| `src/problems/http_request.rs` | 54 |
| `src/problems/linked_list.rs` | 14 |
| `src/problems/lru_cache.rs` | 17 |
| `src/problems/lru_cache_easy.rs` | 18 |
| `src/problems/merge_intervals.rs` | 5 |
| `src/problems/min_stack.rs` | 3 |
| `src/problems/rate_limiter.rs` | 20 |
| `src/problems/retry.rs` | 57 |
| `src/problems/ring_buffer.rs` | 47 |
| `src/problems/semaphore.rs` | 45 |
| `src/problems/sharded_cache.rs` | 41 |
| `src/problems/sliding_window.rs` | 4 |
| `src/problems/smart_pointers.rs` | 36 |
| `src/problems/spin_lock.rs` | 44 |
| `src/problems/state_machine.rs` | 19 |
| `src/problems/thread_pool_v2.rs` | 64 |
| `src/problems/thread_pool_v3.rs` | 64 |
| `src/problems/thread_pool_v4.rs` | 64 |
| `src/problems/threads.rs` | 43 |
| `src/problems/three_sum.rs` | 63 |
| `src/problems/top_k_frequent.rs` | 6 |
| `src/problems/trie.rs` | 10 |
| `src/problems/two_sum.rs` | 1 |
| `src/problems/valid_parentheses.rs` | 2 |
| `src/problems/worker_pool.rs` | 21 |
| `benchmarking_examples/benchmark.rs` | 38, 40 |
| `benchmarking_examples/cache/mod.rs` | 40 |
| `benchmarking_examples/cache/rc_list.rs` | 40 |
| `benchmarking_examples/list_box.rs` | 38 |
| `benchmarking_examples/list_drop.rs` | 38 |
| `benchmarking_examples/list_enum.rs` | 38 |
| `benchmarking_examples/lists/boxed.rs` | 38 |
| `benchmarking_examples/lists/boxed_drop.rs` | 38 |
| `benchmarking_examples/lists/enum_drop.rs` | 38 |
| `benchmarking_examples/lists/enum_node.rs` | 38 |
| `benchmarking_examples/lists/mod.rs` | 38 |

