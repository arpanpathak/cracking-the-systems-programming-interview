//! Prints the event stream that a watcher produces for `GpuJob` objects in the
//! current namespace: the initial list, one object at a time, and then one
//! event per change. Stop it with Ctrl-C.
//!
//! Run it from `code/rust` with `cargo run -p gpujob --bin watch_jobs`.

use futures::TryStreamExt;
use gpujob::GpuJob;
use kube::runtime::watcher::{self, Event, watcher};
use kube::{Api, Client, ResourceExt};

/// Formats a job as its name, GPU count, and resource version.
fn describe(job: &GpuJob) -> String {
    let version = job.resource_version().unwrap_or_default();
    format!("{} gpus={} v{version}", job.name_any(), job.spec.gpus)
}

/// Watches `GpuJob` objects and prints one line per event.
#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let jobs: Api<GpuJob> = Api::default_namespaced(Client::try_default().await?);
    let mut events = std::pin::pin!(watcher(jobs, watcher::Config::default()));
    while let Some(event) = events.try_next().await? {
        match event {
            Event::Init => println!("list started"),
            Event::InitApply(job) => println!("  listed   {}", describe(&job)),
            Event::InitDone => println!("list complete, watching"),
            Event::Apply(job) => println!("  changed  {}", describe(&job)),
            Event::Delete(job) => println!("  deleted  {}", describe(&job)),
        }
    }
    Ok(())
}
