// ch19/priority_workers_unwrap.rs: version 1, with unwrap on every lock.
use std::{
    cmp::Reverse,
    collections::BinaryHeap,
    sync::Mutex,
    thread,
    time::{Duration, Instant},
};

struct Job<F> {
    run: F,
    time: u32,
    priority: u32,
}

// Reverse<(rank, time queued, job_index)>
type JobState = Reverse<(u32, Duration, usize)>;

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

fn schedule<F, T>(jobs: &[Job<F>], workers: usize, policy: Policy) -> Vec<T>
where
    F: Fn() -> T + Sync,
    T: Send,
{
    let start = Instant::now();
    let heap = Mutex::new(
        jobs.iter()
            .enumerate()
            .map(|(index, job)| {
                Reverse((policy.rank(job.time, job.priority), start.elapsed(), index))
            })
            .collect::<BinaryHeap<JobState>>(),
    );
    let results = Mutex::new(Vec::with_capacity(jobs.len()));

    thread::scope(|s| {
        for _ in 0..workers {
            s.spawn(|| {
                loop {
                    let next = heap.lock().unwrap().pop();
                    let Some(Reverse((.., index))) = next else {
                        break;
                    };
                    let out = (jobs[index].run)();
                    results.lock().unwrap().push(out);
                }
            });
        }
    });

    results.into_inner().unwrap()
}

fn main() {
    let jobs: [Job<fn() -> &'static str>; 4] = [
        Job {
            run: || {
                thread::sleep(Duration::from_millis(50));
                "a"
            },
            time: 5,
            priority: 2,
        },
        Job {
            run: || {
                thread::sleep(Duration::from_millis(20));
                "b"
            },
            time: 2,
            priority: 3,
        },
        Job {
            run: || {
                thread::sleep(Duration::from_millis(30));
                "c"
            },
            time: 3,
            priority: 1,
        },
        Job {
            run: || {
                thread::sleep(Duration::from_millis(40));
                "d"
            },
            time: 4,
            priority: 1,
        },
    ];

    println!("fcfs     {:?}", schedule(&jobs, 2, Policy::Fcfs));
    println!("sjf      {:?}", schedule(&jobs, 2, Policy::Sjf));
    println!("priority {:?}", schedule(&jobs, 2, Policy::Priority));
}
