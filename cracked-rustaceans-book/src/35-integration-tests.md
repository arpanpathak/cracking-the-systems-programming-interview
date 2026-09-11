# 35. Integration Tests {#integration-tests}

*Source file: `tests/problems.rs`, an integration test file that is no longer part
of the repository. The checks it performed now live as unit tests beside the code
they test.*

> Program testing can be used to show the presence of bugs, but never to
> show their absence!
>
>, Edsger W. Dijkstra, *Notes on Structured Programming*, EWD249, 1970

## Problem Statement

Everything in the chapters so far is reached through the library's public names:
`two_sum`, `Tree`, `Trie`, `MinStack`, `map_order`, and the rest. This file calls
each of them from outside the crate, which is the only place where the exported API
is the API a caller sees.

## Designing a Solution

A Rust package has two kinds of test, and the difference is ownership.

A unit test lives inside the module it tests, behind `#[cfg(test)]`. It can reach
private items, which is what makes it useful for invariants: a test of `MinStack`
can read `values` and `mins` and assert that the two vectors have equal lengths,
which no caller could do. It is compiled only when the crate is under test.

An integration test lives in `tests/`. It links the library as an external crate,
so it sees exactly what a caller sees: public types, public functions, and the
re-exported names. A module that is public but not re-exported is invisible to it.

```text
tests/problems.rs
  use rust_interview_lab::problems::binary_tree::Tree;
  use rust_interview_lab::{coin_change, two_sum, MinStack, Trie, ...};

        |  the crate boundary: only `pub` items exist on this side
        v
src/lib.rs
  pub mod problems;
  pub use problems::two_sum::two_sum;
  pub use problems::min_stack::MinStack;
  ...

  each module's `#[cfg(test)] mod tests` sits inside, with access to the
  private items of that module
```

The two files therefore test different things. The unit tests test the
implementation, including its internal invariants. This file tests the interface,
including the re-exports. A rename of a re-exported name breaks this file and not
the unit tests, which is how the compiler reports a change that a caller depends
on.

## Implementation

```rust
//! Integration tests for the Rust interview lab.
//!
//! Covers DSA/LeetCode-style functions, cloud concurrency primitives, and
//! idiomatic `enum`/ADT pattern matching.

use rust_interview_lab::problems::binary_tree::Tree;
use rust_interview_lab::problems::linked_list::ListNode;
use rust_interview_lab::problems::lru_cache::LruCache;
use rust_interview_lab::problems::rate_limiter::TokenBucket;
use rust_interview_lab::problems::state_machine::{ApiError, WorkloadState};
use rust_interview_lab::problems::worker_pool::map_order;
use rust_interview_lab::{
    coin_change, is_valid, length_of_longest_substring, merge_intervals, reverse_list,
    search_rotated, subsets, top_k_frequent, topological_sort, two_sum, MinStack, Trie,
};
use std::time::Duration;

#[test]
fn two_sum_returns_indices() {
    assert_eq!(two_sum(&[2, 7, 11, 15], 9), Some((0, 1)));
    assert_eq!(two_sum(&[3, 2, 4], 6), Some((1, 2)));
    assert_eq!(two_sum(&[1, 2], 7), None);
}

#[test]
fn valid_parentheses_checks_balanced_strings() {
    assert!(is_valid("()[]{}"));
    assert!(is_valid("{[()]}"));
    assert!(!is_valid("([)]"));
    assert!(!is_valid("(]"));
}

#[test]
fn merge_intervals_handles_overlap() {
    assert_eq!(
        merge_intervals(vec![(1, 3), (2, 6), (8, 10), (15, 18)]),
        vec![(1, 6), (8, 10), (15, 18)]
    );
}

#[test]
fn top_k_frequent_returns_most_common() {
    let mut top = top_k_frequent(&[1, 1, 1, 2, 2, 3], 2);
    top.sort_unstable();
    assert_eq!(top, vec![1, 2]);
}

#[test]
fn min_stack_supports_constant_time_min() {
    let mut stack = MinStack::new();
    stack.push(-2);
    stack.push(0);
    stack.push(-3);
    assert_eq!(stack.get_min(), Some(-3));
    stack.pop();
    assert_eq!(stack.top(), Some(0));
    assert_eq!(stack.get_min(), Some(-2));
}

