struct Solution {}
impl Solution {
    /// @param haystack the string to search in
    /// @param needle   the pattern to find
    /// @return         first index of needle in haystack, or -1
    pub fn str_str(haystack: String, needle: String) -> i32 {
        let (haystack, needle) = (haystack.as_bytes(), needle.as_bytes());
        if needle.is_empty() {
            return 0;
        }

        let lps = Self::build_lps(needle);
        // left walks the needle, and right walks the haystack.
        let (mut left, mut right) = (0, 0);

        while right < haystack.len() {
            if haystack[right] == needle[left] {
                left += 1;
                right += 1;
            } else if left > 0 {
                // Fall back, keeping the characters that still match.
                left = lps[left - 1];
            } else {
                // A mismatch at the start of the needle.
                right += 1;
            }

            if left == needle.len() {
                // The whole needle matched.
                return (right - left) as i32;
            }
        }
        -1
    }

    // LPS: longest proper prefix of needle[0..=right] that is also a suffix
    fn build_lps(needle: &[u8]) -> Vec<usize> {
        let mut lps = vec![0; needle.len()];
        let (mut left, mut right) = (0, 1);

        while right < needle.len() {
            if needle[right] == needle[left] {
                left += 1;
                lps[right] = left;
                right += 1;
            } else if left > 0 {
                left = lps[left - 1];
            } else {
                // lps[right] stays 0.
                right += 1;
            }
        }
        lps
    }
}

fn main() {
    let cases = [
        ("sadbutsad", "sad"),
        ("leetcode", "leeto"),
        ("aabaaabaaac", "aabaaac"),
        ("hello", ""),
    ];

    for (haystack, needle) in cases {
        let result = Solution::str_str(haystack.to_string(), needle.to_string());
        println!("str_str({haystack:?}, {needle:?}) = {result}\n");
    }
}
