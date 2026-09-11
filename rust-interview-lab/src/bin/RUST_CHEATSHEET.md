# Rust cheat sheet — the gotchas that cost you minutes

Every snippet below was compiled with `rustc 1.96`, edition 2024. Comments in the code
are the explanation.

Read a block, close the file, type it from memory. If you need to look, you don't have it yet.

---

## 0. The errors I hit while writing this sheet

These are real, not hypothetical. All three are the kind of thing that eats 5 minutes.

```rust
// 1. filter does not change the iterator's Item, even when you destructure it.
let d: Vec<i32> = v.iter().filter(|&&x| x > 2).collect();
// error[E0277]: a value of type `Vec<i32>` cannot be built from an iterator
//               over elements of type `&i32`
let d: Vec<&i32> = v.iter().filter(|&&x| x > 2).collect();          // ok
let d: Vec<i32> = v.iter().filter(|&&x| x > 2).copied().collect();  // ok

// 2. An unannotated float literal can stay ambiguous until a method needs the type.
let mut ys = vec![2.5, 1.0, 3.5];
ys.sort_by(|a, b| b.total_cmp(a));
// error[E0599]: no method named `total_cmp` found for reference `&{float}`
let mut ys: Vec<f64> = vec![2.5, 1.0, 3.5];                          // ok

// 3. Option/Result combinators take `self`, so they move. A second call fails.
let r: Result<i32, String> = Ok(1);
let m = r.map(|v| v + 1);
let e = r.map_err(|err| err.len());
// error[E0382]: use of moved value: `r`
let m = r.as_ref().map(|v| v + 1);        // borrow instead
let e = r.clone().map_err(|err| err.len()); // or clone
```

---

## 1. Which reference level do I have?

The single most common source of noise. Memorise this table.

| You have | You want | Write |
|---|---|---|
| `&Option<T>` | `Option<&T>` | `.as_ref()` |
| `&mut Option<T>` | `Option<&mut T>` | `.as_mut()` |
| `Option<String>` | `Option<&str>` | `.as_deref()` |
| `Option<Box<T>>` | `Option<&T>` | `.as_deref()` |
| `Option<Vec<T>>` | `Option<&[T]>` | `.as_deref()` |
| `Option<&T>`, `T: Copy` | `Option<T>` | `.copied()` |
| `Option<&T>`, `T: Clone` | `Option<T>` | `.cloned()` |
| `Option<T>` | `Option<T>` copy | `.clone()` |

```rust
let a: Option<String> = Some("x".into());

let r: Option<&String> = a.as_ref();      // &Option<T> -> Option<&T>
let s: Option<&str>   = a.as_deref();     // Option<String> -> Option<&str>
let c: Option<String> = a.clone();        // deep copy

let n: Option<i32> = Some(4);
let nr: Option<&i32> = n.as_ref();
let copied: Option<i32> = nr.copied();    // Option<&i32> -> Option<i32>
let cloned: Option<String> = r.cloned();

// Most common real signature: you receive a reference, you return a borrow.
fn takes_ref_option(o: &Option<String>) -> Option<&str> {
    o.as_deref()
}
```

Why it matters: `&Option<T>` is a reference *to the whole Option*. You usually want the
Option of a reference, which is `Option<&T>`. `as_ref` is the bridge, `as_deref` does the
`String -> str` step at the same time.

---

## 2. Option combinators

```rust
let n: Option<i32> = Some(4);

// Transform the value. Closure gets T by value.
let doubled  = n.map(|v| v * 2);                     // Some(8)

// Transform and possibly fail. Closure returns Option.
let positive = n.and_then(|v| (v > 0).then_some(v)); // Some(4)
let lazy     = n.and_then(|v| if v > 100 { Some(v) } else { None });

// Replace None. map_or is eager, map_or_else is lazy. unwrap_or is for a plain value.
let defaulted      = n.map_or(0, |v| v * 2);        // 8
let lazy_default   = n.map_or_else(|| 0, |v| v * 2); // 8
let plain          = n.unwrap_or(0);                 // 4
let plain_lazy     = n.unwrap_or_else(|| 0);         // 4
let default_trait  = n.unwrap_or_default();          // needs i32: Default

// filter takes &T, so deref the closure argument.
let filtered = n.filter(|v| *v > 10);                // None

// Combining two Options.
let chained     = n.and(Some(9));                    // Some(9): n is Some, so take the arg
let alternative = n.or(Some(9));                     // Some(4): n is Some, keep it
let paired      = n.zip(Some("a"));                  // Some((4, "a"))

// Predicate by value.
let checked = n.is_some_and(|v| v > 3);              // true

// Mutating a slot in place.
let mut slot: Option<i32> = None;
let inserted: &mut i32 = slot.get_or_insert(7);      // inserts, returns &mut T
*inserted += 1;
let taken: Option<i32> = slot.take();                // moves out, leaves None
let old:   Option<i32> = slot.replace(3);            // swaps in 3, returns the old value
```

