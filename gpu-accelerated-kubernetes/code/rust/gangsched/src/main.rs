//! Models two decisions a scheduler makes for a training job that needs
//! several GPUs at once: whether to start the job, and which machines to give
//! it.
//!
//! The fleet is the eight machines of chapter 4, each with one GPU. The
//! program first hands out GPUs one pod at a time and shows two jobs blocking
//! each other. It then admits whole jobs, and finally compares two ways of
//! choosing a job's machines by the network link the job would have to use.
//!
//! Run it from code/rust with:
//!
//! ```text
//! cargo run -p gangsched
//! ```

// ANCHOR: fleet
/// One machine with one GPU.
struct Node {
    /// The machine's host name.
    name: &'static str,
    /// The group of machines that share a fast link.
    domain: Domain,
    /// The job that holds the machine's GPU, if any.
    job: Option<&'static str>,
}

/// A group of machines that share a fast link.
#[derive(Clone, Copy, PartialEq)]
enum Domain {
    /// The Orin NX, alone on 1 GbE.
    Bench,
    /// The two Sparks, on a 200 GbE cable.
    Desk,
    /// The five Thors, on a 25 GbE switch.
    Shelf,
}

/// The network path a group of machines shares.
struct Link {
    /// How the link is printed.
    label: &'static str,
    /// What the link carries, in gigabytes per second.
    gbps: f64,
}

impl Domain {
    /// Returns the link the machines of this domain share.
    fn link(self) -> Link {
        match self {
            Domain::Shelf => Link { label: "the 25 GbE switch", gbps: 3.125 },
            Domain::Desk => Link { label: "the 200 GbE cable", gbps: 25.0 },
            Domain::Bench => Link { label: "1 GbE", gbps: 0.125 },
        }
    }
}

/// The link between machines in different domains.
const HOUSE_NETWORK: Link = Link { label: "the 1 GbE house network", gbps: 0.125 };

/// Returns the machines in name order, all free.
fn new_fleet() -> Vec<Node> {
    [
        ("orin-nx-1", Domain::Bench),
        ("spark-1", Domain::Desk),
        ("spark-2", Domain::Desk),
        ("thor-1", Domain::Shelf),
        ("thor-2", Domain::Shelf),
        ("thor-3", Domain::Shelf),
        ("thor-4", Domain::Shelf),
        ("thor-5", Domain::Shelf),
    ]
    .into_iter()
    .map(|(name, domain)| Node { name, domain, job: None })
    .collect()
}

/// A group of workers that have to run at the same time, one GPU each.
#[derive(Clone, Copy)]
struct Job {
    name: &'static str,
    workers: usize,
}
// ANCHOR_END: fleet

/// Returns the indexes of the machines whose GPU nobody holds, in name order.
fn free(fleet: &[Node]) -> Vec<usize> {
    (0..fleet.len()).filter(|&i| fleet[i].job.is_none()).collect()
}

/// Joins the names of some machines with spaces.
fn names(fleet: &[Node], nodes: &[usize]) -> String {
    nodes.iter().map(|&i| fleet[i].name).collect::<Vec<_>>().join(" ")
}

// ANCHOR: podwise
/// Gives each job one GPU in turn until none are left, the way a scheduler
/// that sees only single pods would, and reports what each job ended up
/// holding.
fn pod_at_a_time(mut fleet: Vec<Node>, jobs: &[Job]) {
    let held = |fleet: &[Node], job: &Job| -> Vec<usize> {
        (0..fleet.len()).filter(|&i| fleet[i].job == Some(job.name)).collect()
    };
    let mut progress = true;
    while progress {
        progress = false;
        for job in jobs {
            if held(&fleet, job).len() < job.workers
                && let Some(&first) = free(&fleet).first()
            {
                fleet[first].job = Some(job.name);
                progress = true;
            }
        }
    }
    let mut running = 0;
    for job in jobs {
        let mine = held(&fleet, job);
        println!("  {:<8} holds {} of {} GPUs: {}", job.name, mine.len(), job.workers, names(&fleet, &mine));
        if mine.len() == job.workers {
            running += 1;
        }
    }
    let taken = fleet.len() - free(&fleet).len();
    println!("  {taken} of {} GPUs are held and {running} jobs are running", fleet.len());
}
// ANCHOR_END: podwise

