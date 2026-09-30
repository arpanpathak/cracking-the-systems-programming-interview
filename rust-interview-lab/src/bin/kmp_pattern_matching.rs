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
        let (mut left, mut right) = (0, 0); // left walks needle, right walks haystack

        while right < haystack.len() {
            if haystack[right] == needle[left] {
                left += 1;
                right += 1;
            } else if left > 0 {
                left = lps[left - 1];
            }
            // fall back
            else {
                right += 1;
            } // mismatch at the start

            if left == needle.len() {
                return (right - left) as i32;
            } // pattern found
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
                right += 1;
            } // lps[right] stays 0
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
