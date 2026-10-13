//! Models the Completely Fair Scheduler: every runnable task has a virtual
//! runtime, the scheduler always runs the task with the smallest one, and a
//! task's virtual runtime advances more slowly the larger its weight.
//!
//! Run it from code/rust with:
//!
//! ```text
//! cargo run -p cfs
//! ```

// ANCHOR: imports
use std::collections::BTreeSet;
// ANCHOR_END: imports

// ANCHOR: weights
/// The kernel's table `sched_prio_to_weight`: the weight of each nice value
/// from -20 to 19. Each step of nice changes the weight by about 25%.
const WEIGHTS: [u64; 40] = [
    88761, 71755, 56483, 46273, 36291, 29154, 23254, 18705, 14949, 11916, 9548, 7620, 6100, 4904,
    3906, 3121, 2501, 1991, 1586, 1277, 1024, 820, 655, 526, 423, 335, 272, 215, 172, 137, 110, 87,
    70, 56, 45, 36, 29, 23, 18, 15,
];

/// The time a task runs before the scheduler chooses again, in nanoseconds.
const SLICE: u64 = 1_000_000;

/// One schedulable entity. `vruntime` is its virtual runtime in nanoseconds,
/// and `slices` counts how often it has run.
struct Task {
    name: &'static str,
    weight: u64,
    vruntime: u64,
    slices: u64,
}

impl Task {
    fn new(name: &'static str, nice: i32) -> Task {
        Task {
            name,
            weight: WEIGHTS[(nice + 20) as usize],
            vruntime: 0,
            slices: 0,
        }
    }
}
// ANCHOR_END: weights

// ANCHOR: queue
/// The runnable tasks, ordered by virtual runtime with the name as a
/// tie-break. `runnable` holds the order and `tasks` holds the tasks, indexed
/// by the number in the key. The kernel keeps the same order in a red-black
/// tree and takes the leftmost node.
#[derive(Default)]
struct Scheduler {
    tasks: Vec<Task>,
    runnable: BTreeSet<(u64, &'static str, usize)>,
    min_vruntime: u64,
}

impl Scheduler {
    fn enqueue(&mut self, id: usize) {
        let task = &self.tasks[id];

        self.runnable.insert((task.vruntime, task.name, id));
    }
}
// ANCHOR_END: queue

// ANCHOR: tick
impl Scheduler {
    /// Runs the task with the smallest virtual runtime for one slice and
    /// returns its number. The task is charged `SLICE * 1024 / weight`, so a
    /// task of weight 1024 is charged real time and a heavier task is charged
    /// less.
    fn tick(&mut self) -> Option<usize> {
        let (_, _, id) = self.runnable.pop_first()?;
        let task = &mut self.tasks[id];

        task.vruntime += SLICE * 1024 / task.weight;
        task.slices += 1;

        self.enqueue(id);

        if let Some(&(leftmost, _, _)) = self.runnable.first() {
            self.min_vruntime = self.min_vruntime.max(leftmost);
        }

        Some(id)
    }

    /// Makes a task runnable and returns its number. With `place` set, a task
    /// that slept is moved forward to the queue's minimum, so that it cannot
    /// claim the time it did not use while it slept.
    fn wake(&mut self, mut task: Task, place: bool) -> usize {
        if place {
            task.vruntime = task.vruntime.max(self.min_vruntime);
        }

        self.tasks.push(task);
        self.enqueue(self.tasks.len() - 1);

        self.tasks.len() - 1
    }
}
// ANCHOR_END: tick

// ANCHOR: share
/// Runs a task of nice 0 against a task of the given nice value for 2000
/// slices and prints each task's share, rounded to the nearest 5%.
fn share(nice: i32) {
    let mut scheduler = Scheduler::default();

    let first = scheduler.wake(Task::new("A", 0), true);
    let second = scheduler.wake(Task::new("B", nice), true);

    for _ in 0..2000 {
        scheduler.tick();
    }

    let (a, b) = (
        scheduler.tasks[first].slices,
        scheduler.tasks[second].slices,
    );
    let percent = (200 * a / (a + b) + 5) / 10 * 5;

    println!(
        "nice 0 and nice {nice} on 1 CPU: {percent}% and {}%",
        100 - percent
    );
}
// ANCHOR_END: share

// ANCHOR: order
/// Prints which task runs in each of the first 12 slices.
fn order() {
    let mut scheduler = Scheduler::default();

    for task in [Task::new("A", 0), Task::new("B", 0), Task::new("C", 5)] {
        scheduler.wake(task, true);
    }

    let mut names = Vec::new();

    for _ in 0..12 {
        if let Some(id) = scheduler.tick() {
            names.push(scheduler.tasks[id].name);
        }
    }

    println!("A and B at nice 0, C at nice 5: {}", names.join(" "));
}
// ANCHOR_END: order

// ANCHOR: sleeper
/// Lets A and B run for 200 slices, wakes C with a virtual runtime of 0, and
/// counts how many of the next 30 slices C receives.
fn sleeper(place: bool) -> u64 {
    let mut scheduler = Scheduler::default();

    scheduler.wake(Task::new("A", 0), true);
    scheduler.wake(Task::new("B", 0), true);

    for _ in 0..200 {
        scheduler.tick();
    }

    let c = scheduler.wake(Task::new("C", 0), place);

    for _ in 0..30 {
        scheduler.tick();
    }

    scheduler.tasks[c].slices
}
// ANCHOR_END: sleeper

fn main() {
    for nice in [0, 5, 10] {
        share(nice);
    }

    order();

    println!(
        "C wakes with its old virtual runtime: it receives {} of the next 30 slices",
        sleeper(false)
    );
    println!(
        "C wakes and is placed at the minimum: it receives {} of the next 30 slices",
        sleeper(true)
    );
}