Which one to say out loud: `map` transforms, `and_then` chains a second fallible step,
`unwrap_or` is the default, `ok_or` converts to a `Result` so `?` can take over.

---

## 3. Result and `?`

```rust
fn option_to_result() -> Result<i32, String> {
    let o: Option<i32> = Some(1);
    let v = o.ok_or_else(|| "missing".to_string())?;   // Option -> Result -> `?`
    Ok(v)
}

fn result_combinators() -> Result<i32, String> {
    let r: Result<i32, String> = Ok(1);
    let m = r.as_ref().map(|v| v + 1);     // borrow, do not move
    let e = r.clone().map_err(|err| err.len());
    let chain: Result<i32, String> = Ok(2).and_then(|v| Ok(v * 2));
    let o: Option<i32> = r.ok();           // discards the error
    Ok(1)
}

// `?` in main: no unwrap needed, and the error type is erased.
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let n: i32 = "42".parse::<i32>()?;
    Ok(())
}
```

---

## 4. Iterator closures: `|x|` vs `|&x|` vs `*x`

The rule: some adapters take `Self::Item`, some take `&Self::Item`. The ones taking a
reference hand you one extra `&`.

For `v.iter()` where `Item = &i32`:

| Adapter | Closure argument |
|---|---|
| `map`, `filter_map`, `for_each`, `flat_map` | `&i32` |
| `any`, `all`, `position`, `fold`'s item | `&i32` |
| `filter`, `find`, `take_while`, `skip_while`, `partition` | `&&i32` |
| `max_by_key`, `min_by_key` | `&&i32` |
| `max_by`, `min_by` | `&&i32, &&i32` |
| slice `sort_by` | `&T, &T` |
| slice `sort_by_key`, `binary_search_by` | `&T` |

The escape hatch: call `.copied()` or `.cloned()` first and every downstream closure
works by value. That removes the whole problem.

```rust
let v = vec![3, 1, 4, 1, 5];

// Item is &i32. `x * 2` works because i32: Copy and auto-deref handles the rest.
let a: Vec<i32> = v.iter().map(|x| x * 2).collect();

// Three ways to filter, all valid. Pick one and stay consistent.
let b: Vec<i32>  = v.iter().copied().filter(|x| *x > 2).collect();  // Item = i32
let cc: Vec<i32> = v.iter().filter(|x| **x > 2).copied().collect(); // Item = &i32
let d: Vec<&i32> = v.iter().filter(|&&x| x > 2).collect();          // destructure
let e: Vec<i32>  = v.clone().into_iter().filter(|x| *x > 2).collect(); // owned

let found:  Option<&i32>  = v.iter().find(|x| **x == 4);   // && i32
let idx:    Option<usize> = v.iter().position(|x| *x == 4); // &i32
let any:    bool          = v.iter().any(|x| *x == 4);      // &i32
let all:    bool          = v.iter().all(|x| *x > 0);       // &i32
let mx:     Option<&i32>  = v.iter().max_by_key(|x| **x);    // && i32
let taken:  Vec<&i32>     = v.iter().take_while(|x| **x > 1).collect();

let total:  i32 = v.iter().fold(0, |acc, x| acc + x);  // acc: i32, x: &i32
let summed: i32 = v.iter().sum();
let count        = v.iter().count();
let mapped: Vec<String> = v.iter().map(|x| x.to_string()).collect();

let (small, big): (Vec<i32>, Vec<i32>) = v.iter().copied().partition(|x| *x > 2);
let zipped: Vec<(i32, i32)> = v.iter().copied().zip(v.iter().copied()).collect();

// Option inside a collection: flatten drops the Nones.
let flat: Vec<i32> = vec![Some(1), None, Some(2)].into_iter().flatten().collect();
let transposed: Option<i32> = Some(Some(1)).flatten();
```

`filter` does not change the Item type, even with `|&&x|`. That is error 1 above.