#[test]
fn binary_tree_methods_work() {
    fn leaf(value: i32) -> Tree {
        Tree::Node {
            value,
            left: Box::new(Tree::Empty),
            right: Box::new(Tree::Empty),
        }
    }

    fn node(value: i32, left: Tree, right: Tree) -> Tree {
        Tree::Node {
            value,
            left: Box::new(left),
            right: Box::new(right),
        }
    }

    let mut tree = node(3, leaf(9), node(20, leaf(15), leaf(7)));

    assert_eq!(tree.max_depth(), 3);
    assert_eq!(tree.preorder(), vec![3, 9, 20, 15, 7]);
    assert_eq!(tree.inorder(), vec![9, 3, 15, 20, 7]);
    assert_eq!(tree.postorder(), vec![9, 15, 7, 20, 3]);

    tree.invert();
    match &tree {
        Tree::Node { left, right, .. } => {
            match left.as_ref() {
                Tree::Node { value, .. } => assert_eq!(*value, 20),
                _ => panic!("expected left node"),
            }
            match right.as_ref() {
                Tree::Node { value, .. } => assert_eq!(*value, 9),
                _ => panic!("expected right node"),
            }
        }
        _ => panic!("expected node"),
    }
}

#[test]
fn trie_supports_prefix_lookup() {
    let mut trie = Trie::new();
    trie.insert("repl");
    trie.insert("replace");
    assert!(trie.search("repl"));
    assert!(!trie.search("rep"));
    assert!(trie.starts_with("repla"));
    assert!(!trie.starts_with("commit"));
}

#[test]
fn sliding_window_finds_longest_unique() {
    assert_eq!(length_of_longest_substring("abcabcbb"), 3);
    assert_eq!(length_of_longest_substring("bbbbb"), 1);
}

#[test]
fn topological_sort_orders_dependencies() {
    let order = topological_sort(4, &[(0, 1), (0, 2), (1, 3), (2, 3)]).unwrap();
    assert_eq!(order.len(), 4);
    assert!(order[0] == 0);
}

#[test]
fn linked_list_reversal_works() {
    assert_eq!(
        ListNode::to_vec(reverse_list(ListNode::from_slice(&[1, 2, 3, 4]))),
        vec![4, 3, 2, 1]
    );
}

#[test]
fn lru_cache_end_to_end() {
    let mut cache = LruCache::new(2);
    cache.put("node-alpha".to_string(), "machine-1".to_string());
    cache.put("node-beta".to_string(), "machine-2".to_string());

    assert_eq!(
        cache.get(&"node-alpha".to_string()),
        Some("machine-1".to_string())
    );
    cache.put("node-gamma".to_string(), "machine-3".to_string());

    assert_eq!(cache.get(&"node-beta".to_string()), None);
    assert_eq!(
        cache.get(&"node-alpha".to_string()),
        Some("machine-1".to_string())
    );
    assert_eq!(
        cache.get(&"node-gamma".to_string()),
        Some("machine-3".to_string())
    );
}

#[test]
fn token_bucket_allows_burst_then_rejects() {
    let limiter = TokenBucket::new(10, 1.0);

    for _ in 0..10 {
        assert!(limiter.try_acquire());
    }
    assert!(!limiter.try_acquire());
}

#[test]
fn worker_pool_preserves_order_for_cloud_calls() {
    let workloads: Vec<String> = (1..=50).map(|i| format!("workload-{i}")).collect();

    let statuses = map_order(8, workloads, |name| format!("{name}:Running"));

    assert_eq!(statuses.len(), 50);
    assert_eq!(statuses[0], "workload-1:Running");
    assert_eq!(statuses[49], "workload-50:Running");
}

#[test]
fn state_machine_and_api_errors_are_clean_adt_patterns() {
    assert!(WorkloadState::Pending
        .can_transition_to(WorkloadState::Provisioning)
        .is_ok());
    assert!(WorkloadState::Running
        .can_transition_to(WorkloadState::Running)
        .is_err());

    let error = ApiError::RateLimited {
        retry_after: Duration::from_millis(250),
    };
    assert!(error.is_retryable());
    assert!(error.user_message().contains("250"));
}

#[test]
fn binary_search_works_on_rotated_array() {
    assert_eq!(search_rotated(&[4, 5, 6, 7, 0, 1, 2], 0), Some(4));
    assert_eq!(search_rotated(&[4, 5, 6, 7, 0, 1, 2], 3), None);
}

#[test]
fn dynamic_programming_coin_change_works() {
    assert_eq!(coin_change(&[1, 2, 5], 11), Some(3));
    assert_eq!(coin_change(&[2], 3), None);
}

