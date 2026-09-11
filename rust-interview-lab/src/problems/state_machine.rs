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
