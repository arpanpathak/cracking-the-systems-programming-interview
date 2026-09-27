//! A controller for `GpuJob` objects. It runs each job as a pod that requests
//! the job's GPUs, and reports the pod's progress in the job's status.
//!
//! Run it against the cluster in the current kubeconfig context with
//! `cargo run -p gpujob` from `code/rust` (the package's default binary).

use futures::StreamExt;
use gpujob::{GpuJob, GpuJobStatus};
use k8s_openapi::api::core::v1::{Container, Pod, PodSpec, ResourceRequirements};
use k8s_openapi::apimachinery::pkg::api::resource::Quantity;
use kube::api::{DeleteParams, ObjectMeta, Patch, PatchParams};
use kube::runtime::controller::{Action, Controller};
use kube::runtime::watcher;
use kube::{Api, Client, Resource, ResourceExt};
use std::collections::BTreeMap;
use std::sync::Arc;
use std::time::Duration;

/// The field manager name under which the controller writes with server-side apply.
const MANAGER: &str = "gpujob-controller";

/// The extended resource through which a container requests GPUs.
const GPU: &str = "nvidia.com/gpu";

/// Everything a reconcile can fail with.
#[derive(Debug, thiserror::Error)]
enum Error {
    /// A request to the API server failed.
    #[error("kubernetes API: {0}")]
    Kube(#[from] kube::Error),
    /// The status could not be serialized into a patch.
    #[error("serializing status: {0}")]
    Json(#[from] serde_json::Error),
}

/// State shared by every reconcile.
struct Context {
    /// Client for the cluster's API server.
    client: Client,
}

/// Builds the pod that should exist for `job`.
///
/// The owner reference makes Kubernetes delete the pod together with the job,
/// and it lets the controller map each pod event to the job that owns the pod.
fn desired_pod(job: &GpuJob) -> Pod {
    let gpus = BTreeMap::from([(GPU.to_string(), Quantity(job.spec.gpus.to_string()))]);
    Pod {
        metadata: ObjectMeta {
            name: Some(job.name_any()),
            owner_references: job.controller_owner_ref(&()).map(|owner| vec![owner]),
            ..Default::default()
        },
        spec: Some(PodSpec {
            restart_policy: Some("Never".into()),
            containers: vec![Container {
                name: "job".into(),
                image: Some(job.spec.image.clone()),
                command: Some(job.spec.command.clone()).filter(|c| !c.is_empty()),
                resources: Some(ResourceRequirements {
                    limits: Some(gpus),
                    ..Default::default()
                }),
                ..Default::default()
            }],
            ..Default::default()
        }),
        ..Default::default()
    }
}

/// Returns the number of GPUs that an existing pod's container requests, read
/// from its limits, or `None` if the pod has no GPU limit.
fn pod_gpus(pod: &Pod) -> Option<u32> {
    let container = pod.spec.as_ref()?.containers.first()?;
    let limits = container.resources.as_ref()?.limits.as_ref()?;
    limits.get(GPU)?.0.parse().ok()
}

/// Makes the cluster match one job: ensures its pod exists with the requested
/// GPUs, and writes the pod's progress into the job's status.
async fn reconcile(job: Arc<GpuJob>, ctx: Arc<Context>) -> Result<Action, Error> {
    let namespace = job.namespace().unwrap_or_default();
    let name = job.name_any();
    let pods: Api<Pod> = Api::namespaced(ctx.client.clone(), &namespace);
    let jobs: Api<GpuJob> = Api::namespaced(ctx.client.clone(), &namespace);

    // The resources of a pod are fixed when it is created. When the job asks
    // for a different number of GPUs, delete the pod and come back after it is gone.
    if let Some(pod) = pods.get_opt(&name).await?
        && pod_gpus(&pod) != Some(job.spec.gpus)
    {
        tracing::info!(%name, "GPU count changed, replacing pod");
        pods.delete(&name, &DeleteParams::default()).await?;
        return Ok(Action::requeue(Duration::from_secs(2)));
    }

    let apply = PatchParams::apply(MANAGER).force();
    let pod = pods
        .patch(&name, &apply, &Patch::Apply(desired_pod(&job)))
        .await?;

    let status = GpuJobStatus::from_pod(&pod, job.metadata.generation);
    if job.status.as_ref() != Some(&status) {
        let message = status.message.as_deref().unwrap_or("");
        tracing::info!(%name, phase = ?status.phase, message, "status changed");
        let patch = serde_json::json!({
            "apiVersion": GpuJob::api_version(&()),
            "kind": GpuJob::kind(&()),
            "status": status,
        });
        jobs.patch_status(&name, &apply, &Patch::Apply(patch))
            .await?;
    }
    // Changes to the pod trigger the next reconcile through `owns`.
    Ok(Action::await_change())
}

/// Decides what happens after a failed reconcile: log it and retry in five seconds.
#[allow(clippy::needless_pass_by_value)] // the signature is fixed by `Controller::run`
fn error_policy(job: Arc<GpuJob>, error: &Error, _ctx: Arc<Context>) -> Action {
    tracing::warn!(name = %job.name_any(), %error, "reconcile failed");
    Action::requeue(Duration::from_secs(5))
}

/// Starts the controller and runs it until Ctrl-C.
#[tokio::main]
async fn main() -> Result<(), kube::Error> {
    tracing_subscriber::fmt()
        .with_env_filter("controller=info,kube=warn")
        .with_target(false)
        .with_ansi(std::io::IsTerminal::is_terminal(&std::io::stdout()))
        .init();
    let client = Client::try_default().await?;
    let jobs: Api<GpuJob> = Api::all(client.clone());
    let pods: Api<Pod> = Api::all(client.clone());

    Controller::new(jobs, watcher::Config::default())
        .owns(pods, watcher::Config::default())
        .shutdown_on_signal()
        .run(reconcile, error_policy, Arc::new(Context { client }))
        .for_each(|result| async move {
            if let Err(error) = result {
                tracing::debug!(%error, "reconcile error");
            }
        })
        .await;
    Ok(())
}
