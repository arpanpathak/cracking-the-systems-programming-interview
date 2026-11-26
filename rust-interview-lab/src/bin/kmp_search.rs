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
        // haystack[i] == needle[j], j + 1 == needle.len()
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
    let haystack = "aabaaabaaac";
    let needle = "aabaaac";

    println!("{:?}", kmp_search(haystack.as_bytes(), needle.as_bytes()));
}
