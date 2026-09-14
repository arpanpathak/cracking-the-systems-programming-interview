# 49. Amdahl's Law and Deadlock Detection {#amdahl-and-deadlock}

*Source files: [`src/bin/concurrency_amdahl.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/concurrency_amdahl.rs) and [`src/bin/concurrency_deadlock.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/concurrency_deadlock.rs). Run them with `cargo run --bin concurrency_amdahl` and `cargo run --bin concurrency_deadlock`.*

## Problem Statement

1. Given the fraction `s` of a program's work that must run serially, compute its
   speedup on `p` processors, tabulate it for several values of each, and print the
   limit as `p` grows without bound.
2. Given a list of edges `(waiter, holder)`, each meaning that one task is blocked
   waiting for a resource another task holds, decide whether the tasks are deadlocked.

## Designing a Solution

### Amdahl's law

Normalise the program's running time on one processor to 1. The serial part takes `s`
and the parallel part takes `1 - s`. On `p` processors the parallel part takes
`(1 - s) / p`, and the serial part still takes `s`:

```text
speedup(s, p) = 1 / (s + (1 - s) / p)

as p grows without bound, (1 - s) / p approaches 0, so speedup approaches 1 / s
```

A program that is half serial can never run more than twice as fast, however many
processors it is given.

### Deadlock as a cycle

Draw one vertex per task and one edge from each waiting task to the task holding what it
waits for. If following edges from some task leads back to that task, every task on the
path is waiting for the next, and none can proceed: a deadlock. If the graph has no
cycle, some task at the end of every path is not waiting, and it can finish and release
what it holds.

A depth-first search finds a cycle by colouring vertices:

```text
0  unvisited
1  on the current search path
2  fully explored; no cycle is reachable from it

visiting a vertex marked 1 means the path has returned to itself: a cycle
visiting a vertex marked 2 can be skipped
```

The two non-zero colours must stay distinct. A vertex reached twice through different paths
in an acyclic graph, such as vertex 2 in `0 -> 1 -> 2` and `0 -> 2`, is marked 2 by the
time the second path arrives, and it is not a cycle.

## Implementation

```rust
//! Amdahl's law: the serial fraction of the work caps the speedup from adding
//! processors. A program that is 50 percent serial cannot go faster than 2x, no
//! matter how many cores it gets.
//!
//! Run with: cargo run --bin concurrency_amdahl

/// Speedup with `processors` when `serial` is the non-parallel fraction.
fn speedup(serial: f64, processors: f64) -> f64 {
    1.0 / (serial + (1.0 - serial) / processors)
}

fn main() {
    let processor_counts = [1.0, 2.0, 4.0, 8.0, 16.0];
    let serial_fractions = [0.0, 0.05, 0.10, 0.25, 0.50];

    print!("{:>8} |", "serial");
    for processors in processor_counts {
        print!(" {processors:>6.0}");
    }
    println!("   <- processors");
    println!("{:->9}+{}", "", "-".repeat(7 * processor_counts.len()));

    for serial in serial_fractions {
        print!("{serial:>8.2} |");
        for processors in processor_counts {
            print!(" {:>6.2}", speedup(serial, processors));
        }
        println!();
    }

    println!("\nlimit as processors grow: 1 / serial");
    for serial in serial_fractions {
        let limit = if serial == 0.0 {
            f64::INFINITY
        } else {
            1.0 / serial
        };
        println!("  {serial:>4.2} -> {limit:>6.1}");
    }

    assert!((speedup(0.0, 4.0) - 4.0).abs() < 1e-9);
    assert!((speedup(0.5, 4.0) - 1.6).abs() < 1e-9);
    assert!(speedup(0.5, 16.0) < 1.9, "2x is the ceiling for 50% serial");

    println!("\nall checks passed");
}
```

The table uses format specifiers throughout. `{:>8}` right-aligns in eight columns,
`{processors:>6.0}` prints a floating-point value with no decimals in six columns, and
`{:->9}` fills nine columns with `-`, which produces the rule under the header.

