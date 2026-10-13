//! Command typeahead suggests searches for what a user has typed so far. It
//! keeps how often each search was made and returns the most frequent
//! searches that start with the typed letters.
//!
//! Run it from code/ with:
//!
//!     cargo run -p typeahead

// ANCHOR: imports
use std::cmp::Reverse;
use std::collections::BTreeMap;
// ANCHOR_END: imports

// ANCHOR: index
/// Every search and the number of times it was made, sorted by text. All
/// searches with the same first letters are next to each other.
struct Index {
    counts: BTreeMap<String, u32>,
}

impl Index {
    /// The `limit` most frequent searches that start with `prefix`.
    fn suggest(&self, prefix: &str, limit: usize) -> Vec<(&str, u32)> {
        let mut matches: Vec<(&str, u32)> = self
            .counts
            .range(prefix.to_owned()..)
            .take_while(|entry| entry.0.starts_with(prefix))
            .map(|(text, &count)| (text.as_str(), count))
            .collect();

        matches.sort_by_key(|found| Reverse(found.1));
        matches.truncate(limit);

        matches
    }
}
// ANCHOR_END: index

// ANCHOR: main
fn main() {
    let searches = [
        ("kafka", 900),
        ("kafka vs rabbitmq", 300),
        ("kayak", 450),
        ("karaoke near me", 800),
        ("key value store", 700),
        ("keyboard", 650),
        ("kubernetes", 950),
        ("kubernetes ingress", 400),
        ("rate limiter", 500),
        ("raft", 600),
    ];
    let index = Index {
        counts: searches
            .iter()
            .map(|&(text, count)| (text.to_owned(), count))
            .collect(),
    };

    for typed in ["k", "ka", "kaf", "ke", "ra", "x"] {
        let suggestions: Vec<String> = index
            .suggest(typed, 3)
            .iter()
            .map(|(text, count)| format!("{text} ({count})"))
            .collect();

        let shown = if suggestions.is_empty() {
            "no suggestion".to_owned()
        } else {
            suggestions.join(", ")
        };

        println!("{typed:4} -> {shown}");
    }
}
// ANCHOR_END: main
