//! Prints the `CustomResourceDefinition` for `GpuJob` as JSON, ready for kubectl:
//!
//! ```console
//! cargo run -p gpujob --bin crdgen | kubectl apply -f -
//! ```

use gpujob::GpuJob;
use kube::CustomResourceExt;

/// Generates the definition from the `GpuJob` type and prints it.
fn main() -> serde_json::Result<()> {
    println!("{}", serde_json::to_string_pretty(&GpuJob::crd())?);
    Ok(())
}
