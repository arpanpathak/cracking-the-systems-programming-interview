# 4. Longest Substring Without Repeating Characters {#sliding-window}

*Source file: [`src/problems/sliding_window.rs`](../../rust-interview-lab/src/problems/sliding_window.rs). Test it with
`cargo test sliding_window`.*

## Problem Statement

Given a text, return the length of the longest contiguous substring that contains
no repeated character. The answer is a length, not the substring, which lets the
implementation discard the content of the window and keep only its start.

## Designing a Solution

Maintain a window `[start, end)` over the characters and a map from each character
to the last index where it was seen. Extend the window by one character at a time.
If the new character was last seen at an index at or after `start`, the window must
begin after that index.

```text
"pwwkew"

end  char  window       last_seen          longest
 0    p    [p]          {p:0}              1
 1    w    [pw]         {p:0, w:1}         2
 2    w    [w]          start = 1 + 1 = 2  2
 3    k    [wk]         {w:2, k:3}         2
 4    e    [wke]        {e:4}              3
 5    w    [ew]         start = 2 + 1 = 3  3
```

The line that carries the algorithm is `start = start.max(previous + 1)`. The
`max` is not defensive coding. A character may have been seen, left the window,
and been seen again; in that case its recorded index is *before* `start`, and
assigning `previous + 1` unconditionally would move the window backwards and
re-scan characters that have already been counted. `start` is monotonic, and that
monotonicity is what makes the scan linear.

## Implementation

```rust
//! Longest substring without repeating characters.
//!
//! Sliding window with `HashMap<char, usize>`; the window start is monotonic.

use std::collections::HashMap;

pub fn length_of_longest_substring(s: &str) -> usize {
    let mut last_seen = HashMap::with_capacity(s.len());

    // it's magic compiler is able to deduce the datatype as usize based on its first usage, which is kinda cool, isn't it ?
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
```

`for (end, ch) in s.chars().enumerate()` iterates over Unicode scalar values, not
bytes. `end` is therefore a character index, and `end - start + 1` is a length in
characters. A byte-oriented version would report a different number for any text
outside ASCII.

`if let Some(&previous) = last_seen.get(&ch)` copies the index out of the map, so
the borrow ends at the end of the `if let` and the `insert` below is allowed.

## Intuition

A case where the repeat has left the window, which is the case the `max` exists
for:

```text
"abba"

end  char  previous   start before   start after   window    longest
 0    a     none       0              0             [a]       1
 1    b     none       0              0             [ab]      2
 2    b     Some(1)    0              2             [b]       2
 3    a     Some(0)    2              2             [ba]      2

At end = 3 the recorded index of 'a' is 0, which is before the window start of 2.
`start.max(0 + 1)` keeps start at 2. Assigning 0 + 1 instead would set start to 1
and count "abb" as a window.
```

## Time and Space Complexity

| Resource | Cost | Condition |
|---|---|---|
| Time | `O(n)` | one step per character; `start` never decreases |
| Space | `O(min(n, k))` | `k` distinct characters occur in the text |

## Limitations

**The map is sized by a byte count.** `HashMap::with_capacity(s.len())` uses the
byte length as the capacity hint, which over-allocates for multi-byte text. The
hint is safe because a byte count bounds a character count.

**The answer is a length, and the substring is discarded.** A caller that needs
the text of the longest window must record `start` alongside `longest` and slice
the original at the end. That change is two lines and is not in the file.

**Non-ASCII text is measured in characters, not in grapheme clusters.** A
combining sequence such as `e` followed by a combining acute accent is two scalar
values, so the function counts it as two characters. A user-facing length would
need grapheme segmentation, which the standard library does not provide.

**The map keeps an entry per distinct character ever seen.** Entries for
characters that have left the window are not removed, so the space bound is over
the whole text rather than over the current window. An implementation that
removes entries on eviction would bound memory by the window instead.

## Summary

- The `max` on the first match is required for correctness. Without it the
  function fails on `"abba"`.
- `start` is monotonic, which is what reduces the scan to a single pass with no
  backtracking and an `O(n)` bound.
- The space bound is `O(min(n, alphabet))` rather than `O(n)`. For `char` keys the
  alphabet cannot exceed 1,112,064, the number of Unicode scalar values.
- Lengths are counted in scalar values, so a combining sequence counts as two. A
  user-visible length would need grapheme segmentation, which the standard library
  does not provide.

## References

- Standard library, [`str::chars`](https://doc.rust-lang.org/std/primitive.str.html#method.chars).
- Standard library, [`Iterator::enumerate`](https://doc.rust-lang.org/std/iter/trait.Iterator.html#method.enumerate).
- Standard library, [`Ord::max`](https://doc.rust-lang.org/std/cmp/trait.Ord.html#method.max).