The limit loop checks `serial == 0.0` before dividing, and prints `inf` for a fully
parallel program. Dividing by zero would also produce `f64::INFINITY`, so the check
documents the case rather than preventing an error.

The assertions compare floating-point results with a tolerance, `(a - b).abs() < 1e-9`,
rather than with `==`.

```rust
//! Deadlock detection: a deadlock exists exactly when the wait-for graph has a
//! cycle. Each edge `(waiter, holder)` means the first task is blocked on the
//! second.
//!
//! Run with: cargo run --bin concurrency_deadlock

/// Iterative-friendly depth-first search over a small adjacency list.
fn has_deadlock(waits_for: &[(usize, usize)]) -> bool {
    let Some(highest) = waits_for.iter().flat_map(|(a, b)| [*a, *b]).max() else {
        return false;
    };

    let mut edges = vec![Vec::new(); highest + 1];
    for (waiter, holder) in waits_for {
        edges[*waiter].push(*holder);
    }

    // 1 = on the current path, 2 = fully explored.
    fn visit(node: usize, edges: &[Vec<usize>], state: &mut [u8]) -> bool {
        match state[node] {
            1 => return true,
            2 => return false,
            _ => state[node] = 1,
        }
        for &next in &edges[node] {
            if visit(next, edges, state) {
                return true;
            }
        }
        state[node] = 2;
        false
    }

    let mut state = vec![0u8; edges.len()];
    (0..edges.len()).any(|node| visit(node, &edges, &mut state))
}

fn main() {
    let acyclic = [(0, 1), (1, 2), (0, 2)];
    let cycle = [(0, 1), (1, 2), (2, 0)];
    let self_wait = [(0, 0)];

    for (label, graph) in [
        ("0->1, 1->2, 0->2", &acyclic[..]),
        ("0->1, 1->2, 2->0", &cycle[..]),
        ("0->0", &self_wait[..]),
    ] {
        println!("{label:<20} deadlock: {}", has_deadlock(graph));
    }

    // The four Coffman conditions must all hold for a deadlock; removing any one
    // of them prevents it.
    println!("\nCoffman conditions:");
    for condition in [
        "mutual exclusion",
        "hold and wait",
        "no preemption",
        "circular wait",
    ] {
        println!("  - {condition}");
    }

    assert!(!has_deadlock(&acyclic));
    assert!(has_deadlock(&cycle));
    assert!(has_deadlock(&self_wait));
    assert!(!has_deadlock(&[]));

    println!("\nall checks passed");
}
```

`has_deadlock` finds the largest task number with `flat_map` and `max`. The `let ...
else` returns `false` for an empty edge list, where `max` yields `None`.

The adjacency list is `vec![Vec::new(); highest + 1]`. `Vec::new()` is `Clone`, so the
`vec!` macro can repeat it.

`visit` is a nested function, so it receives the graph and the colour array as
parameters. The `match state[node]` returns early for colours 1 and 2 and marks the node
1 in the catch-all arm.

`(0..edges.len()).any(|node| visit(node, &edges, &mut state))` starts a search from every
vertex, so a cycle in a part of the graph unreachable from vertex 0 is still found.
`any` stops at the first `true`.

## Intuition

The Amdahl program prints:

```text
  serial |      1      2      4      8     16   <- processors
---------+-----------------------------------
    0.00 |   1.00   2.00   4.00   8.00  16.00
    0.05 |   1.00   1.90   3.48   5.93   9.14
    0.10 |   1.00   1.82   3.08   4.71   6.40
    0.25 |   1.00   1.60   2.29   2.91   3.37
    0.50 |   1.00   1.33   1.60   1.78   1.88

limit as processors grow: 1 / serial
  0.00 ->    inf
  0.05 ->   20.0
  0.10 ->   10.0
  0.25 ->    4.0
  0.50 ->    2.0

all checks passed
```

With 5 percent serial work, sixteen processors deliver a speedup of 9.14, and no number
of processors can deliver more than 20.

**`has_deadlock(&[(0, 1), (1, 2), (2, 0)])`**