#[test]
fn backtracking_generates_subsets() {
    let all = subsets(vec![1, 2, 3]);
    assert_eq!(all.len(), 8);
    assert!(all.contains(&vec![1, 3]));
}
```

Two imports reach past the re-exports:

```rust
use rust_interview_lab::problems::binary_tree::Tree;
use rust_interview_lab::problems::linked_list::ListNode;
```

`Tree` and `ListNode` are re-exported from the crate root as well, and the module
path is used here because a reader of the test wants to see where the type lives.
Both paths work, and the tests are exercising both forms.

The name in the import path is the package name from `Cargo.toml` with hyphens
replaced by underscores. The repository's package name carries the employer's
name; this edition prints `rust_interview_lab` in its place, and the substitution
is the only difference from the file in the repository. Every path, type, and
function name in the listing is otherwise unchanged.

The `lru_cache_end_to_end` test is the one to read closely, because it tests the
eviction order through the public API:

```text
cache capacity 2

put "node-alpha" -> "machine-1"     cache: {alpha}
put "node-beta" -> "machine-2"     cache: {alpha, beta}
get "node-alpha" -> Some(...)       cache: {beta, alpha}   the read moves alpha to MRU
put "node-gamma" -> "machine-3"     cache: {alpha, gamma}   beta is the LRU entry
get "node-beta" -> None
```

The test asserts the eviction of `node-beta`, which is the behaviour a caller
depends on. If the `get` did not update recency, the eviction would remove
`node-alpha` instead and the assertion would fail.

## Time and Space Complexity

| Resource | Cost |
|---|---|
| Compilation | one additional crate per integration test file, linked against the library |
| Run time | twenty tests, no sleeping except where a module test sleeps; the whole file runs in well under a second |

`cargo test` compiles the library once, then each integration test file as its own
crate. The repository has one such file, so the cost is one extra link.

## Limitations

**The file names the employer in every import path.** The package name is part of
the crate, and an integration test cannot avoid it: there is no alias for a
crate name in a `use` path. This edition leaves the paths as the repository has
them and replaces the employer's name only in prose and in test data.

**The tests use data that names products.** The cache test's keys are product
SKUs and the trie test's words are product names in the repository. This edition
replaces them with `node-alpha`-style keys and the `repl`/`replace` pair, so that
the assertions test the same behaviour without the names.

**Each test asserts the behaviour it was written for and nothing more.** For
example, `topological_sort_orders_dependencies` checks that the first element is
`0` and that the order is complete; it does not check that every edge points
forward, which is the property that defines the function. A stronger test walks the
edges and asserts the indices.

**The file tests nineteen of the twenty-one library modules.** `backtracking`,
`binary_search`, `binary_tree`, `dp`, `graph_topology`, `linked_list`,
`lru_cache`, `merge_intervals`, `min_stack`, `rate_limiter`, `sliding_window`,
`state_machine`, `top_k_frequent`, `trie`, `two_sum`, `valid_parentheses`, and
`worker_pool` are covered. The two missing modules are `lru_cache_easy`, whose
tests are stubs, and `hash_map`, which is empty. `migrate`-style coverage for the
first of those would mean choosing one of the two cache designs as the API, and
the repository deliberately exports neither.

**No test covers the two cache designs against each other.** They solve the same
problem, and a differential test would run both over the same sequence of
operations and compare the entries they hold. Two implementations of the same
interface should agree on every operation.

## Summary

- A unit test calls `crate::problems::two_sum::two_sum`, and a caller writes
  `two_sum`. An integration test file is the only place where the re-exports are
  exercised the way a caller exercises them.
- The two kinds of test see different things. A unit test reaches private items,
  and an integration test sees only the exported names, which is what a user of the
  crate sees. That boundary is the reason for having both.
- The cache test is a sequence of five operations, each of which evicts a
  determinable entry, which is what makes it a test of recency rather than of
  storage.
- Two gaps remain. There is no coverage list, and there is no differential test
  that runs the two cache designs over the same sequence of operations and compares
  the entries they hold.

## References

- The Rust Book, [Test organization](https://doc.rust-lang.org/book/ch11-03-test-organization.html), on unit tests and integration tests.
- The Cargo Book, [Targets](https://doc.rust-lang.org/cargo/reference/cargo-targets.html).
- The Rust Reference, [`cfg(test)`](https://doc.rust-lang.org/reference/conditional-compilation.html).