---

## 5. HashMap, HashSet, BTreeMap

```rust
use std::collections::{BTreeMap, HashMap, HashSet};

// The counting idiom. Memorise this exact line.
let words = ["a", "b", "a"];
let mut counts: HashMap<&str, u32> = HashMap::new();
for w in words {
    *counts.entry(w).or_insert(0) += 1;
}

// entry(): insert default, then modify in one lookup.
counts.entry("c").or_insert(0);
counts.entry("a").and_modify(|c| *c += 10).or_insert(1);

// Grouping: or_default() needs V: Default. Vec<u32> is.
let mut groups: HashMap<u32, Vec<u32>> = HashMap::new();
for n in [1u32, 2, 3, 4] {
    groups.entry(n % 2).or_default().push(n);
}

// get returns Option<&V>, never V. That is why you keep needing .copied().
let map: HashMap<i32, i32> = vec![(1, 2)].into_iter().collect();
let lookup: Option<&i32> = map.get(&1);
let value:  Option<i32>  = map.get(&1).copied();
let exists: bool         = map.contains_key(&1);

let set: HashSet<i32> = vec![1, 1, 2].into_iter().collect();

// Ordered iteration needs BTreeMap. HashMap order is arbitrary.
let mut bt: BTreeMap<i32, &str> = BTreeMap::new();
bt.insert(1, "a");
let first = bt.first_key_value();
let in_range = bt.range(0..2).count();
```

Key requirements: `HashMap`/`HashSet` need `Hash + Eq`. `BTreeMap`/`BTreeSet` need `Ord`.
`f64` has neither, so it cannot be a key in any of them.

---

## 6. Sorting, searching, dequeues

```rust
let mut v = vec![(1, "b"), (2, "a"), (1, "a")];

v.sort_by_key(|p| p.0);                        // stable, key: &T -> K
v.sort_by_key(|p| std::cmp::Reverse(p.0));     // descending without a custom comparator
v.sort_by(|a, b| a.0.cmp(&b.0).then(a.1.cmp(b.1))); // tie-break: Ordering::then
v.sort_unstable();                             // fastest, order not preserved
v.sort_unstable_by(|a, b| b.0.cmp(&a.0));      // descending

let mut xs = vec![3, 1, 4, 1, 5];
xs.sort_unstable();
xs.dedup();                                    // only removes CONSECUTIVE duplicates

let idx: Result<usize, usize> = xs.binary_search(&4);          // Ok(found) | Err(insert_at)
let idx2: Result<usize, usize> = v.binary_search_by_key(&2, |p| p.0); // slice must be sorted
let has = xs.contains(&4);                     // linear scan, no sort needed

// Floats: sort with total_cmp, never partial_cmp().unwrap(). NaN makes the latter panic.
let mut ys: Vec<f64> = vec![2.5, 1.0, 3.5];
ys.sort_by(|a, b| b.total_cmp(a));             // descending, NaN-safe, total order

// VecDeque is the queue and stack with O(1) at both ends.
let mut q = std::collections::VecDeque::new();
q.push_back(1);
q.push_front(0);
let front = q.pop_front();
let back  = q.pop_back();
```

`sort_by_key` cannot return a borrowed value — use `sort_by` for that. `dedup` without a
preceding sort does almost nothing.

---

## 7. BinaryHeap, `Ord`, and f64

`BinaryHeap<T>` requires `T: Ord`, which is why f64 does not work: it only implements
`PartialOrd`, because NaN has no ordering.

```rust
use std::cmp::{Ordering, Reverse};
use std::collections::BinaryHeap;

// Ord types are fine. This is a MAX-heap.
let mut max_heap: BinaryHeap<i32> = BinaryHeap::new();
max_heap.push(3);
max_heap.push(1);
let top:  Option<i32>  = max_heap.pop();    // Some(3) - largest first
let peek: Option<&i32> = max_heap.peek();   // borrow, does not remove
let from_vec: BinaryHeap<i32> = BinaryHeap::from(vec![1, 2, 3]);

// Min-heap: wrap in Reverse. pop() then gives Reverse<T>, so unwrap the field.
let mut min_heap: BinaryHeap<Reverse<i32>> = BinaryHeap::new();
min_heap.push(Reverse(5));
min_heap.push(Reverse(2));
let smallest = min_heap.pop().map(|r| r.0); // Some(2)

// Tuples are Ord when all elements are. This is a tie-broken key.
let mut pairs: BinaryHeap<(i32, usize)> = BinaryHeap::new();
pairs.push((1, 0));
pairs.push((2, 1));

// A heap of f64 needs a wrapper. All five items below are required:
// derive PartialEq, then impl Eq, PartialOrd, Ord.
#[derive(PartialEq)]
struct F(f64);

impl Eq for F {}

impl PartialOrd for F {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))          // delegate: total_cmp is already a total order
    }
}

impl Ord for F {
    fn cmp(&self, other: &Self) -> Ordering {
        self.0.total_cmp(&other.0)     // never panics, handles NaN and -0.0
    }
}

let mut float_heap: BinaryHeap<F> = BinaryHeap::new();
float_heap.push(F(1.5));
float_heap.push(F(0.5));
let smallest_float = float_heap.pop().map(|f| f.0);
```

