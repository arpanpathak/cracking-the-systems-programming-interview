# Index {#index}

## A

- **`ApiError`**, error enumeration carrying data, [19](#state-machine), [35](#integration-tests)
- **`Arc`**, shared ownership across threads, [21](#worker-pool), [22](#mutex-poisoning), [30](#bounded-buffer)
- **`args`**, the command-line boundary, [29](#command-line-arguments)
- **`assert!`**, refusal of an empty input as a design decision, [21](#worker-pool)
- **assertion in a destructor-free type**, [13](#subsets)
- **`attach` and `detach`**, index-linked list maintenance, [18](#lru-cache-array)
- **average, limits of**, a benchmark statistic that hides the distribution, [24](#syscall-overhead)

## B

- **backtracking**, `result.push(path.clone())`, `path.pop()`, [13](#subsets)
- **`BinaryHeap`**, a max-heap, so pairs sort by the first field, [6](#top-k-frequent), [32](#running-median)
- **binary search**, half-open range and the sorted-half test, [9](#binary-search)
- **binary search tree**, ordering invariant, three removal shapes, [8](#binary-search-tree)
- **binary tree**, algebraic data type with boxed children, [7](#binary-tree), [35](#integration-tests)
- **`black_box`**, keeping a measurement alive, [24](#syscall-overhead)
- **bounded buffer**, one mutex and two condition variables, [30](#bounded-buffer)
- **`Box`**, one ownership pointer, one allocation, [7](#binary-tree), [14](#reverse-linked-list), [15](#singly-linked-list)
- **BFS**, flood fill with a queue, [23](#counting-islands)
- **borrow counter**, `RefCell` and the run-time check, [16](#doubly-linked-list)

## C

- **cache**, two designs, bounded and unbounded memory, [17](#lru-cache), [18](#lru-cache-array)
- **capacity hint**, `with_capacity` and its units, [1](#two-sum), [2](#valid-parentheses), [13](#subsets)
- **channel**, `mpsc` for jobs and results, [21](#worker-pool)
- **`checked_sub`**, the fix for overflow at the target, [1](#two-sum)
- **clone**, value copied out of a guard or a map, [16](#doubly-linked-list), [17](#lru-cache)
- **closure**, taking a mutable reference as a parameter, [23](#counting-islands)
- **coin change**, dynamic program over amounts, [12](#coin-change)
- **command-line arguments**, `env::args` and the first item, [29](#command-line-arguments)
- **condition variable**, a directed wake-up for each state change, [30](#bounded-buffer)
- **connected components**, counting them by flood fill, [23](#counting-islands)
- **copy**, `fs::copy` and what it preserves, [28](#file-operations)
- **cost model**, instructions, memory, stack, compilation, [24](#syscall-overhead)
- **cycle detection**, a short topological order, [11](#topological-sort)

## D

- **`dead_code` warning**, the unused second merge function, [5](#merge-intervals), [24](#syscall-overhead)
- **`Default`**, `#[derive(Default)]` and `#[default]` on a variant, [3](#min-stack), [8](#binary-search-tree), [10](#trie)
- **destructor**, recursion in derived drop glue, [7](#binary-tree), [14](#reverse-linked-list), [15](#singly-linked-list), [16](#doubly-linked-list)
- **directory traversal**, `read_dir` and a recursive walk, [27](#paths-and-directories)
- **discriminant**, a `size_of` of one byte for a six-variant enum, [19](#state-machine)
- **`Display`**, the trait a message method should implement, [19](#state-machine)
- **`drop`**, releasing a sender to end a receive loop, [21](#worker-pool)
- **`Duration`**, a retry delay carried by an error variant, [19](#state-machine)
- **dynamic dispatch**, a trait object and the vtable call, [21](#worker-pool)

## E

- **enum**, states a caller cannot construct illegally, [7](#binary-tree), [8](#binary-search-tree), [19](#state-machine)
- **epigraph**, attributed quotations in this book, [references](#references)
- **`ErrorKind`**, branching on a failure without parsing a message, [28](#file-operations)
- **eviction**, least recently used, in two designs, [17](#lru-cache), [18](#lru-cache-array)
- **error type**, variants with data, and matching on them, [19](#state-machine)

## F

- **`f64`**, a rate that is neither validated nor reported, [20](#rate-limiter); a median that cannot be an integer, [32](#running-median)
- **file I/O**, `fs::write`, `OpenOptions` and `BufReader`, [26](#files-and-io)
- **file operations**, `copy`, `rename` and `remove_file`, [28](#file-operations)
- **flood fill**, marking on entry, [23](#counting-islands)
- **`format!`**, one allocation per call, [19](#state-machine), [25](#shadowing)

## H

- **half-open range**, `[low, high)` as the search invariant, [9](#binary-search)
- **hash map**, expected constant time and the assumption behind it, [1](#two-sum), [6](#top-k-frequent), [10](#trie)
- **heap**, `BinaryHeap` as a priority queue, [6](#top-k-frequent), [32](#running-median)
- **`HashSet`**, the visited set that a bitmap would replace, [23](#counting-islands)

## I

- **idempotency**, a keyed store that runs an operation at most once, [34](#idempotent-operations)
- **in-degree**, the counter Kahn's algorithm waits on, [11](#topological-sort)
- **index-linked list**, nodes in a vector, links as integers, [18](#lru-cache-array)
- **`Instant`**, the clock a limiter trusts, [20](#rate-limiter); the clock a measurement reads, [31](#parallel-sum)
- **integration test**, what the crate boundary hides, [35](#integration-tests)
- **interior mutability**, mutation behind a shared reference, [16](#doubly-linked-list)
- **invariant**, a sentence true before and after every operation, [3](#min-stack), [9](#binary-search), [13](#subsets), [32](#running-median)

## J

- **`JoinHandle::join`**, a discarded panic, [21](#worker-pool), [22](#mutex-poisoning)

## K

- **Kahn's algorithm**, topological sort by in-degree, [11](#topological-sort)
- **`key`**, the field a full cache reads back before overwriting a slot, [18](#lru-cache-array)

## L

- **lifetime**, `'a` in the range query, and what it ties together, [8](#binary-search-tree)
- **linked list**, reversal with three bindings, [14](#reverse-linked-list)
- **lock**, held across a clock read, released before the work, [20](#rate-limiter), [21](#worker-pool), [30](#bounded-buffer)
- **LRU**, least recently used, [17](#lru-cache), [18](#lru-cache-array)

## M

- **max-heap**, why the top-k result pops the largest pair, [6](#top-k-frequent)
- **median, running**, two heaps and a rebalancing rule, [32](#running-median)
- **`mem::replace`**, moving a value out of a place, [15](#singly-linked-list), [8](#binary-search-tree)
- **`mem::swap`**, exchanging two subtrees, [7](#binary-tree); two bytes, [33](#reverse-string)
- **Mutex**, protection, and the poison mark, [20](#rate-limiter), [21](#worker-pool), [22](#mutex-poisoning), [30](#bounded-buffer)
- **monomorphisation**, one copy of the code per type argument, [1](#two-sum)
- **mutation**, writing to a binding rather than rebinding it, [25](#shadowing)

## N

- **`new`**, and the `Default` implementation Clippy expects, [15](#singly-linked-list)
- **`None`**, the end of a list, not a sentinel, [14](#reverse-linked-list)

## O

- **`OpenOptions`**, `create` and `append` flags, [26](#files-and-io)
- **`Option`**, absence in the type, [1](#two-sum), [3](#min-stack), [12](#coin-change), [14](#reverse-linked-list), [32](#running-median)
- **overhead**, the boundary cost of a system call, [24](#syscall-overhead)
- **overflow**, arithmetic that differs between debug and release, [1](#two-sum), [9](#binary-search), [13](#subsets)

## P

- **panic**, unwinding while a guard is alive, [20](#rate-limiter), [22](#mutex-poisoning); reversal of a non-ASCII string, [33](#reverse-string)
- **parallel sum**, borrowed workers under a scope, [31](#parallel-sum)
- **`PartialEq`**, the minimal bound on a grid cell, [23](#counting-islands)
- **`Path` and `PathBuf`**, borrowed and owned paths, [27](#paths-and-directories)
- **`PoisonError`**, the error a poisoned lock returns, [22](#mutex-poisoning)
- **prefix tree**, see trie, [10](#trie)
- **pruning**, a range query that skips whole subtrees, [8](#binary-search-tree)

## R

- **`Rc`**, shared ownership on one thread, [16](#doubly-linked-list)
- **`read_dir`**, one `Result` per directory entry, [27](#paths-and-directories)
- **`Ref` and `Ref::map`**, a guard projected to a field, [16](#doubly-linked-list)
- **`RefCell`**, mutation with a run-time borrow check, [16](#doubly-linked-list)
- **recursion**, stack depth proportional to input, [7](#binary-tree), [8](#binary-search-tree), [14](#reverse-linked-list), [27](#paths-and-directories)
- **refill**, tokens computed from elapsed time, [20](#rate-limiter)
- **rename**, an atomic replacement within one filesystem, [28](#file-operations)
- **`Result`**, failure in the type, [19](#state-machine), [22](#mutex-poisoning)
- **`Reverse`**, flipping a heap's ordering, [32](#running-median)

## S

- **`Send` and `Sync`**, what a single-threaded structure does not implement, [16](#doubly-linked-list)
- **sentinel**, `usize::MAX` kept inside the table, [12](#coin-change)
- **shadowing**, a new binding with an old name, [25](#shadowing)
- **sliding window**, a start index that only moves forward, [4](#sliding-window)
- **`sort_unstable_by_key`**, ordering intervals by start, [5](#merge-intervals)
- **stack**, frames per call, and the depth they reach, [7](#binary-tree), [15](#singly-linked-list), [27](#paths-and-directories)
- **state machine**, legal transitions in one `match`, [19](#state-machine)
- **`String`**, an allocated message on an error path, [19](#state-machine)
- **string reversal**, an in-place byte swap under an ASCII precondition, [33](#reverse-string)
- **subsets**, `2^n` results and the clone per result, [13](#subsets)
- **syscall**, the user and kernel boundary, [24](#syscall-overhead)

## T

- **`thread::scope`**, workers that borrow the input, [31](#parallel-sum)
- **tie-break**, the ordering the top-k result depends on, [6](#top-k-frequent)
- **token bucket**, burst then rate, [20](#rate-limiter)
- **topological sort**, an order in which edges point forward, [11](#topological-sort)
- **trace**, the state after each step, produced by running the code, [2](#valid-parentheses), [5](#merge-intervals), [9](#binary-search), [11](#topological-sort)
- **trait object**, `dyn` and what it costs, [21](#worker-pool)
- **`try_unwrap`**, moving a value out of an `Rc`, [16](#doubly-linked-list)

## U

- **`unsafe`**, the obligation a `SAFETY` comment states, [24](#syscall-overhead), [33](#reverse-string)
- **unit test**, access to private items, [35](#integration-tests)
- **`upgrade`**, turning a weak pointer into a strong one, [16](#doubly-linked-list)

## V

- **`Vec`**, amortised growth and reuse of a slot, [18](#lru-cache-array)
- **`VecDeque`**, constant time at both ends, [11](#topological-sort), [17](#lru-cache), [30](#bounded-buffer)

## W

- **warm-up**, why a benchmark runs the code before timing it, [24](#syscall-overhead)
- **`Weak`**, observing without owning, [16](#doubly-linked-list)
- **worker pool**, bounded threads, ordered results, [21](#worker-pool)
