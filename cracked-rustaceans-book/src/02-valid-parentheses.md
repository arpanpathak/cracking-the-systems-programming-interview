# 2. Valid Parentheses {#valid-parentheses}

*Source file: [`src/problems/valid_parentheses.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/valid_parentheses.rs). Test it with
`cargo test valid_parentheses`.*

## Problem Statement

Given a string built from the six delimiter characters `()[]{}`, decide whether every
opening delimiter is closed by its own kind, with the pairs properly nested. Any
other character makes the string invalid.

## Designing a Solution

Two conditions must hold. A closing delimiter may appear only when the delimiter it
must match is the most recent unmatched opening, and nothing may remain unmatched at
the end of the scan.

A counter of openings and closings satisfies the second condition and not the first.
In `([)]` every kind of delimiter appears in matching quantity, so a counter reports
balance, and the string is invalid because `)` closes `(` while `[` is still open.
Correctness depends on the order of the unmatched openings, and an ordered sequence
of pending openings is a stack.

The stack holds the opening delimiters whose counterpart has not been seen, with the
most recently opened on top. That entry is the delimiter a closing character must
match. An opening delimiter is pushed. A closing delimiter pops the top and compares
its kind. A closing delimiter that arrives at an empty stack has nothing to close, and
the string is invalid at that point. When the scan finishes the stack must be empty,
because anything left in it is an opening delimiter with no counterpart.

The scan is a pushdown automaton, the weakest machine that recognises a language with
matched nesting. A finite automaton has no stack and cannot decide the question, so no
regular expression can match arbitrarily deep nesting.

## Implementation

```rust
//! Valid Parentheses: classic stack problem with idiomatic pattern matching.
//!
pub fn is_valid(s: &str) -> bool {
    use std::collections::HashMap;

    let mut stack = Vec::with_capacity(s.len());

    // Maps each closing delimiter to the opening delimiter it must match.
    let expected = HashMap::from([(')', '('), ('}', '{'), (']', '[')]);

    for ch in s.chars() {
        match ch {
            '(' | '[' | '{' => stack.push(ch),
            // Every other character, including one outside the six delimiters,
            // must close the top of the stack.
            _ => {
                if stack.pop().as_ref() != expected.get(&ch) {
                    return false;
                }
            }
        }
    }

    stack.is_empty()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn valid_cases() {
        assert!(is_valid("()"));
        assert!(is_valid("()[]{}"));
        assert!(is_valid("{[()]}"));
    }

    #[test]
    fn invalid_cases() {
        assert!(!is_valid("(]"));
        assert!(!is_valid("([)]"));
        assert!(!is_valid("("));
        assert!(!is_valid(")"));
        assert!(!is_valid("(("));
    }
}
```

The capacity hint is `s.len()`, the byte length of the string. A character count never
exceeds a byte count, so the hint bounds the number of pushes and the vector does not
grow during the scan. For text outside ASCII the hint over-allocates.

`expected` maps each closing delimiter to the opening delimiter it must match. The
pairing sits in one structure rather than in one `match` arm per delimiter, so adding
a pair to the grammar extends the array rather than the `match`.

The loop has two arms. The first pushes every opening delimiter. The second is the
catch-all arm the compiler requires, and it performs the comparison for every other
character:

```rust
_ => {
    if stack.pop().as_ref() != expected.get(&ch) {
        return false;
    }
}
```

`stack.pop()` returns `Option<char>`, and `.as_ref()` turns it into `Option<&char>` for
comparison with `expected.get(&ch)`, which has the same type. The guard returns `false`
whenever the two options differ, which covers a mismatched delimiter and a closing
delimiter on an empty stack. The next section states the case it does not cover.

`stack.is_empty()` at the end rejects a string of opening delimiters alone. Without it,
`"("` would be reported as valid.

## Intuition

```text
input: {[()]}

char  stack before   pop result   stack after   value returned
 {      []            -            [{]
 [      [{]           -            [{[]
 (      [{[]          -            [{[()]
 )      [{[()]        Some('(')    [{[]           -
 ]      [{[ ]         Some('[')    [{
 }      [{]           Some('{')    []
end                                                       true
```

```text
input: ([)]

char  stack before   pop result   stack after   value returned
 (      []            -            [(]
 [      [(]           -            [([]          -
 )      [([]          Some('[')    [(]           -
 ]      [(]           Some('(')    []            false

The delimiters appear in matching quantities and in the wrong nesting order, so the
scan reports the failure at the final character.
```

```text
input: )

char  stack before   pop result   stack after   value returned
 )      []            None          []            false
```

## Time and Space Complexity

| Resource | Cost | Condition |
|---|---|---|
| Time | `O(n)` | one push or one pop per character, each constant |
| Space | `O(n)` | for a string of opening delimiters only |
| Space on typical input | `O(d)` | `d` is the greatest nesting depth reached |

The worst case is a string such as `"(((("`, where the stack grows with the input. The
typical case is smaller, because the stack holds only the openings that have not been
closed, which is the nesting depth at the cursor rather than the length of the string.

The scan is iterative, so nesting depth is bounded by available memory rather than by
the thread's stack. A recursive formulation would exhaust the stack on a deeply nested
string, which is a denial-of-service condition in a program that validates a document
supplied by a user.

## Limitations

**A character outside the alphabet is accepted when the stack is empty.** The catch-all
arm compares two `Option<&char>` values. For a character that is not one of the six
delimiters, `expected.get(&ch)` is `None`. If the stack is also empty,
`stack.pop().as_ref()` is `None`, the two are equal, and the scan continues instead of
rejecting the character. `is_valid("abc")` and `is_valid("()x")` therefore return
`true`. The case does not arise when the stack is non-empty, because a popped
`Some(...)` never equals `None`, so the same character is rejected after an opening
delimiter. No test in the file covers an input of this kind.

The function returns `bool`, so it cannot report where the failure occurred. A parser
that reports "unmatched `(` at offset 12" needs the position. A version returning
`Result<(), usize>` carries it with one change: iterate with `enumerate` and return the
index in place of `false`.

The capacity hint is measured in bytes while the stack stores characters. For a string
of three-byte characters the allocation is three times larger than the characters can
justify, and the vector's length still never exceeds the character count.

The stack element type is `char`, one Unicode scalar value per entry. The algorithm does
not require that. A version that reports positions would push the index of the opening
character, and the comparisons would be between indices.

## References

- Standard library, [`Vec::pop`](https://doc.rust-lang.org/std/vec/struct.Vec.html#method.pop), on the `Option` it returns.
- Standard library, [`str::chars`](https://doc.rust-lang.org/std/primitive.str.html#method.chars), on iterating scalar values rather than bytes.
- Michael Sipser, *Introduction to the Theory of Computation*, 3rd edition, Cengage Learning, 2012, Chapter 2, on pushdown automata and the limits of finite automata.