If the interviewer only wants a sorted list, skip the wrapper: `sort_by(|a, b| b.total_cmp(a))`.
Reach for the heap when you need streaming top-k, and say why.

---

## 8. Locks, guards, and the deadlock I wrote

`Mutex::lock()` returns `LockResult<MutexGuard<T>>`, so it needs `unwrap()`, and the guard
is what derefs to `T`.

```rust
use std::sync::{Arc, Mutex, RwLock};
use std::sync::atomic::{AtomicUsize, Ordering};

let shared = Arc::new(Mutex::new(vec![1]));

let mut handles = Vec::new();
for i in 0..4 {
    let shared = Arc::clone(&shared);          // clone the handle, move it in
    handles.push(std::thread::spawn(move || {
        let mut guard = shared.lock().unwrap(); // MutexGuard<Vec<i32>>
        guard.push(i);                          // method call auto-derefs
        *guard = vec![i];                       // explicit deref to replace the value
    }));                                        // guard drops here -> unlock
}
for h in handles { h.join().unwrap(); }

// Poisoning: lock() is a Result. Propagate, or take the data back.
let ignoring = shared.lock().unwrap_or_else(|e| e.into_inner());

// THE TRAP. These two look identical and are not.
let _ = shared.lock();     // guard dropped at the end of THIS statement: not locked
let _g = shared.lock();    // guard held until end of scope: intended

// THE OTHER TRAP. `lock()` returns a guard, so binding it holds the lock for the
// rest of the body. This deadlocks on the final line, same thread, no warning:
//   let again = shared.lock().unwrap();
//   let g2 = shared.lock().unwrap();      // hangs forever
// Bind the DATA instead, or scope the guard:
let len = { let g = shared.lock().unwrap(); g.len() };
```

```rust
// RwLock: many readers OR one writer.
let rw = Arc::new(RwLock::new(0));
{
    let r1 = rw.read().unwrap();
    let r2 = rw.read().unwrap();   // two readers coexist
}
{
    let mut w = rw.write().unwrap();
    *w += 1;
}

// Atomics: every operation takes an Ordering. Forgetting it is a compile error.
let counter = AtomicUsize::new(0);
counter.fetch_add(1, Ordering::Relaxed);
let loaded  = counter.load(Ordering::SeqCst);
let swapped = counter.swap(5, Ordering::AcqRel);
let cas: Result<usize, usize> =
    counter.compare_exchange(5, 6, Ordering::AcqRel, Ordering::Relaxed);
```

Which to reach for:

| Need | Type | Notes |
|---|---|---|
| Counter across threads | `AtomicUsize` | needs an `Ordering` every call |
| Counter, single thread | `Cell<T>` | `T: Copy` only, `get`/`set` |
| Shared mutable state, single thread | `RefCell<T>` | `borrow`/`borrow_mut`, **panics** on conflict |
| Shared mutable state, threads | `Mutex<T>` | blocking, **poisons** on panic |
| Read-mostly across threads | `RwLock<T>` | many readers or one writer |
| Single-thread shared ownership | `Rc<T>` | not `Send` |
| Cross-thread shared ownership | `Arc<T>` | clone the handle, not the data |

Lock guard held across `.await` is not `Send` — that needs `tokio::sync::Mutex`.

---

## 9. Strings

