# 25. Shadowing and Mutation {#shadowing}

*Source file: [`src/bin/shadowing.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/shadowing.rs). Run it with `cargo run --bin shadowing`.*

## Problem Statement

Two constructs look similar in source and behave differently: giving a name a new
value with `let`, and changing the value a binding already holds.

## Designing a Solution

A `let` introduces a binding. Writing a second `let` with the same name introduces
a *second* binding that shadows the first; the first is still there, still owns
whatever it owns, and is no longer reachable by that name. Because a new binding
can have a new type, shadowing is the mechanism for converting a value.

Mutation is a different operation. `let mut count = 0` creates one binding whose
value may be replaced through it, and `count += 1` writes to that place. The type
is fixed at the declaration, and no new binding appears.

```text
shadowing                          mutation

let value: u32 = 7;               let mut count = 0;
  binding A: u32                    binding: i32, mutable

let value = value.to_string();    count += 1;
  binding B: String                 the same binding, new value
  A is unreachable by name
  A is dropped at the end of       count += 1;
  its scope                         again

let value = value.len();          count
  binding C: usize                one binding in the whole block
  B is unreachable by name
```

The two mechanisms solve different problems. Shadowing changes the type, and it
makes every later reader of the name see the new one. Mutation keeps the type and
the binding, which is what a counter or an accumulator needs.

## Implementation

<p class="listing"><span class="listing-label">Listing 25.1</span> The complete program, with its tests. <code>src/bin/shadowing.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/shadowing.rs">read the file on GitHub</a></p>

`let value = value.to_string()` uses the old `value` on the right and introduces
the new binding on the left. The order is what makes the idiom legal: the right
side is evaluated with the old binding in scope, and the new binding takes effect
after the statement.

`let value = value.len()` then shadows the `String`, and the value becomes `1`
because `"7"` is one character. The chain of three bindings ends with a `usize`.

The conversion idiom in the header comment is the reason the feature matters in
application code:

```rust
let raw = request.header("X-Device-Count")?;
let raw: u64 = raw.parse()?;
```

The second `let` reuses the name for the converted value. There is no chance of
using the unparsed text afterwards, because the name now refers to the parsed
number. A `mut` version would need two names or an early `drop`, and neither is as
clear about which value is in play.

`demonstrate_mutation` shows the other side: one binding, marked `mut`, whose value
changes three times. The loop's counter has one name and one type, which is exactly
what shadowing cannot express, because each `let` in a loop body would create a
fresh binding that dies at the end of the iteration.

## Intuition

```text
demonstrate_shadowing

statement                        bindings in scope              log so far
let value: u32 = 7               value: u32 = 7
let mut log = format!(...)       value: u32 = 7                 "integer: 7"
                                 log: String
let value = value.to_string()    value: String = "7"            "integer: 7\nstring: 7"
                                 (the u32 binding is unreachable)
let value = value.len()          value: usize = 1               "integer: 7\nstring: 7\nusize: 1"
                                 (the String binding is unreachable)
return log

the function returns "integer: 7\nstring: 7\nusize: 1", and the test asserts on
the three lines separately
```

```text
demonstrate_mutation

statement        bindings              log
let mut count=0  count: i32 = 0
let mut log      count: i32 = 0        "mut count:"
                 log: String
iteration 1      count = 1             "mut count: 1"
iteration 2      count = 2             "mut count: 1 2"
iteration 3      count = 3             "mut count: 1 2 3"

one binding for count, changed three times
```

## Time and Space Complexity

| Resource | Cost |
|---|---|
| Shadowing | no run-time cost; the old binding is dropped at the end of its scope, if it owns anything |
| Mutation | no run-time cost beyond the write itself |
| `format!` | one `String` allocation per call |

The only allocation in either function is the log, which is built with `format!`
and `push_str`. The conversion `value.to_string()` also allocates a `String`, and
it is freed at the end of `demonstrate_shadowing` when the last binding to it goes
out of scope.

## Limitations

**The comment says the old binding is "gone"; the value is not necessarily freed.**
Shadowing hides a name. The original binding's storage lasts until the end of its
scope, and for a type with a destructor the resource is released at the end of the
scope, not at the shadowing `let`. For `u32` and `String` in this file the
distinction has no observable effect; for a file handle or a lock guard it does,
because the guard stays alive until the end of the block. The comment's wording is
more absolute than the rule.

**Shadowing hides mistakes as well as values.** A `let` that accidentally reuses a
name produces no warning, and the compiler's unused-variable lint may not fire
because the first binding was used before it was shadowed. The mechanism is
powerful and it is not checked.

**The file has no test for the shadowed value being unreachable.** The tests assert
on the log's contents, which proves that each binding was used. Nothing demonstrates
the *lifetime* point, that an owned resource in a shadowed binding is released at
the end of the scope, not at the shadowing statement.

**Two `demonstrate_*` functions return a `String` built by `format!`.** A version
that took `&mut String` and appended to the caller's buffer would allocate less,
and the tests would be the same. For a demonstration the difference is irrelevant;
it is the kind of allocation that shows up in a profile.

## Summary

- `let` introduces a binding and `mut` allows a place to be written. The two are
  independent.
- The conversion idiom is the reason shadowing appears in ordinary code. Parsing
  input and reusing the name avoids inventing a second name for the same value.
- Shadowing does not destroy the shadowed binding. Its storage lasts until the end
  of the scope, so a value with a destructor is released at the end of the block
  rather than at the shadowing statement.
- A `mut` binding fixes the type, which is why a counter uses `mut` and a
  conversion uses `let`.
- Shadowing hides mistakes as well as values: a `let` that reuses a name by
  accident produces no warning.

## References

- The Rust Book, [Shadowing](https://doc.rust-lang.org/book/ch03-01-variables-and-mutability.html#shadowing).
- The Rust Book, [Variables and mutability](https://doc.rust-lang.org/book/ch03-01-variables-and-mutability.html).
- The Rust Reference, [Names, scopes, and shadowing](https://doc.rust-lang.org/reference/names.html).
