//! Reports, for every node in the cluster, how many `nvidia.com/gpu` units the
//! node advertises, how many are held by pods, and which pods hold them. It is
//! a read-only client: it lists nodes and pods through the API server and does
//! the accounting itself, the same way the scheduler counts extended resources.
//!
//! Run it from `code/rust`, against the cluster in the current kubeconfig
//! context, with `cargo run -p gpuusage`.

use k8s_openapi::api::core::v1::{Node, Pod};
use k8s_openapi::apimachinery::pkg::api::resource::Quantity;
use kube::api::ListParams;
use kube::{Api, Client, ResourceExt};
use std::collections::BTreeMap;
use std::error::Error;

/// The extended resource that the NVIDIA device plugin advertises.
const GPU: &str = "nvidia.com/gpu";

/// A pod that holds GPU units on a node.
struct Holder {
    /// The pod's namespace and name, as `namespace/name`.
    pod: String,
    /// The number of `nvidia.com/gpu` units the pod holds.
    units: i64,
}

/// Returns the number of GPU units a pod requests: the sum of the
/// `nvidia.com/gpu` limits of its containers.
fn pod_gpus(pod: &Pod) -> i64 {
    let Some(spec) = &pod.spec else { return 0 };
    spec.containers
        .iter()
        .filter_map(|c| c.resources.as_ref()?.limits.as_ref()?.get(GPU))
        .filter_map(|q| q.0.parse::<i64>().ok())
        .sum()
}

/// Returns the node a pod currently holds resources on. A pod holds them from
/// the moment it is bound to a node until it finishes; a pod that has
/// succeeded or failed gives them back.
fn holding_node(pod: &Pod) -> Option<&str> {
    let phase = pod.status.as_ref().and_then(|s| s.phase.as_deref());
    if matches!(phase, Some("Succeeded" | "Failed")) {
        return None;
    }
    pod.spec.as_ref()?.node_name.as_deref()
}

/// Reads the number of GPU units from a node's capacity or allocatable map.
fn gpu_units(resources: Option<&BTreeMap<String, Quantity>>) -> i64 {
    resources
        .and_then(|r| r.get(GPU))
        .and_then(|q| q.0.parse().ok())
        .unwrap_or(0)
}

/// Lists every node and every pod, groups the GPU-holding pods by node, and
/// prints one table row per node followed by the pods that hold its units.
#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    let client = Client::try_default().await?;
    let nodes = Api::<Node>::all(client.clone())
        .list(&ListParams::default())
        .await?;
    let pods = Api::<Pod>::all(client).list(&ListParams::default()).await?;

    let mut holders: BTreeMap<String, Vec<Holder>> = BTreeMap::new();
    for pod in &pods {
        let units = pod_gpus(pod);
        if let Some(node) = holding_node(pod)
            && units > 0
        {
            let name = format!("{}/{}", pod.namespace().unwrap_or_default(), pod.name_any());
            holders
                .entry(node.to_string())
                .or_default()
                .push(Holder { pod: name, units });
        }
    }

    println!(
        "{:<23}{:<10}{:<13}{:<8}FREE",
        "NODE", "CAPACITY", "ALLOCATABLE", "IN USE"
    );
    for node in &nodes {
        let name = node.name_any();
        let in_use: i64 = holders
            .get(&name)
            .map_or(0, |h| h.iter().map(|h| h.units).sum());
        let status = node.status.as_ref();
        let capacity = gpu_units(status.and_then(|s| s.capacity.as_ref()));
        let allocatable = gpu_units(status.and_then(|s| s.allocatable.as_ref()));
        println!(
            "{:<23}{:<10}{:<13}{:<8}{}",
            name,
            capacity,
            allocatable,
            in_use,
            allocatable - in_use
        );
    }
    for (node, list) in &mut holders {
        list.sort_by(|a, b| a.pod.cmp(&b.pod));
        for h in list.iter() {
            println!("  {} holds {} on {node}", h.pod, h.units);
        }
    }
    Ok(())
}
