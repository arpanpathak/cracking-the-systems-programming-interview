# 2. Valid Parentheses {#valid-parentheses}

*Source file: [`src/problems/valid_parentheses.rs`](../../rust-interview-lab/src/problems/valid_parentheses.rs). Test it with
`cargo test valid_parentheses`.*

## Problem Statement

Given a string built from the six delimiter characters `()[]{}`, decide whether
every opening delimiter is eventually closed by its own kind, with the pairs
properly nested. Any other character makes the string invalid.

The problem is the smallest useful model of a task that appears throughout
programming: deciding whether a sequence is well formed. A text editor does it to
highlight matching braces, a configuration loader does it before parsing a
document, and a compiler does it before it can build an expression tree. The rules
are what make a stack the natural tool, and the exercise is the shortest route to
seeing why a counter is not enough.

## Designing a Solution

Two conditions have to hold when the scan reaches the end of the string. No closing
delimiter may appear when the delimiter it has to match is not the most recent
unmatched one, and nothing may remain unmatched.

The second condition is easy to satisfy with a counter, and the first is not.
Consider `([)]`. Every kind of delimiter appears in matching quantities, so a count
of openings and closings reports balance, and the string is nevertheless invalid:
the `)` closes the `(` while the `[` is still open. Correctness depends on the
*order* of the unmatched openings rather than only on their number, and a value that
remembers an ordered sequence of pending openings is exactly a stack.

The stack holds the opening delimiters whose counterpart has not yet been seen, with
the most recently opened on top. That is the delimiter a closing character has to match, so
the scan maintains the invariant

> the stack contains the unmatched opening delimiters, in the order they appeared,

after every character. An opening delimiter is pushed. A closing delimiter pops the
top and checks its kind. If the stack is empty when a closing delimiter arrives,
there was nothing for it to close, and the string is invalid at that point. When the
scan finishes, the stack has to be empty, because anything left in it is an opening
delimiter with no matching opener.

The machine this scan describes has a name. It is a pushdown automaton, the weakest
kind of machine that recognises a language in which nesting has to be matched. Its
counterpart is a finite automaton, which has no stack, and that is why a regular
expression cannot decide this question: no finite pattern can count arbitrarily deep
nesting.

## Implementation

```rust
//! Valid Parentheses: classic stack problem with idiomatic pattern matching.
//!
pub fn is_valid(s: &str) -> bool {
    use std::collections::HashMap;

    let mut stack = Vec::with_capacity(s.len());

    // Because manually adding if else is not an extensible solution.
    let expected = HashMap::from([
        (')', '('), 
        ('}', '{'), 
        (']', '['),
        // You can write whatever grammar you'd like, such as '<', '|', '$'....
    ]);

    for ch in s.chars() {
        // Look at the tasteful thickness of "পূর্ণাঙ্গ বিন্যাস মিলকরণ", We love Unicode!
        match ch {
            '(' | '[' | '{' => stack.push(ch),
            // Rust compiler will throw error for not handling all the possible character ranges.
            // So ask it to chill with an if guard.....I've got you Sir!! Thank 
            _ => { if stack.pop().as_ref() != expected.get(&ch) { return false; } }
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

The capacity hint is `s.len()`, the byte length of the string. A character count is
never larger than a byte count, so the hint is an upper bound on the entries the
loop can push, and the vector never grows while the scan runs. For text outside
ASCII the hint over-allocates by the ratio between the two lengths: a few bytes of
waste measured against the cost of a reallocation in the worst case.

`expected` is a map from each closing delimiter to the opening delimiter it must
match. Building it once per call keeps the pairing in one structure rather than in
one `match` arm per delimiter; adding a pair to the grammar is a longer array
rather than a longer `match`.

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

`stack.pop()` returns `Option<char>`, and `.as_ref()` turns it into `Option<&char>`
so that it can be compared with `expected.get(&ch)`, which has the same type. The
guard returns `false` whenever the two options differ, which covers a mismatched
delimiter and a closing delimiter on an empty stack. The next section shows the case
it does not cover.

The function ends with `stack.is_empty()`. Without that expression, a string of
opening delimiters alone would be accepted and `"("` would be reported as valid.

## Intuition

```text
input: {[()]}

