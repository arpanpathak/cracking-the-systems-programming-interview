//! KMP substring search driven by a `match` on (bytes equal, at the needle's end, j).
//!
//! `lps[j]` is the length of the longest proper prefix of `needle[..=j]` that is also
//! a suffix of it. On a mismatch, `j` falls back to `lps[j - 1]` instead of restarting,
//! so `i` never moves backwards and the search is O(n + m).

fn build_lps(needle: &[u8]) -> Vec<usize> {
    let mut lps = vec![0usize; needle.len()];
    let (mut len, mut j) = (0usize, 1usize);

    while j < needle.len() {
        match (needle[j] == needle[len], len) {
            (true, _) => {
                len += 1;
                lps[j] = len;
                j += 1;
            }
            (false, 0) => {
                lps[j] = 0;
                j += 1;
            }
            (false, _) => {
                len = lps[len - 1];
            }
        }
    }
    lps
}

fn kmp_search(haystack: &[u8], needle: &[u8]) -> Option<usize> {
    if needle.is_empty() {
        return Some(0);
    }

    let lps = build_lps(needle);
    let (mut i, mut j) = (0usize, 0usize);

    while i < haystack.len() {
        // (haystack[i] == needle[j], needle[j] is its last byte, j)
        match (haystack[i] == needle[j], j + 1 == needle.len(), j) {
            // haystack[i] is the needle's last byte, so the match began j bytes earlier.
            (true, true, _) => return Some(i - j),
            (true, false, _) => {
                i += 1;
                j += 1; // Keep advancing...
            }
            (false, _, 0) => i += 1,
            (false, _, _) => j = lps[j - 1],
        }
    }

    None
}

fn main() {
    let cases = [
        ("sadbutsad", "sad"),
        ("hello world", "world"),
        ("aabaaabaaac", "aabaaac"),
        ("leetcode", "leeto"),
    ];

    for (haystack, needle) in cases {
        let found = kmp_search(haystack.as_bytes(), needle.as_bytes());
        println!("kmp_search({haystack:?}, {needle:?}) = {found:?}");
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const CASES: [(&str, &str); 6] = [
        ("hello world", "world"),
        ("abcabd", "abd"),
        ("aaab", "aab"),
        ("aabaaabaaac", "aabaaac"),
        ("abc", "zz"),
        ("abc", ""),
    ];

    #[test]
    fn matches_str_find() {
        for (haystack, needle) in CASES {
            assert_eq!(
                kmp_search(haystack.as_bytes(), needle.as_bytes()),
                haystack.find(needle),
                "haystack {haystack:?}, needle {needle:?}"
            );
        }
    }
}
