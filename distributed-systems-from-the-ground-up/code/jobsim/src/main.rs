//! Command jobsim runs a job scheduler with 3 workers. A worker takes a job
//! for a limited time, and has to report before that time ends. One worker
//! crashes in the middle of a job. The scheduler gives the job to another
//! worker, and every job is finished.
//!
//! Run it from code/ with:
//!
//!     cargo run -p jobsim

// ANCHOR: scheduler
#[derive(Clone, PartialEq)]
enum State {
    Waiting,
    /// Taken by a worker, which must finish before the deadline.
    Running {
        worker: usize,
        deadline: u64,
    },
    Done,
}

struct Job {
    state: State,
    attempts: u32,
}

struct Scheduler {
    jobs: Vec<Job>,
}

impl Scheduler {
    /// Returns to the queue every job whose worker missed its deadline.
    fn reclaim(&mut self, now: u64) {
        let overdue = self
            .jobs
            .iter_mut()
            .enumerate()
            .filter_map(|(number, job)| match job.state {
                State::Running { worker, deadline } if now >= deadline => {
                    Some((number, worker, job))
                }
                State::Waiting | State::Running { .. } | State::Done => None,
            });

        for (number, worker, job) in overdue {
            println!(
                "t={now:2}  job {number} was held by worker {worker} past its deadline: back in the queue"
            );
            job.state = State::Waiting;
        }
    }

    /// Gives a waiting job to a worker for 3 seconds.
    fn take(&mut self, worker: usize, now: u64) -> Option<usize> {
        let number = self
            .jobs
            .iter()
            .position(|job| job.state == State::Waiting)?;
        let job = &mut self.jobs[number];

        job.state = State::Running {
            worker,
            deadline: now + 3,
        };
        job.attempts += 1;

        Some(number)
    }

    /// Marks a job as done, if this worker still holds it.
    fn finish(&mut self, number: usize, worker: usize) -> bool {
        let job = &mut self.jobs[number];
        let holds = matches!(job.state, State::Running { worker: holder, .. } if holder == worker);

        if holds {
            job.state = State::Done;
        }

        holds
    }
}
// ANCHOR_END: scheduler

// ANCHOR: main
/// What 1 worker does in 1 second: it reports the job it has finished, and
/// then takes the next one. `current` is its job and the time that job ends.
fn turn(scheduler: &mut Scheduler, worker: usize, current: &mut Option<(usize, u64)>, now: u64) {
    if let Some((number, ready)) = *current
        && now >= ready
    {
        let accepted = scheduler.finish(number, worker);

        println!("t={now:2}  worker {worker} finishes job {number}: accepted {accepted}");
        *current = None;
    }

    if current.is_none()
        && let Some(number) = scheduler.take(worker, now)
    {
        println!("t={now:2}  worker {worker} takes job {number}");
        *current = Some((number, now + 2));
    }
}

fn main() {
    let job = || Job {
        state: State::Waiting,
        attempts: 0,
    };
    let mut scheduler = Scheduler {
        jobs: vec![job(), job(), job(), job(), job(), job()],
    };
    // The job each worker is doing, and the time at which it will finish.
    let mut working: Vec<Option<(usize, u64)>> = vec![None; 3];

    for now in 0..12 {
        scheduler.reclaim(now);

        // Worker 1 crashes at t=2 and does nothing from then on.
        let alive = |worker: usize| worker != 1 || now < 2;

        working
            .iter_mut()
            .enumerate()
            .filter(|turn| alive(turn.0))
            .for_each(|(worker, current)| turn(&mut scheduler, worker, current, now));
    }

    let attempts: Vec<String> = scheduler
        .jobs
        .iter()
        .map(|job| job.attempts.to_string())
        .collect();
    let done = scheduler
        .jobs
        .iter()
        .filter(|job| job.state == State::Done)
        .count();

    println!(
        "jobs done: {done} of {}, attempts per job: {}",
        scheduler.jobs.len(),
        attempts.join(" ")
    );
}
// ANCHOR_END: main
