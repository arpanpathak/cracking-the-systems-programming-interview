//! The first character that repeats, and the first character that never repeats.
//!
//! Both return the character with its index. The repeating one needs a single pass
//! with a set; the non-repeating one needs the full counts first, so it takes two.

use std::collections::{HashMap, HashSet};

/// The first character seen a second time, at the index of that second sighting.
fn first_repeating_char(s: &str) -> Option<(usize, char)> {
    let mut seen = HashSet::<char>::new();

    for (i, ch) in s.chars().enumerate() {
        if !seen.insert(ch) {
            return Some((i, ch));
        }
    }

    None
}

/// The first character that appears exactly once in the whole string.
fn first_non_repeating_char(s: &str) -> Option<(usize, char)> {
    let mut counts = HashMap::<char, usize>::new();
    for ch in s.chars() {
        *counts.entry(ch).or_default() += 1;
    }

    for (i, ch) in s.chars().enumerate() {
        if counts[&ch] == 1 {
            return Some((i, ch));
        }
    }

    None
    // You can do s.chars().enumerate().find(|(_, ch)| counts[ch] == 1)
}

fn main() {
    for input in ["abcdea", "swiss", "aabb"] {
        let repeating = first_repeating_char(input);
        let non_repeating = first_non_repeating_char(input);

        println!("{input:?}: first repeating {repeating:?}, first non-repeating {non_repeating:?}");
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    type TestCase = Option<(usize, char)>;
    // Use const or static for module-level arrays.
    // Types like &str are cleaner than String for test declarations.
    const CASES: [(&str, TestCase); 2] = [("abcdef", None), ("abcdea", Some((5, 'a')))];

    const NON_REPEATING_CASES: [(&str, TestCase); 4] = [
        ("abcdea", Some((1, 'b'))),
        ("swiss", Some((1, 'w'))),
        ("aabb", None),
        ("", None),
    ];

    #[test]
    fn should_validate() {
        for (input, expected) in CASES {
            assert_eq!(
                first_repeating_char(input),
                expected,
                "Failed on input: {}",
                input
            );
        }
    }

    #[test]
    fn finds_first_non_repeating() {
        for (input, expected) in NON_REPEATING_CASES {
            assert_eq!(
                first_non_repeating_char(input),
                expected,
                "Failed on input: {input}"
            );
        }
    }
}
