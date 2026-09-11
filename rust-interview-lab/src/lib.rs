//! Rust coding lab for NVIDIA Cloud / SDK / CLI interviews.
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

pub use problems::adt_idioms::{Command, GpuCount};
pub use problems::async_mini::{MiniExecutor, block_on};
pub use problems::backtracking::subsets;
pub use problems::binary_search::search_rotated;
pub use problems::binary_tree::Tree;
pub use problems::bounded_queue::BoundedQueue;
pub use problems::bump_allocator::BumpArena;
pub use problems::consistent_hash::ConsistentHash;
pub use problems::dp::coin_change;
pub use problems::graph_topology::topological_sort;
pub use problems::http_request::{Method, Request, parse_request};
pub use problems::linked_list::{ListNode, reverse_list};
pub use problems::lru_cache::LruCache;
pub use problems::merge_intervals::merge_intervals;
pub use problems::min_stack::MinStack;
pub use problems::rate_limiter::TokenBucket;
pub use problems::retry::{RetryPolicy, Retryable, retry};
pub use problems::ring_buffer::SpscRing;
pub use problems::semaphore::Semaphore;
pub use problems::sharded_cache::ShardedCache;
pub use problems::sliding_window::length_of_longest_substring;
pub use problems::smart_pointers::TreeNode;
pub use problems::spin_lock::SpinLock;
pub use problems::state_machine::{ApiError, WorkloadState, parse_gpu_count};
pub use problems::threads::{AtomicCounter, parallel_sum};
pub use problems::top_k_frequent::top_k_frequent;
pub use problems::trie::Trie;
pub use problems::two_sum::two_sum;
pub use problems::valid_parentheses::is_valid;
pub use problems::worker_pool::map_order;
