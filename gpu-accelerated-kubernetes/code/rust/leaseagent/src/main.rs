//! Keeps a Kubernetes Lease alive for one host, the way the kubelet keeps its
//! node's Lease in the `kube-node-lease` namespace alive. Every two seconds it
//! writes the Lease named after the host in the `fleet` namespace, with the
//! current time as `renewTime` and a lease duration of six seconds. Other
//! programs judge the host alive for as long as these renewals continue.
//!
//! Run it from `code/rust`, against the cluster in the current kubeconfig
//! context, with `cargo run -p leaseagent -- gpu-host-a`.

use jiff::Timestamp;
use jiff::tz::TimeZone;
use k8s_openapi::api::coordination::v1::{Lease, LeaseSpec};
use k8s_openapi::apimachinery::pkg::apis::meta::v1::MicroTime;
use kube::api::{ObjectMeta, Patch, PatchParams};
use kube::{Api, Client};
use std::error::Error;
use std::time::Duration;

// ANCHOR: settings
/// The namespace that holds the hosts' Leases.
const NAMESPACE: &str = "fleet";
/// How often the agent renews the Lease: a third of the lease duration, so a
/// host has to miss three renewals in a row before its Lease expires.
const RENEW_EVERY: Duration = Duration::from_secs(2);
/// How long a Lease stays valid after its last renewal, in seconds.
const LEASE_DURATION: i32 = 6;
/// The field manager name for server-side apply.
const FIELD_MANAGER: &str = "leaseagent";
// ANCHOR_END: settings

// ANCHOR: lease
/// Builds the Lease that `host` writes at time `now`, having first acquired
/// it at time `acquired`.
fn lease(host: &str, acquired: Timestamp, now: Timestamp) -> Lease {
    Lease {
        metadata: ObjectMeta {
            name: Some(host.to_string()),
            namespace: Some(NAMESPACE.to_string()),
            ..ObjectMeta::default()
        },
        spec: Some(LeaseSpec {
            holder_identity: Some(host.to_string()),
            lease_duration_seconds: Some(LEASE_DURATION),
            acquire_time: Some(MicroTime(acquired)),
            renew_time: Some(MicroTime(now)),
            ..LeaseSpec::default()
        }),
    }
}
// ANCHOR_END: lease

/// Formats a timestamp as local time of day, for the log.
fn time_of_day(t: Timestamp) -> String {
    t.to_zoned(TimeZone::system())
        .strftime("%H:%M:%S")
        .to_string()
}

// ANCHOR: renew
/// Reads the host name from the command line and renews its Lease with
/// server-side apply until the process receives Ctrl-C. A renewal that fails
/// is reported and retried at the next tick.
#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    let Some(host) = std::env::args().nth(1) else {
        eprintln!("usage: leaseagent <host>");
        std::process::exit(2);
    };
    let leases: Api<Lease> = Api::namespaced(Client::try_default().await?, NAMESPACE);
    let params = PatchParams::apply(FIELD_MANAGER).force();
    let acquired = Timestamp::now();
    let mut ticker = tokio::time::interval(RENEW_EVERY);
    loop {
        tokio::select! {
            _ = tokio::signal::ctrl_c() => return Ok(()),
            _ = ticker.tick() => {}
        }
        let now = Timestamp::now();
        match leases
            .patch(&host, &params, &Patch::Apply(lease(&host, acquired, now)))
            .await
        {
            Ok(_) => println!("{} {host} renewed", time_of_day(now)),
            Err(error) => println!("{} {host} renewal failed: {error}", time_of_day(now)),
        }
    }
}
// ANCHOR_END: renew