| call | `state` before | action | returns |
|---|---|---|---|
| `visit(0)` | `[0, 0, 0]` | mark 0 as 1, follow edge to 1 | |
| `visit(1)` | `[1, 0, 0]` | mark 1 as 1, follow edge to 2 | |
| `visit(2)` | `[1, 1, 0]` | mark 2 as 1, follow edge to 0 | |
| `visit(0)` | `[1, 1, 1]` | `state[0] == 1`: on the path | `true` |

The `true` propagates up through each caller's `if visit(...) { return true; }`, and
`any` stops. For the acyclic graph `[(0, 1), (1, 2), (0, 2)]`, the search from 0 marks
2 as fully explored before it follows the edge `0 -> 2`, finds colour 2, and continues,
so every vertex ends at 2 and the result is `false`. The program prints:

```text
0->1, 1->2, 0->2     deadlock: false
0->1, 1->2, 2->0     deadlock: true
0->0                 deadlock: true

Coffman conditions:
  - mutual exclusion
  - hold and wait
  - no preemption
  - circular wait

all checks passed
```

## Time and Space Complexity

| Operation | Time | Space |
|---|---|---|
| `speedup` | `O(1)` | none |
| `has_deadlock` | `O(V + E)`, each vertex is explored once and each edge followed once | `O(V + E)` for the adjacency list and colours, plus `O(V)` stack frames |

`V` is the largest task number plus one, not the number of distinct tasks.

## Limitations

**Amdahl's law assumes a fixed workload.** It answers how much faster the same job
becomes. Gustafson's law answers a different question, how much more work fits in the
same time, and it is the more relevant model when larger machines are used for larger
problems. Amdahl's law also ignores coordination costs, such as lock contention and the
false sharing of chapter 48, which can make a program slower as processors are added.

**The search recurses.** Its documentation comment calls it "iterative-friendly", but
`visit` calls itself once per edge on the current path. A wait-for graph shaped like a
chain of a few hundred thousand tasks would overflow the stack. An explicit stack of
`(node, next_edge_index)` pairs removes the limit.

**Task numbers must be small.** The adjacency list has `highest + 1` entries, so edges
`(0, 4_000_000_000)` allocate billions of empty vectors. A `HashMap<usize, Vec<usize>>`
handles sparse identifiers.

**Detection is not prevention.** The program answers whether a snapshot of the graph has
a cycle. Real systems usually prevent deadlock by removing one Coffman condition, most
often circular wait by acquiring locks in a fixed global order, or they recover with
timeouts.

**The Coffman conditions are printed, not used.** The list in `main` is documentation
for the reader of the output. The detection algorithm tests only circular wait, the one
condition visible in a wait-for graph.

## Summary

- Amdahl's law, `1 / (s + (1 - s) / p)`, bounds the speedup of a fixed workload by
  `1 / s`; a program that is 5 percent serial cannot run more than 20 times faster.
- A deadlock among tasks waiting on each other is a cycle in the wait-for graph.
- Depth-first search with three colours distinguishes a back edge to the current path,
  which is a cycle, from an edge to an already explored vertex, which is not.
- Starting the search from every vertex finds cycles in disconnected parts of the graph.
- Deadlock requires all four Coffman conditions; practical systems prevent one of them,
  usually circular wait through a lock ordering.

## References

- Gene M. Amdahl, "Validity of the single processor approach to achieving large scale
  computing capabilities", *AFIPS Conference Proceedings* 30, 1967, pages 483–485.
- John L. Gustafson, "Reevaluating Amdahl's law", *Communications of the ACM* 31(5),
  1988, pages 532–533.
- E. G. Coffman, M. Elphick, and A. Shoshani, "System deadlocks", *ACM Computing
  Surveys* 3(2), 1971, pages 67–78.
- Thomas H. Cormen, Charles E. Leiserson, Ronald L. Rivest, and Clifford Stein,
  *Introduction to Algorithms*, 4th edition, MIT Press, 2022, Section 20.3,
  "Depth-first search".
- Standard library, [`std::fmt`](https://doc.rust-lang.org/std/fmt/index.html), on width, fill, and precision.
