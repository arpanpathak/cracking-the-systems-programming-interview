# 19. Workload State Machine {#state-machine}

*Source file: [`src/problems/state_machine.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/state_machine.rs). Test it with
`cargo test state_machine`.*

## Problem Statement

Model the lifecycle of a workload that an SDK exposes, so that the legal
transitions are stated once and an illegal transition is refused with a reason.
Then model the errors the same API returns, so that a caller can decide whether to
retry without parsing a message.

## Designing a Solution

An enumeration rather than a status code. A status code makes the set of legal
values a convention that lives in a document; an enumeration makes it a type, and a
`match` that omits a case does not compile.

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

The same argument applies to the error type. A retry decision depends on facts,
the delay a server asked for, the status code it returned, so those facts are
attached to the variants that need them. A caller that matches on `RateLimited`
has the delay in hand.

## Implementation

```rust
//! Algebraic data types / enum state machines.
//!
//! NVIDIA cloud SDKs model workloads as finite state machines. Rust `enum` is
//! perfect for this: invalid states are unrepresentable and transitions are
//! explicit `match` arms, not nested `if` chains.

use std::time::Duration;

/// Lifecycle of a GPU cloud workload exposed through an SDK/API.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum WorkloadState {
    Pending,
    Provisioning,
    Running,
    Terminating,
    Terminated,
    Failed,
}

impl WorkloadState {
    /// Returns an error string for impossible transitions, or `Ok(())`.
    pub fn can_transition_to(self, next: Self) -> Result<(), String> {
        match (self, next) {
            // Forward lifecycle.
            (Self::Pending, Self::Provisioning)
            | (Self::Pending, Self::Failed)
            | (Self::Provisioning, Self::Running)
            | (Self::Provisioning, Self::Failed)
            | (Self::Running, Self::Terminating)
            | (Self::Running, Self::Failed)
            | (Self::Terminating, Self::Terminated)
            | (Self::Terminating, Self::Failed) => Ok(()),

            // Retry loops allowed from failed states.
            (Self::Failed, Self::Pending) | (Self::Failed, Self::Provisioning) => Ok(()),

            // Everything else is invalid.
            _ => Err(format!("cannot transition from {self:?} to {next:?}")),
        }
    }

    pub fn is_terminal(self) -> bool {
        matches!(self, Self::Terminated | Self::Failed)
    }

    pub fn summary(self) -> &'static str {
        match self {
            Self::Pending => "workload accepted, waiting for scheduler",
            Self::Provisioning => "GPU resources being allocated",
            Self::Running => "workload is running",
            Self::Terminating => "cleanup in progress",
            Self::Terminated => "workload stopped and billing ended",
            Self::Failed => "workload failed; inspect logs",
        }
    }
}

/// API error modeled as an enum with associated data.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ApiError {
    InvalidRequest(String),
    Unauthorized,
    RateLimited { retry_after: Duration },
    NotFound { resource_id: String },
    Server { status: u16, message: String },
}

impl ApiError {
    pub fn is_retryable(&self) -> bool {
        matches!(
            self,
            Self::RateLimited { .. }
                | Self::Server {
                    status: 500..=599,
                    ..
                }
        )
    }

    pub fn user_message(&self) -> String {
        match self {
            Self::InvalidRequest(msg) => format!("invalid request: {msg}"),
            Self::Unauthorized => "authentication required or token expired".to_string(),
            Self::RateLimited { retry_after } => {
                format!("rate limited, retry in {}ms", retry_after.as_millis())
            }
            Self::NotFound { resource_id } => format!("resource not found: {resource_id}"),
            Self::Server { status, message } => format!("server error {status}: {message}"),
        }
    }
}

