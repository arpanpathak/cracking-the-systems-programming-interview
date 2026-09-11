//! Runs the hand-written async runtime in [`nvidia_rust_interview_lab::problems::async_mini`].
//!
//! There is no Tokio here on purpose: the point is to show that `Future`, `Waker`,
//! `Poll`, and `Pin` are enough to build an executor, and that `.await` is just
//! sugar over a state machine that is polled.
//!
//! ```bash
//! cargo run --bin async_demo
//! ```

use nvidia_rust_interview_lab::problems::async_mini::{Delay, MiniExecutor, YieldTimes, block_on};
use std::sync::Arc;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::time::{Duration, Instant};

fn main() {
    println!("== block_on drives a hand-written future ==");
    let yields = block_on(YieldTimes::new(3));
    println!("YieldTimes suspended and resumed {yields} time(s)");

    println!("\n== block_on drives an async block ==");
    let total = block_on(async {
        let first = YieldTimes::new(1).await;
        let second = YieldTimes::new(2).await;
        first + second
    });
    println!("async block finished with {total}");

    println!("\n== block_on parks the thread until the waker fires ==");
    let start = Instant::now();
    block_on(Delay::new(Duration::from_millis(50)));
    println!("Delay completed after {:?}", start.elapsed());

    println!("\n== MiniExecutor runs independent tasks ==");
    let executor = MiniExecutor::new();
    let completed = Arc::new(AtomicUsize::new(0));

    for id in 1..=3 {
        let completed = Arc::clone(&completed);
        executor.spawn(async move {
            YieldTimes::new(id).await;
            completed.fetch_add(1, Ordering::SeqCst);
            println!("task {id} completed after {id} yield(s)");
        });
    }

    executor.run();
    println!("{} task(s) completed", completed.load(Ordering::SeqCst));
}
