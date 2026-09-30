//! Rust systems programming lab: data structures, concurrency, networking, and cloud SDK patterns.
//!
//! Contains both:
//!
//! - LeetCode-style DSA problems written in idiomatic Rust
//! - cloud/SDK/CLI concurrency, systems, and networking problems
//! - explicit `enum` / algebraic data type and pattern-matching examples
//!
//! `benchmarking_examples` holds the data-structure implementations and the
//! programs that measure them. Each variant lives in its own module, and
//! `benchmarking_examples/benchmark.rs` contains only the benchmark itself.
//!
//! Run all tests with:
//!
//! ```bash
//! cargo test
//! ```

// The sources live under benchmarking_examples/ so that everything the benchmark
// measures sits in one directory. They are declared here as library modules rather
// than included by each program: a Cargo binary is its own crate, and an unused
// `pub` item in a binary is reported as dead code, so a `mod lists;` in each
// program would make three of the four variants dead in every program that does
// not use them, and would compile the shared code four times.
#[path = "../benchmarking_examples/cache/mod.rs"]
pub mod cache;

#[path = "../benchmarking_examples/lists/mod.rs"]
pub mod lists;
pub mod problems;

pub use problems::{
    adt_idioms::{Command, GpuCount},
    async_mini::{MiniExecutor, block_on},
    backtracking::subsets,
    binary_search::search_rotated,
    binary_tree::Tree,
    bounded_queue::BoundedQueue,
    bump_allocator::BumpArena,
    consistent_hash::ConsistentHash,
    dp::coin_change,
    graph_topology::topological_sort,
    http_request::{Method, Request, parse_request},
    linked_list::{ListNode, reverse_list},
    lru_cache::LruCache,
    merge_intervals::merge_intervals,
    min_stack::MinStack,
    rate_limiter::TokenBucket,
    retry::{RetryPolicy, Retryable, retry},
    ring_buffer::SpscRing,
    semaphore::Semaphore,
    sharded_cache::ShardedCache,
    sliding_window::length_of_longest_substring,
    smart_pointers::TreeNode,
    spin_lock::SpinLock,
    state_machine::{ApiError, WorkloadState, parse_gpu_count},
    threads::{AtomicCounter, parallel_sum},
    top_k_frequent::top_k_frequent,
    trie::Trie,
    two_sum::two_sum,
    valid_parentheses::is_valid,
    worker_pool::map_order,
};