// ANCHOR: place
/// Chooses machines for a job from the free ones, or returns `None` when it
/// cannot place every worker.
type Placer = fn(fleet: &[Node], open: &[usize], workers: usize) -> Option<Vec<usize>>;

/// Takes the first free machines in name order.
fn first_free(_fleet: &[Node], open: &[usize], workers: usize) -> Option<Vec<usize>> {
    open.get(..workers).map(<[usize]>::to_vec)
}

/// Looks for one domain that can hold the whole job and, among those, takes
/// the one with the fewest free machines, so that large domains stay whole
/// for large jobs. A job that fits in no single domain is spread over the
/// first free machines.
fn by_topology(fleet: &[Node], open: &[usize], workers: usize) -> Option<Vec<usize>> {
    let in_domain = |domain: Domain| -> Vec<usize> {
        open.iter().copied().filter(|&i| fleet[i].domain == domain).collect()
    };
    [Domain::Bench, Domain::Desk, Domain::Shelf]
        .into_iter()
        .map(in_domain)
        .filter(|members| members.len() >= workers)
        .min_by_key(Vec::len)
        .map(|members| members[..workers].to_vec())
        .or_else(|| first_free(fleet, open, workers))
}
// ANCHOR_END: place

// ANCHOR: cost
/// The size of the gradient every worker contributes per step, in gigabytes.
const GRADIENT_GB: f64 = 14.0;

/// Returns the link a job's all-reduce is limited by: the domain's link when
/// every machine is in one domain, and the house network otherwise.
fn slowest(fleet: &[Node], nodes: &[usize]) -> Link {
    let first = fleet[nodes[0]].domain;
    if nodes.iter().all(|&i| fleet[i].domain == first) { first.link() } else { HOUSE_NETWORK }
}

/// Returns the time one ring all-reduce takes: each worker sends 2(n-1)/n
/// gradients over the slowest link.
fn exchange_seconds(fleet: &[Node], nodes: &[usize]) -> f64 {
    let n = nodes.len() as f64;
    2.0 * (n - 1.0) / n * GRADIENT_GB / slowest(fleet, nodes).gbps
}
// ANCHOR_END: cost

// ANCHOR: admit
/// Starts a job only when every one of its workers has a machine. It reports
/// the placement and what the job's all-reduce will cost, and returns false
/// when the job has to wait.
fn admit(fleet: &mut [Node], job: Job, place: Placer) -> bool {
    let open = free(fleet);
    let Some(nodes) = place(fleet, &open, job.workers) else {
        println!("  {:<8} waits: it needs {} GPUs and {} are free", job.name, job.workers, open.len());
        return false;
    };
    for &i in &nodes {
        fleet[i].job = Some(job.name);
    }
    println!("  {:<8} runs on {}", job.name, names(fleet, &nodes));
    if nodes.len() > 1 {
        let link = slowest(fleet, &nodes);
        println!("           over {}: {:.1} s for each all-reduce", link.label, exchange_seconds(fleet, &nodes));
    }
    true
}

/// Frees every GPU a job holds.
fn release(fleet: &mut [Node], job: &str) {
    for node in fleet.iter_mut().filter(|n| n.job == Some(job)) {
        node.job = None;
    }
    println!("  {job:<8} finishes");
}
// ANCHOR_END: admit

// ANCHOR: main
fn main() {
    let two = [Job { name: "train-a", workers: 5 }, Job { name: "train-b", workers: 5 }];

    println!("one pod at a time, two jobs of five workers:");
    pod_at_a_time(new_fleet(), &two);

    println!("whole jobs at a time:");
    let mut fleet = new_fleet();
    admit(&mut fleet, two[0], by_topology);
    admit(&mut fleet, two[1], by_topology);
    release(&mut fleet, "train-a");
    admit(&mut fleet, two[1], by_topology);

    let three = [
        Job { name: "pair", workers: 2 },
        Job { name: "quad", workers: 4 },
        Job { name: "single", workers: 1 },
    ];
    println!("three jobs, on the first free machines:");
    let mut fleet = new_fleet();
    for job in three {
        admit(&mut fleet, job, first_free);
    }
    println!("the same three jobs, placed by topology:");
    let mut fleet = new_fleet();
    for job in three {
        admit(&mut fleet, job, by_topology);
    }
}
// ANCHOR_END: main
