# 33. Reversing a String In Place {#reverse-string}

*Source file: [`src/bin/reverse_string.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/reverse_string.rs). Run it with
`cargo run --bin reverse_string`.*

## Problem Statement

Reverse the characters of a `String` without allocating a second one. The
constraint is what makes the problem interesting in Rust: a `String` is UTF-8, so
its bytes are not the same as its characters, and the safe API does not expose a
mutable byte buffer.

## Designing a Solution

The function works on bytes and swaps from the two ends inward. Two indices start
at the first and last byte, exchange their values, and move toward each other
until they meet. Each swap fixes two positions, so the loop runs half as many
times as there are bytes and requires no extra storage.

Reversing bytes only produces a valid `String` when every byte is a complete
character. For ASCII that is true, because one byte is one code point. For
general UTF-8 it is not: a multi-byte character read backwards is not a character.
The function therefore asserts that the input is ASCII before it touches the
buffer, and the assertion is the precondition that makes the unsafe access sound.

`String::as_mut_vec` is the only way to reach the bytes. It is `unsafe` because a
caller that leaves invalid UTF-8 in the buffer creates a `String` that violates
its own invariant, and every later operation on it is undefined. The `SAFETY`
comment states the obligation and the assertion that discharges it.

## Implementation

```rust

fn reverse_str(s: &mut String) {
    // SAFETY: s._as_mut_vec() is unsafe because it exposes the inner mutability to it's character buffer, and we must ensure
    // to leave valid UTF-8. We enforce ASCII only characters.
    assert!(s.is_ascii());
    let bytes = unsafe { s.as_mut_vec() };

    let (mut start, mut end) = (0, bytes.len() - 1);

    while start < end {
        bytes.swap(start, end);
        start+=1; end-=1;
    }
}

fn main() {
    for value in ["abcd", "abc", "a", "rust"] {
        let mut s = String::from(value);
        reverse_str(&mut s);
        println!("{value:>6} -> {s}");
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn an_even_length_string_is_reversed() {
        let mut s = String::from("abcd");
        reverse_str(&mut s);
        assert_eq!(s, "dcba");
    }

    #[test]
    fn an_odd_length_string_keeps_its_middle_byte() {
        let mut s = String::from("abc");
        reverse_str(&mut s);
        assert_eq!(s, "cba");
    }

    #[test]
    fn a_single_byte_is_unchanged() {
        let mut s = String::from("a");
        reverse_str(&mut s);
        assert_eq!(s, "a");
    }

    #[test]
    fn the_buffer_is_reused() {
        let mut s = String::from("abcd");
        let capacity = s.capacity();
        let address = s.as_ptr();
        reverse_str(&mut s);
        assert_eq!(s.capacity(), capacity);
        assert_eq!(s.as_ptr(), address);
    }

    #[test]
    fn reversing_twice_restores_the_string() {
        let mut s = String::from("interview");
        reverse_str(&mut s);
        reverse_str(&mut s);
        assert_eq!(s, "interview");
    }

    #[test]
    #[should_panic]
    fn non_ascii_input_panics() {
        let mut s = String::from("café");
        reverse_str(&mut s);
    }
}
```

The listing is the whole file. Taken in order:

- `assert!(s.is_ascii())` walks the string before the reversal. It is `O(n)`, which
  does not change the overall bound, and it runs before the unsafe block rather than
  inside it, so the panic leaves the string untouched.
- `bytes.swap(start, end)` is `slice::swap`, which exchanges two elements without
  moving either out. A manual exchange through a temporary would be three
  assignments on `u8`; `swap` states the intent and compiles to the same place.
- `main` reverses four strings and prints each result, so one run shows the even
  case, the odd case, the single byte, and a second four-letter word.
- The tests cover both parities, the single byte, the in-place property, and the
  round trip. `the_buffer_is_reused` reads the capacity and the address before and
  after and requires both to be unchanged, which is what separates this function
  from one that builds a new `String`. `non_ascii_input_panics` is marked
  `#[should_panic]`, so the assertion is checked rather than assumed.

## Intuition

Reverse `"abcd"`:

```text
before   a  b  c  d
         ^        ^
         start    end

swap 0,3 b  a  c  d
swap 1,2 b  c  a  d
         start >= end, stop
after    b  c  a  d
```

Reverse `"abc"`:

```text
before   a  b  c
swap 0,2 c  b  a
         start = 1, end = 1, stop
after    c  b  a
```

The middle byte of an odd-length string is never moved, which is why the loop
condition is `start < end` rather than `start <= end`.

The program prints:

```text
  abcd -> dcba
   abc -> cba
     a -> a
  rust -> tsur
```

The buffer is the same allocation in every line. Only the bytes inside it move.

## Time and Space Complexity

| Resource | Cost | Condition |
|---|---|---|
| Time | `O(n)` | `is_ascii` reads every byte; the swaps touch half of them |
| Space | `O(1)` | the swap is in place; no second buffer |
| Allocations | zero | the `String` keeps its buffer |

The reversal itself is `n / 2` swaps, and it is performed in place, so the
buffer's address and capacity do not change. The assertion adds a second pass over
the bytes, which is the price of the safe wrapper around the unsafe block.

## Limitations

**Non-ASCII input panics.** `assert!(s.is_ascii())` refuses any string containing
a byte above `0x7F`, which includes every accented letter and every emoji. A
general reversal needs to decode the string into characters, reverse the
characters, and rebuild the `String`, which allocates.

**Empty input panics.** With `bytes.len() == 0`, the expression `bytes.len() - 1`
underflows. In a debug build that panics with an arithmetic error; in a release
build it wraps and the following `swap` is out of bounds. The function needs a
check for an empty string, and it does not have one, so the tests do not cover the
empty case either.

**The `unsafe` block is sound only because of the assertion above it.** Removing
the assertion makes the function undefined behaviour on any non-ASCII input. The
`SAFETY` comment is the record of that dependency, and a future edit that drops
the check has to drop the unsafe approach as well.

**The function reverses bytes, not grapheme clusters.** For ASCII the two are the
same. For text that passes the assertion they cannot differ, but a reader should
not carry the assumption to a general string.

**The largest test input is nine bytes.** The tests establish the two parities and
the round trip. A larger input, or one built to exercise the exact midpoint of an
even-length string, would test the loop bound more of the way.

## Summary

- Byte reversal is `O(n)` time and `O(1)` space, and only the ASCII precondition
  makes it a valid `String` transformation.
- `as_mut_vec` is `unsafe` because it can leave the buffer invalid; the assertion
  ahead of it is what discharges the obligation recorded in the `SAFETY` comment.
- The loop runs `n / 2` times and leaves the middle byte of an odd-length string
  in place.
- The program reverses four strings and prints them, and the tests check both
  parities, the single byte, the unchanged allocation, and the round trip.
- Empty and non-ASCII inputs are not handled: the first panics on the subtraction,
  and the second is refused by the assertion.

## References

- Standard library, [`String::as_mut_vec`](https://doc.rust-lang.org/std/string/struct.String.html#method.as_mut_vec).
- Standard library, [`str::is_ascii`](https://doc.rust-lang.org/std/primitive.str.html#method.is_ascii).
- Standard library, [`slice::swap`](https://doc.rust-lang.org/std/primitive.slice.html#method.swap).
- The Rustonomicon, [Working with unsafe](https://doc.rust-lang.org/nomicon/working-with-unsafe.html).
