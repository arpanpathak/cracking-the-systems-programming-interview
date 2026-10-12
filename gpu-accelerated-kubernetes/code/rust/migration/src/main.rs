//! Models the live migration of a virtual machine: moving a running VM's
//! memory from one host to another while the VM keeps running.
//!
//! The model is the pre-copy algorithm. Each round sends the memory that
//! changed during the round before it. The VM is paused only for the last
//! round, when what remains is small enough to send within the allowed pause.
//! The program runs the algorithm for VMs of two sizes over the links in our
//! fleet and prints each round.
//!
//! Run it from code/rust with:
//!
//! ```text
//! cargo run -p migration
//! ```

// ANCHOR: types
/// The virtual machine being moved.
struct Vm {
    /// Labels the VM in the output.
    name: &'static str,
    /// The size of the VM's memory.
    memory_gb: f64,
    /// How much memory the VM's programs change each second.
    dirty_gbps: f64,
}

/// The network path between the two hosts.
struct Link {
    /// Labels the link in the output.
    name: &'static str,
    /// What the link carries, in gigabytes per second. A link of 8 gigabits
    /// per second carries 1 gigabyte per second.
    gbps: f64,
}

/// The longest the VM may be paused for the last round, in seconds.
const MAX_PAUSE_SECONDS: f64 = 0.3;
/// Ends a migration that keeps making progress too slowly.
const MAX_ROUNDS: u32 = 30;
/// How much more the guest is slowed each time a round fails to shrink the
/// remaining memory, as a fraction of full speed.
const THROTTLE_STEP: f64 = 0.2;
/// The most the guest may be slowed.
const MAX_THROTTLE: f64 = 0.8;
// ANCHOR_END: types

// ANCHOR: migrate
/// Runs pre-copy rounds until the remaining memory can be sent within the
/// allowed pause, and prints each round. With `throttle` set, it slows the
/// guest whenever a round leaves as much memory to send as it started with.
fn migrate(vm: &Vm, link: &Link, throttle: bool) {
    let suffix = if throttle { ", with throttling" } else { "" };
    println!("{} over {}{suffix}:", vm.name, link.name);

    let mut remaining = vm.memory_gb; // memory still to be sent
    let mut slowed = 0.0; // fraction by which the guest is slowed
    let mut elapsed = 0.0;

    for round in 1..=MAX_ROUNDS {
        if remaining <= link.gbps * MAX_PAUSE_SECONDS {
            let pause = remaining / link.gbps;
            println!("  round {round:2}: VM paused, {remaining:.2} GB sent in {pause:.2} s");
            println!(
                "  done in {:.1} s; the VM was paused for {:.0} ms",
                elapsed + pause,
                pause * 1000.0
            );

            return;
        }

        let seconds = remaining / link.gbps;
        let dirtied = (vm.dirty_gbps * (1.0 - slowed) * seconds).min(vm.memory_gb);
        println!(
            "  round {round:2}: {remaining:6.2} GB sent in {seconds:6.1} s, {dirtied:6.2} GB changed meanwhile"
        );
        elapsed += seconds;

        if dirtied >= remaining {
            if !throttle || slowed >= MAX_THROTTLE {
                println!("  does not converge: memory changes as fast as the link carries it");

                return;
            }

            slowed += THROTTLE_STEP;
            println!(
                "            no progress: guest slowed to {:.0}% of full speed",
                (1.0 - slowed) * 100.0
            );
        }

        remaining = dirtied;
    }

    println!("  gave up after {MAX_ROUNDS} rounds");
}
// ANCHOR_END: migrate

// ANCHOR: main
fn main() {
    // An inference VM sized for the Orin NX, and a training VM sized for a
    // Thor or a Spark.
    let inference = Vm {
        name: "16 GB inference VM (0.2 GB/s changed)",
        memory_gb: 16.0,
        dirty_gbps: 0.2,
    };
    let training = Vm {
        name: "100 GB training VM (4 GB/s changed)",
        memory_gb: 100.0,
        dirty_gbps: 4.0,
    };

    // The links in the fleet, in gigabytes per second.
    let orin = Link {
        name: "1 GbE",
        gbps: 0.125,
    };
    let lane = Link {
        name: "one 25 GbE lane",
        gbps: 3.125,
    };
    let bonded = Link {
        name: "four bonded 25 GbE lanes",
        gbps: 12.5,
    };
    let spark = Link {
        name: "the Sparks' 200 GbE cable",
        gbps: 25.0,
    };

    migrate(&inference, &orin, false);
    migrate(&inference, &lane, false);
    migrate(&training, &lane, false);
    migrate(&training, &lane, true);
    migrate(&training, &bonded, false);
    migrate(&training, &spark, false);
}
// ANCHOR_END: main
