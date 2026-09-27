//! Shows the API server refusing a write with an outdated resource version.
//! Two clients read the `train` job, and both write it back with `replace`.
//! The first write succeeds and changes the version, so the second fails with
//! `409 Conflict`.
//!
//! Run it from `code/rust`, while a `GpuJob` named `train` exists, with
//! `cargo run -p gpujob --bin conflict`.

use gpujob::GpuJob;
use kube::api::PostParams;
use kube::{Api, Client, ResourceExt};

/// The job that both clients read and write.
const JOB: &str = "train";

/// Performs the two writes and reports how the server answered each.
#[tokio::main]
async fn main() -> Result<(), kube::Error> {
    let jobs: Api<GpuJob> = Api::default_namespaced(Client::try_default().await?);
    let mut first = jobs.get(JOB).await?;
    let mut second = first.clone();
    println!(
        "both clients read {JOB} at v{}",
        first.resource_version().unwrap_or_default()
    );

    first.spec.gpus += 1;
    let stored = jobs.replace(JOB, &PostParams::default(), &first).await?;
    println!(
        "first write stored, now v{}",
        stored.resource_version().unwrap_or_default()
    );

    second.spec.gpus += 2;
    match jobs.replace(JOB, &PostParams::default(), &second).await {
        Err(kube::Error::Api(status)) if status.code == 409 => {
            println!("second write refused: {} {}", status.code, status.message);
        }
        other => println!("unexpected: {other:?}"),
    }
    Ok(())
}
