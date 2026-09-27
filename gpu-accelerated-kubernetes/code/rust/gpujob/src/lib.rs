//! The `GpuJob` custom resource: a request to run one container with a number
//! of GPUs, and the status that the controller reports back.
//!
//! The `///` comments on the spec and status types become the field
//! descriptions in the generated `CustomResourceDefinition`, which
//! `kubectl explain gpujob.spec` prints.

use k8s_openapi::api::core::v1::Pod;
use kube::CustomResource;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

/// A request to run one container with a number of GPUs.
///
/// The `CustomResource` derive generates the `GpuJob` type, which holds this
/// spec together with the object's metadata and an optional `GpuJobStatus`.
#[derive(CustomResource, Deserialize, Serialize, Clone, Debug, JsonSchema)]
#[kube(
    group = "gpucloud.dev",
    version = "v1",
    kind = "GpuJob",
    namespaced,
    status = "GpuJobStatus",
    shortname = "gj",
    printcolumn = r#"{"name":"GPUs","type":"integer","jsonPath":".spec.gpus"}"#,
    printcolumn = r#"{"name":"Phase","type":"string","jsonPath":".status.phase"}"#
)]
pub struct GpuJobSpec {
    /// Container image to run.
    pub image: String,
    /// Command to run in the container. When empty, the image's own command runs.
    #[serde(default)]
    pub command: Vec<String>,
    /// Number of GPUs the container requests.
    // Kubernetes schemas support int32 and int64, so the u32 is published as a
    // non-negative int32.
    #[schemars(with = "i32", range(min = 0))]
    pub gpus: u32,
}

/// The state of a job as the controller last observed it.
#[derive(Deserialize, Serialize, Clone, Debug, Default, PartialEq, JsonSchema)]
#[serde(rename_all = "camelCase")]
pub struct GpuJobStatus {
    /// Progress of the job's pod.
    pub phase: Phase,
    /// The scheduler's reason, when the pod cannot be placed on a node.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub message: Option<String>,
    /// The `metadata.generation` of the spec that this status describes.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub observed_generation: Option<i64>,
}

/// Progress of a job, following the phase of its pod.
#[derive(Deserialize, Serialize, Clone, Copy, Debug, Default, PartialEq, Eq, JsonSchema)]
pub enum Phase {
    /// The pod is waiting to be scheduled or for its containers to start.
    #[default]
    Pending,
    /// The pod's container is running.
    Running,
    /// The container exited with status 0.
    Succeeded,
    /// The container exited with a non-zero status.
    Failed,
}

impl GpuJobStatus {
    /// Derives a job's status from its pod. `generation` is the job's
    /// `metadata.generation`, recorded as the generation this status describes.
    #[must_use]
    pub fn from_pod(pod: &Pod, generation: Option<i64>) -> Self {
        let status = pod.status.as_ref();
        let phase = match status.and_then(|s| s.phase.as_deref()) {
            Some("Running") => Phase::Running,
            Some("Succeeded") => Phase::Succeeded,
            Some("Failed") => Phase::Failed,
            _ => Phase::Pending,
        };
        // A pod that cannot be placed explains why in its PodScheduled condition.
        let message = status
            .and_then(|s| s.conditions.as_ref())
            .into_iter()
            .flatten()
            .find(|c| c.type_ == "PodScheduled" && c.status == "False")
            .and_then(|c| c.message.clone());
        Self {
            phase,
            message,
            observed_generation: generation,
        }
    }
}
