//! One main for every benchmark in the lab.
//!
//! Usage:
//!   cargo run --release --bin benchmark                    # cache, then lists
//!   cargo run --release --bin benchmark cache              # cache only
//!   cargo run --release --bin benchmark list               # all four variants
//!   cargo run --release --bin benchmark list enum 500000   # one variant, one size
//!
//! The recursive list variants abort with a stack overflow past roughly 265,000
//! nodes, so run them below that size or on their own.

use std::hint::black_box;
use std::time::{Duration, Instant};

use nvidia_rust_interview_lab::cache::Cache;
use nvidia_rust_interview_lab::cache::arena::LruCache as ArenaCache;
use nvidia_rust_interview_lab::cache::rc_list::LruCache as RcCache;
use nvidia_rust_interview_lab::lists::SinglyList;
use nvidia_rust_interview_lab::lists::{boxed, boxed_drop, enum_drop, enum_node};

const CACHE_CAPACITY: usize = 65_536;
const KEY_SPACE: u64 = 131_072;
const OPERATIONS: u64 = 10_000_000;
const DEFAULT_LIST_ELEMENTS: usize = 200_000;
/// Timed passes per cache; the fastest is reported, since a slow pass is noise.
const CACHE_RUNS: usize = 3;
/// Timed passes per list variant.
const LIST_RUNS: usize = 3;

fn main() {
    let arguments: Vec<String> = std::env::args().skip(1).collect();

    match arguments.first().map(String::as_str) {
        Some("cache") => cache_benchmark(),
        Some("list") => {
            let variant = arguments.get(1).map(String::as_str);
            let elements = arguments
                .get(2)
                .and_then(|value| value.parse().ok())
                .unwrap_or(DEFAULT_LIST_ELEMENTS);
            list_benchmark(variant, elements);
        }
        _ => {
            cache_benchmark();
            println!();
            list_benchmark(None, DEFAULT_LIST_ELEMENTS);
        }
    }
}

// ---------------------------------------------------------------------------
// Cache: arena vs Rc<RefCell> linked list
// ---------------------------------------------------------------------------

/// Request stream with realistic locality: four requests in five come from a hot
/// set of 1% of the keys, the rest from the whole space.
fn key_at(state: u64) -> u64 {
    let mixed = state >> 17;
    if (state >> 33) % 100 < 80 {
        mixed % (KEY_SPACE / 100)
    } else {
        mixed % KEY_SPACE
    }
}

/// The fastest of `CACHE_RUNS` timed passes, with the hit count and final size
/// from the last one. Each pass starts from an empty cache, so the stream is the
/// same every time.
fn best_cache_run<C: Cache<u64, u64>>() -> (Duration, u64, usize) {
    let mut best = Duration::MAX;
    let mut hits = 0;
    let mut len = 0;

    for _ in 0..CACHE_RUNS {
        let mut cache = C::new(CACHE_CAPACITY);
        let (elapsed, run_hits) = cache_workload(&mut cache);
        best = best.min(elapsed);
        hits = run_hits;
        len = cache.len();
    }
    (best, hits, len)
}

/// The same request stream against any cache.
fn cache_workload<C: Cache<u64, u64>>(cache: &mut C) -> (Duration, u64) {
    let mut state = 0x9e37_79b9_7f4a_7c15u64;
    let mut hits = 0u64;

    let start = Instant::now();
    for _ in 0..OPERATIONS {
        state = state
            .wrapping_mul(6_364_136_223_846_793_005)
            .wrapping_add(1_442_695_040_888_963_407);
        let key = key_at(state);

        match cache.get(&key) {
            Some(value) => {
                hits += 1;
                black_box(value);
            }
            None => cache.put(key, key.rotate_left(17)),
        }
    }
    (start.elapsed(), hits)
}

