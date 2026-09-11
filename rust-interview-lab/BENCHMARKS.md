# Benchmark results

Recorded output from the programs in `benchmarking_examples/`, produced in release
mode on the machine listed below. The written report is in
`benchmarking_examples/benchmarking-report.pdf`.

## Environment

| | |
|---|---|
| CPU | `aarch64`, 8 cores (NVIDIA Jetson) |
| Toolchain | `rustc 1.96.0-nightly (55e86c996 2026-04-02)` |
| Build | `--release` |
| Threads | one per measurement |

Absolute times are specific to this machine, compiler, and allocator. The ratios
and the maximum list size are the quantities intended to carry over, the latter
only for a comparable stack size.

## Procedure

Each measurement is preceded by a warm-up pass of the same magnitude as the
measured pass and is then repeated three times, with the shortest pass reported. A
single pass is not reproducible on this platform: a first pass over a fresh heap
measured between 2.3 ms and 11.4 ms for one push loop of fixed size, the variation
being attributable to page mapping rather than to the structure under test.

The variants `box` and `box+drop` share one `push_front` implementation and differ
only in deallocation, so their push times serve as a control on the measurement.

Every list run removes each inserted value and checks the order before reporting a
time. Every cache run compares the hit counts of the two implementations before
reporting a time.

## Cache: index arena and `Rc<RefCell>` list

Command: `cargo run --release --bin benchmark cache`

Both implementations maintain the same doubly linked LRU. One holds its nodes in a
`Vec` and links them by `usize` index; the other allocates an `Rc<RefCell<_>>` per
node and links them by pointer. Both process one request sequence over 131,072
keys with a capacity of 65,536 entries.

```
LRU cache: 65,536 entries, 10,000,000 requests over 131,072 keys
A miss inserts and evicts the least recently used entry.
Best of 3 runs per cache.

  hit rate: 89.8%  (8,979,314 hits, 1,020,686 inserts)

  storage                       total   per request
  ------------------------------------------------
  arena (Vec + indices)         1.03s      103 ns
  Rc<RefCell> list              1.86s      186 ns

  the arena is 1.81x faster on the same requests: 1.03s against 1.86s
  the arena reuses the evicted slot; the list frees a node and allocates another
```

### Observations

- A successful lookup moves an entry to the front of the list. The arena writes
  and reads indices in vector slots. The list clones a handle, upgrades a weak
  handle, borrows the cell, and writes through the borrow, in addition to reaching
  a separate heap allocation.
- Eviction reuses the least recently used slot in the arena. The list removes the
  tail node from the hash table and allocates a node for the incoming key.
- The hash table lookup is identical in both implementations and accounts for a
  large part of each request, so the ratio depends on the proportion of each
  request spent on list maintenance. Measured across access patterns, the ratio
  ranges from 1.1 to 1.9; an all-hits stream reaches 1.83 and a stream that never
  repeats a key falls to 1.30.
- Both implementations are single-threaded. Neither figure includes the
  synchronisation that a shared arena would require.

## Linked lists: four variants

Command: `cargo run --release --bin benchmark list [variant] [n]`

Four singly linked lists with identical push and pop operations, differing in node
representation and in deallocation.

| list | storage | deallocation | 260,000 nodes | 270,000 nodes |
|---|---|---|---|---|
| `box` | `Option<Box<Node<T>>>` | recursive | completed | aborted |
| `enum` | `Next(T, Box<ListNode<T>>)` | recursive | completed | aborted |
| `box+drop` | `Option<Box<Node<T>>>` | iterative | completed | completed |
| `enum+drop` | `Next(T, Box<ListNode<T>>)` | iterative | completed | completed |

The recursive variants terminate at 270,000 nodes. The message recorded is:

```
thread 'main' has overflowed its stack
fatal runtime error: stack overflow, aborting
```

Deallocating a node deallocates its successor, which deallocates its successor, at
a cost of one stack frame per element. With an 8 MiB stack the limit falls between
260,000 and 270,000 elements, which corresponds to approximately 32 bytes per
element. The value of 5,000,000 reported below is the largest size tested, not an
observed limit.

Timings at 200,000 elements, and at 5,000,000 elements for the two variants that
complete at that size:

```
  variant        elements          push          drop
  ----------------------------------------------------
  box             200,000        2.40ms        3.23ms
  enum            200,000        3.42ms        3.20ms
  box+drop        200,000        2.32ms        2.91ms
  enum+drop       200,000        3.62ms        2.52ms

  box+drop      5,000,000       58.11ms       72.32ms
  enum+drop     5,000,000       90.98ms       67.51ms
```

### Observations

- Insertion costs 12.0 ns per element for the boxed node and 17.1 ns for the enum
  node. `Option<Box<T>>` occupies one machine word because the all-zero address
  encodes the empty case; the enum carries a discriminant in addition, so each
  insertion moves more memory.
- Deallocation costs 16.2 ns, 16.0 ns, 14.6 ns, and 12.6 ns per element for the
  four variants. The iterative strategy saves 0.32 ms and 0.68 ms respectively at
  200,000 elements, against totals of 3.23 ms and 3.20 ms. The difference between
  the strategies is therefore small at this size; the properties that separate
  them are the maximum size and the absence of recursion.
- The push times of `box` and `box+drop`, 2.40 ms and 2.32 ms, agree within the
  run-to-run variation, which is the expected result for identical push code.

## Reproduce

```bash
cargo run --release --bin benchmark                      # cache, then lists
cargo run --release --bin benchmark cache                # cache only
cargo run --release --bin benchmark list                 # all four variants
cargo run --release --bin benchmark list enum+drop 5000000
cargo run --release --bin benchmark list box 260000      # completes
cargo run --release --bin benchmark list box 270000      # aborts
```