/// Typical NVIDIA SDK helper: never expose nested `if let` soup to callers.
pub fn parse_gpu_count(raw: &str) -> Result<u32, ApiError> {
    match raw.trim() {
        "" => Err(ApiError::InvalidRequest("gpuCount is empty".into())),
        parsed => parsed.parse::<u32>().map_err(|_| {
            ApiError::InvalidRequest(format!("gpuCount must be a number, got {raw:?}"))
        }),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn state_machine_rejects_invalid_transitions() {
        assert!(
            WorkloadState::Pending
                .can_transition_to(WorkloadState::Provisioning)
                .is_ok()
        );
        assert!(
            WorkloadState::Running
                .can_transition_to(WorkloadState::Running)
                .is_err()
        );
        assert!(
            WorkloadState::Terminated
                .can_transition_to(WorkloadState::Running)
                .is_err()
        );
        assert!(WorkloadState::Terminating.is_terminal() == false);
        assert!(WorkloadState::Terminated.is_terminal());
    }

    #[test]
    fn api_error_retry_policy() {
        let rate_limited = ApiError::RateLimited {
            retry_after: Duration::from_millis(100),
        };
        let not_found = ApiError::NotFound {
            resource_id: "gpu-123".into(),
        };
        let server = ApiError::Server {
            status: 503,
            message: "maintenance".into(),
        };

        assert!(rate_limited.is_retryable());
        assert!(!not_found.is_retryable());
        assert!(server.is_retryable());
    }

    #[test]
    fn parsing_returns_typed_errors() {
        assert_eq!(parse_gpu_count("4"), Ok(4));
        assert!(parse_gpu_count("").is_err());
        assert!(parse_gpu_count("abc").is_err());
    }
}
```

`can_transition_to` matches on the pair `(self, next)`, listing every permitted
transition as an alternative pattern. The whole rule set is one expression, and the
fall-through arm catches everything else, including a self-transition such as
`Running` to `Running`.

A self-transition is refused rather than treated as a no-op. A controller that
reports a transition it did not perform writes an audit log that cannot be trusted,
and refusing the case costs one line.

`is_retryable` uses `matches!` with a range pattern: `status: 500..=599` is
retryable, everything else is not. `NotFound` and `Unauthorized` are not retryable
because waiting does not change them: the resource still does not exist and the
credential is still expired.

`parse_gpu_count` trims the field, distinguishes an empty field from an
unparseable one in the message, and quotes the received text with `{raw:?}` so that
trailing whitespace is visible. The error variant carries a message; the variant
itself is what a caller matches on.

The repository's version of this function is named for the employer's product line,
and its error messages name the field after that product. This edition names the
field `gpuCount` and leaves the logic unchanged.

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

**`can_transition_to` returns `Result<(), String>`.** A refused transition is a
value a caller may want to match on, to log it, to count it, or to distinguish
"illegal transition" from "the workload no longer exists", and a `String` cannot
be matched. It also allocates on every refusal. The fix is a small error type with
two fields, `from` and `next`, which is what the state machine already has in the
form of `WorkloadState`.

**`user_message` allocates for every call, including the two variants that need no
formatting.** `Unauthorized` returns `to_string()` of a constant. A `Display`
implementation writes into the caller's buffer and allocates nothing, which is the
idiomatic way to expose a message.

**`is_retryable` treats any status in `500..=599` as retryable, and a `Server`
variant carrying a `4xx` status as not retryable.** That is defensible for this
error type, and the range test is doing double duty: it is also asserting that the
`Server` variant holds a server-side status. Nothing enforces that at construction
time.

**The transition table is tested by example, not exhaustively.** The test checks
four transitions. There are thirty-six ordered pairs of six states, and the table
permits twelve of them. A test that loops over all pairs and compares each answer
with a written list would catch a missing or an extra pattern.

**`parse_gpu_count` accepts a value that overflows `u32` as a parse failure
rather than as a distinct error.** `"4294967296"` and `"four"` produce the same
variant, so a caller cannot tell a malformed field from an out-of-range one.

## Summary

- An enumeration makes the transition table exhaustive, because a `match` without
  a fall-through arm fails to build when a variant is added.
- A self-transition is refused rather than treated as a no-op, and the table states
  that explicitly.
- The error variants carry data because the retry delay and the status code are
  inputs to a decision.
- `can_transition_to` returns `Result<(), String>`. A `String` cannot be matched,
  so a caller cannot distinguish an illegal transition from a workload that no
  longer exists, and the refusal allocates. An error type carrying `from` and
  `next` would remove both problems.
- `user_message` allocates on every call, including the variants that need no
  formatting, where a `Display` implementation would write into the caller's
  buffer.
- `parse_gpu_count` reports an out-of-range value and a malformed one as the
  same variant.

## References

- The Rust Book, [Defining an enum](https://doc.rust-lang.org/book/ch06-01-defining-an-enum.html).
- Standard library, [`std::time::Duration`](https://doc.rust-lang.org/std/time/struct.Duration.html).
- Standard library, [`str::parse`](https://doc.rust-lang.org/std/primitive.str.html#method.parse).