fn cache_benchmark() {
    println!(
        "LRU cache: {} entries, {} requests over {} keys",
        with_thousands(CACHE_CAPACITY as u64),
        with_thousands(OPERATIONS),
        with_thousands(KEY_SPACE)
    );
    println!("A miss inserts and evicts the least recently used entry.");
    println!("Best of {CACHE_RUNS} runs per cache.\n");

    let (arena_time, arena_hits, arena_len) = best_cache_run::<ArenaCache<u64, u64>>();
    let (list_time, list_hits, list_len) = best_cache_run::<RcCache<u64, u64>>();

    // Same population and same hit count, or this compares nothing.
    assert_eq!(arena_len, list_len);
    assert_eq!(
        arena_hits, list_hits,
        "the two runs saw different request streams"
    );

    println!(
        "  hit rate: {:.1}%  ({} hits, {} inserts)\n",
        arena_hits as f64 * 100.0 / OPERATIONS as f64,
        with_thousands(arena_hits),
        with_thousands(OPERATIONS - arena_hits)
    );

    let per_request = |elapsed: Duration| elapsed.as_nanos() as f64 / OPERATIONS as f64;

    // `{:.2?}` uses Duration's own Debug format, rounded to two decimals.
    println!("  {:<22} {:>12} {:>13}", "storage", "total", "per request");
    println!("  {}", "-".repeat(48));
    for (name, elapsed) in [
        (
            <ArenaCache<u64, u64> as Cache<u64, u64>>::variant(),
            arena_time,
        ),
        (<RcCache<u64, u64> as Cache<u64, u64>>::variant(), list_time),
    ] {
        println!(
            "  {name:<22} {elapsed:>12.2?} {:>8.0} ns",
            per_request(elapsed)
        );
    }

    let speedup = list_time.as_secs_f64() / arena_time.as_secs_f64();
    println!(
        "\n  the arena is {speedup:.2}x faster on the same requests: {arena_time:.2?} against {list_time:.2?}"
    );
    println!("  the arena reuses the evicted slot; the list frees a node and allocates another");
}

// ---------------------------------------------------------------------------
// Lists: four variants, one loop
// ---------------------------------------------------------------------------

fn list_benchmark(variant: Option<&str>, elements: usize) {
    println!(
        "Singly linked list: push {} values, pop them back in order, then drop a full list",
        with_thousands(elements as u64)
    );
    println!("Best of {LIST_RUNS} runs per variant, allocator warmed up.\n");
    println!(
        "  {:<10} {:>12} {:>13} {:>13}",
        "variant", "elements", "push", "drop"
    );
    println!("  {}", "-".repeat(52));

    match variant {
        Some("box") => run_list::<boxed::LinkedList<u64>>(elements),
        Some("enum") => run_list::<enum_node::LinkedList<u64>>(elements),
        Some("box+drop") => run_list::<boxed_drop::LinkedList<u64>>(elements),
        Some("enum+drop") => run_list::<enum_drop::LinkedList<u64>>(elements),
        _ => {
            run_list::<boxed::LinkedList<u64>>(elements);
            run_list::<enum_node::LinkedList<u64>>(elements);
            run_list::<boxed_drop::LinkedList<u64>>(elements);
            run_list::<enum_drop::LinkedList<u64>>(elements);
        }
    }
}

fn run_list<L: SinglyList<u64>>(elements: usize) {
    // Warm the allocator first: without this the first variant in a process pays
    // for fresh heap pages and looks several times slower than an identical one.
    let mut warm_up = L::new();
    for value in 0..elements as u64 {
        warm_up.push_front(value);
    }
    drop(warm_up);

    let mut best_push = Duration::MAX;
    let mut best_drop = Duration::MAX;

    for _ in 0..LIST_RUNS {
        let mut list = L::new();

        let start = Instant::now();
        for value in 0..elements as u64 {
            list.push_front(value);
        }
        best_push = best_push.min(start.elapsed());

        // Pop every value back and check the order, so a broken list cannot post
        // a fast time.
        let mut expected = elements as u64;
        while let Some(value) = list.pop_front() {
            expected -= 1;
            assert_eq!(value, expected, "{} lost LIFO order", L::variant());
        }
        assert_eq!(expected, 0);
        black_box(expected);

        // Rebuild, then time the drop of a full list. This is where the
        // recursive variants overflow the stack.
        for value in 0..elements as u64 {
            list.push_front(value);
        }
        let start = Instant::now();
        drop(list);
        best_drop = best_drop.min(start.elapsed());
    }

    println!(
        "  {:<10} {:>12} {best_push:>13.2?} {best_drop:>13.2?}",
        L::variant(),
        with_thousands(elements as u64)
    );
}

fn with_thousands(value: u64) -> String {
    let digits = value.to_string();
    let mut out = String::with_capacity(digits.len() + digits.len() / 3);
    for (index, digit) in digits.chars().enumerate() {
        if index > 0 && (digits.len() - index) % 3 == 0 {
            out.push(',');
        }
        out.push(digit);
    }
    out
}