```rust
let s:  String = "hi there".to_string();
let s2: String = String::from("hi");
let s3: String = "hi".to_owned();

let r:  &str = &s;            // deref coercion: String -> &str
let r2: &str = s.as_str();    // the explicit form
let own: String = r.to_string(); // &str -> String

// parse returns Result, so it needs `?` or an unwrap in a function.
let n: i32 = "42".parse::<i32>()?;
let with_default = "42".parse::<i32>().unwrap_or(0);
let as_option    = "42".parse::<i32>().ok();

let parts: Vec<&str> = s.split_whitespace().collect();
let joined = parts.join(",");
let upper  = s.to_uppercase();
let first: Option<char> = s.chars().next();    // bytes vs chars are different
let nth:   Option<char> = s.chars().nth(1);
let reversed: String = s.chars().rev().collect();
let formatted = format!("{s} {n}");

let mut m = String::new();
m.push('a');
m.push_str("bc");
```

`s[0]` gives a *byte* and panics on a non-ASCII boundary. Use `s.chars().nth(i)`.
Function parameters should be `&str`, struct fields should be `String`.

---

## 10. Match ergonomics

Matching a reference makes the bindings references automatically. You rarely need `&` in
the pattern.

```rust
match &opt {
    Some(x) => { let _: &String = x; }   // x is &String, no `&` written
    None => {}
}

match &mut mopt {
    Some(x) => x.push('!'),              // x is &mut String
    None => {}
}

match opt {
    Some(x) => { let _: String = x; }     // x is String: this one MOVES
    None => {}
}

if let Some(x) = &mopt {}                 // x: &String
while let Some(x) = stack.pop() {}        // x: i32, owned
let Some(x) = mopt else { return };       // let-else: bind or leave

if let Some(Ok(v)) = Some(Ok::<i32, String>(1)) {}  // nested patterns in one line

let s = String::from("quit");
match &s[..] {                            // &str patterns need a slice, not &String
    "quit" => {}
    _ => {}
}

match n {
    x @ 1..=5 => { let _ = x; }           // bind and test at once
    _ => {}
}
```

When the compiler says `expected &String, found String`, add `&` to the scrutinee
(`match &opt`) rather than to the pattern.

---

## 11. Escaping the borrow checker

```rust
let mut v = vec![1, 2, 3, 4];

// Two mutable borrows into one slice, without cloning.
let (left, right) = v.split_at_mut(2);
left[0] = 9;
right[0] = 8;

// Read and write in one expression does not compile. Copy the index out first.
let i = 1usize;
let value = v[i];
v[i] = value + 1;

for x in &mut v { *x += 1; }        // &mut i32, deref to assign
for x in v.iter().copied() { }      // by value, no borrow held

// Move a value out of a slot that is borrowed elsewhere.
let mut owned = vec![1, 2, 3];
let taken    = std::mem::take(&mut owned);              // leaves Default (empty)
let replaced = std::mem::replace(&mut owned, vec![7]);  // leaves vec![7]

let mut opt = Some(vec![1]);
let moved = opt.take();                                  // Option<T> -> Option<T>, leaves None

let snapshot = v.len();     // copy the value out
let copy = v.clone();       // the pragmatic unblock when you are short on time
```

Order of attack when the borrow checker fights you: copy the value out, then
`split_at_mut`, then `mem::take`, then `clone`. Save `clone` for when the clock matters
and say out loud that you know it is a clone.

---

## 12. Final checklist of syntax slips

- `Vec::pop`, `HashMap::get`, `stack.pop()`, `BinaryHeap::pop` all return `Option`. Handle it.
- `.iter()` gives `&T`; add `.copied()` / `.cloned()` before the closures.
- `filter`, `find`, `take_while`, `max_by_key` give `&&T`.
- The binding needs `mut`, not the value: `let mut v = ...`.
- `.collect()` needs a target type: `let v: Vec<_> = ...` or `collect::<Vec<_>>()`.
- Integer literals default to `i32`; annotate `0usize`, `vec![0u32; n]` when indexing.
- Indexing needs `usize`: `v[x as usize]`.
- Unannotated float literals can stay ambiguous until a method pins the type.
- `Option`/`Result` combinators take `self` and move. Use `.as_ref()` to keep the value.
- Locks return guards. Bind the data, not the guard. `let _ = lock()` unlocks instantly.
- `#[derive(Debug, Clone, PartialEq)]` on any struct you plan to print or assert on.
- `assert_eq!` needs `Debug` and `PartialEq` on both sides.
- `.to_string()` needs `Display`; `format!("{x:?}")` needs `Debug`.
- Closure needs `move` only to cross a thread boundary or to return it.
- `Arc::clone(&x)` inside the loop, then `move` the clone into the spawn.