char  stack before   pop result   stack after   value returned
 {      []            -            [{]
 [      [{]           -            [{[]
 (      [{[]          -            [{[()]
 )      [{[()]        Some('(')    [{[]
 ]      [{[ ]         Some('[')    [{
 }      [{]           Some('{')    []
end                                                       true
```

```text
input: ([)]

char  stack before   pop result   stack after   value returned
 (      []            -            [(]
 [      [(]           -            [([]
 )      [([]          Some('[')    [(]           -
 ]      [(]           Some('(')    []            false

The delimiters appear in matching quantities and are nested in the wrong order, so
the scan reports the failure at the final character.
```

```text
input: )

char  stack before   pop result   stack after   value returned
 )      []            None          []            false

A closing delimiter with an empty stack ends the scan immediately.
```

## Time and Space Complexity

| Resource | Cost | Condition |
|---|---|---|
| Time | `O(n)` | one push or one pop per character, each constant |
| Space | `O(n)` | for a string of opening delimiters only |
| Space on typical input | `O(d)` | `d` is the greatest nesting depth reached |

The worst case is a string such as `"(((("`, where the stack grows with the input.
The typical case is far smaller, because the stack holds only the openings that have
not yet been closed, which is the nesting depth at the cursor rather than the length
of the string.

The scan is iterative, so nesting depth is bounded by available memory rather than by
the thread's stack. A recursive version of the same algorithm would exhaust the stack
on a deeply nested string, which means a program that validates a document supplied
by a user would have a denial-of-service condition. This is the one place in the book
where an iterative formulation is a robustness requirement rather than a preference,
and it costs nothing: the loop is as short as the recursion would be.

## Limitations

**A character outside the alphabet is accepted when the stack is empty.** The
catch-all arm compares two `Option<&char>` values. For a character that is not one
of the six delimiters, `expected.get(&ch)` is `None`. If the stack is also empty,
`stack.pop().as_ref()` is `None` as well, so the two are equal and the scan
continues instead of rejecting the character. `is_valid("abc")` and `is_valid("()x")`
therefore return `true`. The defect does not appear when the stack is non-empty,
because a popped `Some(...)` can never equal `None`, so the same character is
rejected after an opening delimiter. No test in the file covers an input of this
kind, which is why the behaviour is easy to miss.

The function returns `bool`, so it cannot say where the failure occurred. A parser
that reports "unmatched `(` at offset 12" needs the position. A version returning
`Result<(), usize>` carries it with one change: iterate with `enumerate` and return
the index in place of `false`.

The capacity hint is measured in bytes while the stack stores characters. For a
string of three-byte characters the allocation is three times larger than the
characters can justify, and the vector's length still never exceeds the character
count. The bound is safe and the allocation is loose.

The stack element type is `char`, one Unicode scalar value per entry. The algorithm
does not need that. A version that reports positions would push the index of the
opening character instead, and the comparisons would be against indices rather than
against characters.

## Summary

- The invariant is that the stack holds the unmatched openings in order, with the
  most recent on top. Every branch of the loop preserves it, and the final
  `is_empty` is the statement that nothing was left unmatched.
- Counting delimiters is not sufficient. `([)]` has matching counts and no valid
  parse, which is what the stack is for.
- The scan rejects a closing delimiter whose opener is not on top, a closing
  delimiter with an empty stack, and a non-empty stack at the end.
- A character outside the alphabet is rejected only while the stack is non-empty.
  With an empty stack it is accepted, which is the defect described in Limitations.
- The scan is a pushdown automaton, which is why a regular expression cannot decide
  the question.

## References

- Standard library, [`Vec::pop`](https://doc.rust-lang.org/std/vec/struct.Vec.html#method.pop), on the `Option` it returns.
- Standard library, [`str::chars`](https://doc.rust-lang.org/std/primitive.str.html#method.chars), on iterating scalar values rather than bytes.
- Michael Sipser, *Introduction to the Theory of Computation*, 3rd edition, Cengage Learning, 2012, Chapter 2, on pushdown automata and the limits of finite automata.
