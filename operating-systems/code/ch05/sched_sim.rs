// ch05/sched_sim.rs: the same three policies, simulated in Rust.
use std::collections::VecDeque;

#[derive(Clone)]
struct Job {
    name: &'static str,
    arrival: i32,
    burst: i32,
}

#[derive(Clone, Copy)]
struct Stats {
    completion: i32,
    turnaround: i32,
    wait: i32,
}

// First-Come, First-Served: run jobs in arrival order, each to completion.
fn fcfs(jobs: &[Job]) -> Vec<Stats> {
    let mut out = Vec::new();
    let mut t = 0;

    for j in jobs {
        t = t.max(j.arrival) + j.burst;
        out.push(Stats {
            completion: t,
            turnaround: t - j.arrival,
            wait: t - j.arrival - j.burst,
        });
    }

    out
}

// Shortest Job First: the order in which SJF runs jobs that arrive together.
// Running this order with fcfs() gives the SJF schedule.
fn shortest_first(jobs: &[Job]) -> Vec<Job> {
    let mut sorted = jobs.to_vec();
    sorted.sort_by_key(|j| j.burst);
    sorted
}

// Round-Robin: rotate through a ready queue in fixed time slices.
fn rr(jobs: &[Job], quantum: i32) -> Vec<Stats> {
    let mut ready: VecDeque<usize> = VecDeque::new();
    let mut remaining: Vec<i32> = jobs.iter().map(|j| j.burst).collect();
    let mut completion = vec![0; jobs.len()];

    for i in 0..jobs.len() {
        ready.push_back(i);
    }

    let mut t = 0;
    while let Some(i) = ready.pop_front() {
        let run = quantum.min(remaining[i]);
        t += run;
        remaining[i] -= run;

        if remaining[i] == 0 {
            completion[i] = t;
        } else {
            ready.push_back(i);
        }
    }

    (0..jobs.len())
        .map(|i| Stats {
            completion: completion[i],
            turnaround: completion[i] - jobs[i].arrival,
            wait: completion[i] - jobs[i].arrival - jobs[i].burst,
        })
        .collect()
}

fn report(title: &str, jobs: &[Job], stats: &[Stats]) {
    let avg_turnaround: f64 =
        stats.iter().map(|s| s.turnaround as f64).sum::<f64>() / stats.len() as f64;
    let avg_wait: f64 =
        stats.iter().map(|s| s.wait as f64).sum::<f64>() / stats.len() as f64;

    println!("{title}");
    println!("  job  completion  turnaround  wait");

    for (i, j) in jobs.iter().enumerate() {
        println!(
            "  {}    {:6}   {:6}   {:6}",
            j.name, stats[i].completion, stats[i].turnaround, stats[i].wait
        );
    }

    println!("  average turnaround {avg_turnaround:.2}, average wait {avg_wait:.2}\n");
}

fn main() {
    let jobs = [
        Job { name: "A", arrival: 0, burst: 10 },
        Job { name: "B", arrival: 0, burst: 5 },
        Job { name: "C", arrival: 0, burst: 5 },
    ];

    report("FCFS (arrival order)", &jobs, &fcfs(&jobs));

    let by_burst = shortest_first(&jobs);
    report("SJF  (shortest first)", &by_burst, &fcfs(&by_burst));

    report("RR   (quantum 5)", &jobs, &rr(&jobs, 5));
}
