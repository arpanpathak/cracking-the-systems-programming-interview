use std::collections::{HashMap, HashSet};

fn first_repeating_char(s: &str) -> Option<(usize, char)> {
    let mut seen = HashSet::<char>::new();

    for (i, ch) in s.chars().enumerate() {
        if !seen.insert(ch) {
            return Some((i, ch));
        }
    }

    None
}

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
    // You can do s.chars().enumerate().find((_, ch) counts[ch] == 1)
}

fn main() {
    let s = "swiss";

    println!("first repeating:     {:?}", first_repeating_char(s));
    println!("first non-repeating: {:?}", first_non_repeating_char(s));
}

#[cfg(test)]
mod tests {
    use super::*;
    type TestCase = Option<(usize, char)>;
    // Use const or static for module-level arrays.
    // Types like &str are cleaner than String for test declarations.
    const CASES: [(&str, TestCase); 2] = [("abcdef", None), ("abcdea", Some((5, 'a')))];

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
}
