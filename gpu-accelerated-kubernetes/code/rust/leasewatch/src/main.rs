//! Reports when a host in the `fleet` namespace stops renewing its Lease, and
//! when it starts again. It keeps a reflector store of the Leases and checks
//! it once a second.
//!
//! It judges a Lease by its own clock, the way the Kubernetes node lifecycle
//! controller judges node Leases: it notes the local time at which it first
//! sees each new `renewTime`, and declares the host expired when no new
//! `renewTime` has appeared for longer than the lease duration. The
//! `renewTime` value itself was written with the host's clock, which may
//! differ from ours.
//!
//! Run it from `code/rust`, against the cluster in the current kubeconfig
//! context, with `cargo run -p leasewatch`.

use futures::StreamExt;
use jiff::{Timestamp, Zoned};
use k8s_openapi::api::coordination::v1::Lease;
use kube::runtime::{WatchStreamExt, reflector, watcher};
use kube::{Api, Client, ResourceExt};
use std::collections::HashMap;
use std::error::Error;
use std::time::{Duration, Instant};

/// The namespace whose Leases the program watches.
const NAMESPACE: &str = "fleet";
/// How often the program re-evaluates every Lease.
const CHECK_EVERY: Duration = Duration::from_secs(1);

// ANCHOR: observation
/// What the program knows about one host's Lease.
struct Observation {
    /// The latest `renewTime` seen in the Lease.
    renew_time: Timestamp,
    /// The local time at which that `renewTime` was first seen.
    observed_at: Instant,
    /// Whether the host has been reported as expired.
    expired: bool,
}
// ANCHOR_END: observation

// ANCHOR: check
/// Updates the observation of one Lease at local time `now` and prints a line
/// when the host is first seen, expires, or renews again after expiring.
fn check(seen: &mut HashMap<String, Observation>, lease: &Lease, now: Instant) {
    let Some(spec) = &lease.spec else { return };
    let (Some(renew), Some(seconds)) = (&spec.renew_time, spec.lease_duration_seconds) else {
        return;
    };
    let duration = Duration::from_secs(u64::from(seconds.unsigned_abs()));
    let stamp = Zoned::now().strftime("%H:%M:%S").to_string();
    let name = lease.name_any();

    match seen.get_mut(&name) {
        None => {
            seen.insert(
                name.clone(),
                Observation {
                    renew_time: renew.0,
                    observed_at: now,
                    expired: false,
                },
            );
            println!(
                "{stamp} {name} seen, lease duration {}s",
                duration.as_secs()
            );
        }
        Some(obs) if obs.renew_time != renew.0 => {
            obs.renew_time = renew.0;
            obs.observed_at = now;
            if obs.expired {
                obs.expired = false;
                println!("{stamp} {name} renewing again");
            }
        }
        Some(obs) if !obs.expired && now.duration_since(obs.observed_at) > duration => {
            obs.expired = true;
            let silent = now.duration_since(obs.observed_at).as_secs_f64().round();
            println!("{stamp} {name} expired: no renewal seen for {silent}s");
        }
        Some(_) => {}
    }
}
// ANCHOR_END: check

// ANCHOR: run
/// Starts a watcher that fills a reflector store with the namespace's Leases,
/// waits for the first list, and then checks every Lease in the store once
/// per `CHECK_EVERY` until the process receives Ctrl-C.
#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    let leases: Api<Lease> = Api::namespaced(Client::try_default().await?, NAMESPACE);
    let (store, writer) = reflector::store();
    let stream = watcher(leases, watcher::Config::default())
        .default_backoff()
        .reflect(writer)
        .applied_objects();
    tokio::spawn(stream.for_each(|_| std::future::ready(())));
    store.wait_until_ready().await?;

    let mut seen = HashMap::new();
    let mut ticker = tokio::time::interval(CHECK_EVERY);
    loop {
        tokio::select! {
            _ = tokio::signal::ctrl_c() => return Ok(()),
            _ = ticker.tick() => {}
        }
        let now = Instant::now();
        for lease in store.state() {
            check(&mut seen, &lease, now);
        }
    }
}
// ANCHOR_END: run
