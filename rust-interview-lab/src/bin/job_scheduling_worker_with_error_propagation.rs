use std::{
    cmp::Reverse,
    collections::BinaryHeap,
    sync::Mutex,
    thread,
    time::{Duration, Instant},
};

type ScheduledJob<T, E> = Result<Vec<T>, E>;

struct Job<F> {
    run: F,
    time: u32,
    priority: u32,
}

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

fn schedule<F, T>(jobs: &[Job<F>], workers: usize, policy: Policy) -> ScheduledJob<T, String>
where
    F: Fn() -> T + Sync,
    T: Send,
{
    let start = Instant::now(); // Monotonic Clock which never goes backward.
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
            s.spawn(|| -> Result<(), String> {
                loop {
                    let Reverse((.., index)) = heap
                        .lock()
                        .map_err(|e| e.to_string())?
                        .pop()
                        .ok_or("worker polled an empty queue")?;

                    let out = (jobs[index].run)();
                    results
                        .lock()
                        .map_err(|e| e.to_string())?
                        .push(out);
                }
            });
        }
    });

    heap.into_inner()
        .map_err(|e| e.to_string())?;
    results
        .into_inner()
        .map_err(|e| e.to_string())
}

fn main() -> Result<(), String> {
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

    println!("fcfs     {:?}", schedule(&jobs, 2, Policy::Fcfs)?);
    println!("sjf      {:?}", schedule(&jobs, 2, Policy::Sjf)?);
    println!("priority {:?}", schedule(&jobs, 2, Policy::Priority)?);
    Ok(())
}
