//! Longest substring without repeating characters.
//!
//! Sliding window with `HashMap<char, usize>`; the window start is monotonic.

use std::collections::HashMap;

pub fn length_of_longest_substring(s: &str) -> usize {
    let mut last_seen = HashMap::with_capacity(s.len());

    let (mut start, mut longest) = (0, 0);

    for (end, ch) in s.chars().enumerate() {
        if let Some(&previous) = last_seen.get(&ch) {
            start = start.max(previous + 1);
        }
        longest = longest.max(end - start + 1);
        last_seen.insert(ch, end);
    }

    longest
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn examples() {
        assert_eq!(length_of_longest_substring("abcabcbb"), 3);
        assert_eq!(length_of_longest_substring("bbbbb"), 1);
        assert_eq!(length_of_longest_substring("pwwkew"), 3);
        assert_eq!(length_of_longest_substring(""), 0);
    }
}
