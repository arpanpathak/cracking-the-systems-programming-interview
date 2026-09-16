# 19. Workload State Machine {#state-machine}

*Source file: [`src/problems/state_machine.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/state_machine.rs). Test it with
`cargo test state_machine`.*

## Problem Statement

Model the lifecycle of a workload that an SDK exposes, so that the legal transitions are
stated once and an illegal transition is refused with a reason. Then model the errors the
same API returns, so that a caller can decide whether to retry without parsing a message.

## Designing a Solution

An enumeration rather than a status code. A status code makes the set of legal values a
convention that lives in a document; an enumeration makes it a type, and a `match` that
omits a case does not compile.

```text
              +--------------------------------------+
              |                                      |
              v                                      |
Pending ---> Provisioning ---> Running ---> Terminating ---> Terminated
   |             |               |              |
   +-------------+---------------+--------------+----> Failed
   |             |
   +<------------+        a failed workload may be retried
```

The same argument applies to the error type. A retry decision depends on facts, such as
the delay a server asked for and the status code it returned, so those facts are attached
to the variants that need them. A caller that matches on `RateLimited` has the delay in
hand.

## Implementation

<p class="listing"><span class="listing-label">Listing 19.1</span> The complete module, with its tests. <code>src/problems/state_machine.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/state_machine.rs">read the file on GitHub</a></p>

`can_transition_to` matches on the pair `(self, next)`, listing every permitted
transition as an alternative pattern. The whole rule set is one expression, and the
fall-through arm catches everything else, including a self-transition such as `Running`
to `Running`.

A self-transition is refused rather than treated as a no-op. A controller that reports a
transition it did not perform writes an audit log that cannot be trusted, and refusing
the case costs one line.

`is_retryable` uses `matches!` with a range pattern: a status in `500..=599` is
retryable, everything else is not. `NotFound` and `Unauthorized` are not retryable
because waiting does not change them: the resource still does not exist and the
credential is still expired.

`parse_gpu_count` trims the field, distinguishes an empty field from an unparseable one
in the message, and quotes the received text with `{raw:?}` so that trailing whitespace
is visible. The error variant carries a message; the variant itself is what a caller
matches on.

The repository's version of this function is named for the employer's product line, and
its error messages name the field after that product. This edition names the field
`gpuCount` and leaves the logic unchanged.

## Intuition

```text
state machine, over the whole table

from            to              result
Pending         Provisioning    Ok
Pending         Failed          Ok
Pending         Running         Err "cannot transition from Pending to Running"
Provisioning    Running         Ok
Provisioning    Failed          Ok
Provisioning    Terminated      Err
Running         Terminating     Ok
Running         Failed          Ok
Running         Running         Err
Terminating     Terminated      Ok
Terminating     Failed          Ok
Terminating     Running         Err
Terminated      Pending         Err
Terminated      Running         Err
Failed          Pending         Ok
Failed          Provisioning    Ok
Failed          Terminated      Err
```

```text
parse_gpu_count(" 4 ")   trim gives "4", parse succeeds       -> Ok(4)
parse_gpu_count("")      trim gives "", so the empty arm runs  -> Err(InvalidRequest)
parse_gpu_count("four")  parse fails, map_err replaces the error
                            with InvalidRequest quoting "four"    -> Err(InvalidRequest)
parse_gpu_count("-1")    parse::<u32> fails on the sign        -> Err(InvalidRequest)
```

## Time and Space Complexity

| Operation | Time | Space |
|---|---|---|
| `can_transition_to` | `O(1)` | none when permitted; one `String` when refused |
| `is_terminal` | `O(1)` | none |
| `summary` | `O(1)` | none; the return type is `&'static str` |
| `is_retryable` | `O(1)` | none |
| `user_message` | `O(1)` | one `String` allocation per call |
| `parse_gpu_count` | `O(digits)` | one `String` on the error path |

## Limitations

**`can_transition_to` returns `Result<(), String>`.** A refused transition is a value a
caller may want to match on, to log it, to count it, or to distinguish "illegal
transition" from "the workload no longer exists", and a `String` cannot be matched. It
also allocates on every refusal. The fix is a small error type with two fields, `from`
and `next`, both of which the state machine already has.

**`user_message` allocates for every call, including the two variants that need no
formatting.** `Unauthorized` returns a `to_string()` of a constant. A `Display`
implementation writes into the caller's buffer and allocates nothing.

**`is_retryable` treats any status in `500..=599` as retryable, and a `Server` variant
carrying a `4xx` status as not retryable.** The range test is doing double duty: it also
asserts that the `Server` variant holds a server-side status, and nothing enforces that at
construction time.

**The transition table is tested by example, not exhaustively.** The test checks four
transitions. There are thirty-six ordered pairs of six states, and the table permits
twelve of them. A test that loops over all pairs and compares each answer with a written
list would catch a missing or an extra pattern.

**`parse_gpu_count` reports a value that overflows `u32` as a parse failure.** `"4294967296"`
and `"four"` produce the same variant, so a caller cannot tell a malformed field from an
out-of-range one.

## Summary

- An enumeration makes the set of legal states a type rather than a convention: a
  `match` that omits a case does not compile, so adding a state is a compile error at
  every place that must handle it.
- The same argument governs the error type. A retry decision depends on facts such as a
  requested delay and a status code, so those facts are attached to the variants that
  carry them, and a caller that matches on the variant has them in hand.
- Every operation is constant time; the allocations are on the error and message paths
  only.
- The transition table is checked by example rather than exhaustively, so a new state
  compiles but is not necessarily tested.

## References

- The Rust Book, [Defining an enum](https://doc.rust-lang.org/book/ch06-01-defining-an-enum.html).
- Standard library, [`std::time::Duration`](https://doc.rust-lang.org/std/time/struct.Duration.html).
- Standard library, [`str::parse`](https://doc.rust-lang.org/std/primitive.str.html#method.parse).
