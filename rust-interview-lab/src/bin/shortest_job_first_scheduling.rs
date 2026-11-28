use std::{
    cmp::{Ordering::*, Reverse},
    collections::BinaryHeap,
};

struct Job<F> {
    run: F,
    time: u32,
    priority: u32,
} // Smaller priotiy means higher
type JobState = Reverse<(u32, u32, usize, u32)>; // (rank, queued at, index, time left), smallest pops first

enum Policy {
    Fcfs,
    Sjf,
    Priority,
}
impl Policy {
    fn rank(&self, remaining: u32, priority: u32) -> u32 {
        match self {
            Policy::Fcfs => 0,
            Policy::Sjf => remaining,
            Policy::Priority => priority,
        }
    }
}

fn schedule<F, T>(jobs: &[Job<F>], quantum: u32, policy: Policy) -> Vec<T>
where
    F: Fn() -> T,
{
    let mut clock = 0;
    let mut heap = jobs
        .iter()
        .enumerate()
        .map(|(index, job)| Reverse((policy.rank(job.time, job.priority), clock, index, job.time)))
        .collect::<BinaryHeap<JobState>>();

    let mut results = Vec::with_capacity(jobs.len());
    while let Some(Reverse((.., index, left))) = heap.pop() {
        match left.cmp(&quantum) {
            Greater => {
                clock += quantum;
                let left = left - quantum;
                heap.push(Reverse((
                    policy.rank(left, jobs[index].priority),
                    clock,
                    index,
                    left,
                )));
            }
            Less | Equal => {
                clock += left;
                results.push((jobs[index].run)());
            }
        }
    }
    results
}

fn main() {
    let job = |name, time, priority| Job {
        run: move || format!("{name} done"),
        time,
        priority,
    };
    let jobs = [
        job("a", 5, 2),
        job("b", 2, 3),
        job("c", 3, 1),
        job("d", 4, 1),
    ];

    println!("fcfs     {:?}", schedule(&jobs, 2, Policy::Fcfs));
    println!("sjf      {:?}", schedule(&jobs, 2, Policy::Sjf));
    println!("priority {:?}", schedule(&jobs, 2, Policy::Priority));
}
