//! Round-robin scheduling: each runnable task gets one fixed time slice in turn,
//! so no task starves. This is the simplest fair policy a scheduler can use.
//!
//! Run with: cargo run --bin os_scheduler

const QUANTUM_MS: u64 = 5;

/// The task chosen on each of `ticks` time slices.
fn schedule<'a>(tasks: &[&'a str], ticks: usize) -> Vec<&'a str> {
    if tasks.is_empty() {
        return Vec::new();
    }
    (0..ticks).map(|tick| tasks[tick % tasks.len()]).collect()
}

fn main() {
    let tasks = ["encoder", "decoder", "gc"];

    println!("{} runnable tasks, {QUANTUM_MS} ms quantum", tasks.len());
    for (tick, task) in schedule(&tasks, 7).iter().enumerate() {
        let start = tick as u64 * QUANTUM_MS;
        println!(
            "  slice {tick}: {start:>2}-{:>2} ms  {task}",
            start + QUANTUM_MS
        );
    }

    let order = schedule(&tasks, 7);
    assert_eq!(
        order,
        [
            "encoder", "decoder", "gc", "encoder", "decoder", "gc", "encoder"
        ]
    );
    assert!(schedule(&[], 3).is_empty());

    // A long task is preempted, not run to completion, which is what bounds its
    // worst-case latency to one quantum times the number of tasks.
    println!(
        "\nworst-case wait for one slice: {} ms",
        QUANTUM_MS * tasks.len() as u64
    );
    println!("all checks passed");
}
