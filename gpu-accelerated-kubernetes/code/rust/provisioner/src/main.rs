//! Models a controller that asks a provider for machines until a pool has the
//! size its owner asked for.
//!
//! The provider's create call can fail in an awkward way: the machine is
//! created and the reply is lost. The program runs the same controller twice.
//! The first run retries a lost reply with a plain create call. The second
//! sends a client token with every call, so a retry returns the machine that
//! the first attempt created.
//!
//! Run it from code/rust with:
//!
//! ```text
//! cargo run -p provisioner
//! ```

use std::collections::{BTreeMap, BTreeSet};
use std::fmt;

// ANCHOR: provider
/// One machine the provider has created.
#[derive(Clone)]
struct Machine {
    /// The provider's identifier for the machine.
    id: String,
    /// The kind of machine.
    model: &'static str,
    /// The client token of the call that created it, if it carried one.
    token: Option<String>,
}

/// The ways a create call can fail.
enum CreateError {
    /// No reply arrived. The machine may or may not exist.
    Timeout,
    /// The account already holds as many machines of this model as it is
    /// allowed.
    Quota,
}

impl fmt::Display for CreateError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(match self {
            CreateError::Timeout => "timed out",
            CreateError::Quota => "quota exceeded",
        })
    }
}

/// The account that machines are created in.
struct Provider {
    /// The number of machines of each model the account may hold.
    quota: BTreeMap<&'static str, usize>,
    /// Every machine that exists, in creation order.
    machines: Vec<Machine>,
    /// Counts create calls, so the run can lose the reply to one of them.
    calls: usize,
    /// The number of the call whose reply is lost.
    lose_reply: usize,
}

impl Provider {
    /// Returns how many machines of a model exist.
    fn count(&self, model: &str) -> usize {
        self.machines.iter().filter(|m| m.model == model).count()
    }

    /// Makes one machine. A call that carries a token already used by an
    /// existing machine returns that machine and creates nothing.
    fn create(&mut self, model: &'static str, token: Option<&str>) -> Result<Machine, CreateError> {
        self.calls += 1;
        if let Some(token) = token
            && let Some(existing) = self
                .machines
                .iter()
                .find(|m| m.token.as_deref() == Some(token))
        {
            return Ok(existing.clone());
        }

        if self.count(model) >= self.quota[model] {
            return Err(CreateError::Quota);
        }

        let machine = Machine {
            id: format!("m-{:02}", self.machines.len() + 1),
            model,
            token: token.map(str::to_owned),
        };
        self.machines.push(machine.clone());

        if self.calls == self.lose_reply {
            return Err(CreateError::Timeout);
        }

        Ok(machine)
    }
}
// ANCHOR_END: provider

// ANCHOR: controller
/// A group of identical machines and the size its owner wants.
struct Pool {
    /// Prefixes the name of each slot: thor-1, thor-2, and so on.
    name: &'static str,
    /// The kind of machine in the pool.
    model: &'static str,
    /// The number of machines the pool should have.
    want: usize,
}

/// Brings each pool to its wanted size.
struct Controller {
    provider: Provider,
    /// Whether create calls carry a client token.
    tokens: bool,
    /// Maps a pool's name to the machines the controller knows it has.
    owned: BTreeMap<&'static str, Vec<Machine>>,
}

impl Controller {
    /// Fills the empty slots of one pool, in order, and stops at the first
    /// call that fails. It returns true when the pool is full.
    fn reconcile(&mut self, pool: &Pool) -> bool {
        let owned = self.owned.entry(pool.name).or_default();

        while owned.len() < pool.want {
            let slot = format!("{}-{}", pool.name, owned.len() + 1);
            let token = self.tokens.then_some(slot.as_str());

            match self.provider.create(pool.model, token) {
                Ok(machine) => {
                    println!("    {slot:<8} is machine {}", machine.id);
                    owned.push(machine);
                }
                Err(e) => {
                    println!("    {slot:<8} create failed: {e}");

                    return false;
                }
            }
        }

        true
    }
}
// ANCHOR_END: controller

// ANCHOR: run
/// The fleet we ask for: the Thors on the shelf and the two Sparks.
const POOLS: [Pool; 2] = [
    Pool {
        name: "thor",
        model: "Jetson AGX Thor",
        want: 5,
    },
    Pool {
        name: "spark",
        model: "DGX Spark",
        want: 2,
    },
];

/// Reconciles every pool for three passes and then compares what the
/// controller owns with what the provider holds.
fn run(tokens: bool) {
    let provider = Provider {
        quota: BTreeMap::from([("Jetson AGX Thor", 5), ("DGX Spark", 2)]),
        machines: Vec::new(),
        calls: 0,
        lose_reply: 3,
    };
    let mut c = Controller {
        provider,
        tokens,
        owned: BTreeMap::new(),
    };

    for pass in 1..=3 {
        println!("  pass {pass}");
        let mut full = true;

        for pool in &POOLS {
            full = c.reconcile(pool) && full;
        }

        if full {
            println!("    every pool is full");
            break;
        }
    }

    let mut known = BTreeSet::new();

    for pool in &POOLS {
        let owned = &c.owned[pool.name];
        known.extend(owned.iter().map(|m| m.id.as_str()));
        println!(
            "  {:<5} wanted {}, controller owns {}, provider holds {}",
            pool.name,
            pool.want,
            owned.len(),
            c.provider.count(pool.model)
        );
    }

    for m in c
        .provider
        .machines
        .iter()
        .filter(|m| !known.contains(m.id.as_str()))
    {
        println!(
            "  machine {} ({}) is running and belongs to no pool",
            m.id, m.model
        );
    }
}

fn main() {
    println!("create calls without a client token:");
    run(false);
    println!("create calls with the slot name as the client token:");
    run(true);
}
// ANCHOR_END: run
