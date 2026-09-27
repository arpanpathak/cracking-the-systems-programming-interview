//! A model of how a Kubernetes controller learns about objects: a server that
//! numbers every write, a reflector that lists and watches into a local cache,
//! a work queue of names, and a controller that reconciles them. It then
//! causes a burst of edits, a dropped connection, and a partition, and logs
//! how each part responds.
//!
//! Run it from `code/rust` with `cargo run -p informer`.

mod cache;
mod controller;
mod queue;
mod reflector;
mod server;

use cache::Cache;
use controller::Controller;
use queue::WorkQueue;
use reflector::Reflector;
use server::{ApiServer, Object};
use std::sync::{Arc, OnceLock};
use std::thread;
use std::time::{Duration, Instant};

/// The time the program began, for the relative timestamps in the log.
static START: OnceLock<Instant> = OnceLock::new();

/// Prints one log line to standard error, prefixed with the milliseconds
/// since the program began.
#[macro_export]
macro_rules! log {
    ($($arg:tt)*) => {
        eprintln!("{:4}ms  {}", $crate::elapsed_ms(), format!($($arg)*))
    };
}

/// Returns the milliseconds since the program began.
pub fn elapsed_ms() -> u128 {
    START.get_or_init(Instant::now).elapsed().as_millis()
}

/// Sleeps for the given number of milliseconds.
fn sleep_ms(ms: u64) {
    thread::sleep(Duration::from_millis(ms));
}

fn main() {
    START.get_or_init(Instant::now);
    let server = Arc::new(ApiServer::default());
    server
        .update(Object::new("job-a", 1))
        .expect("unconditional write");
    server
        .update(Object::new("job-b", 8))
        .expect("unconditional write");

    let cache = Arc::new(Cache::default());
    let queue = Arc::new(WorkQueue::default());
    let reflector = Reflector {
        server: Arc::clone(&server),
        cache: Arc::clone(&cache),
        queue: Arc::clone(&queue),
    };
    let controller = Controller {
        server: Arc::clone(&server),
        cache,
        queue,
    };
    thread::spawn(move || reflector.run());
    thread::spawn(move || controller.run());
    sleep_ms(100);

    log!("--- job-a is edited five times in a burst");
    for gpus in 2..=6 {
        server
            .update(Object::new("job-a", gpus))
            .expect("unconditional write");
        if gpus == 2 {
            sleep_ms(5); // the controller starts on the first edit
        }
    }
    sleep_ms(150);

    log!("--- the watch connection drops");
    server.drop_watches();
    sleep_ms(50);

    log!("--- partition: job-b is deleted and the history compacted meanwhile");
    server.partition();
    server.delete("job-b");
    server.compact();
    sleep_ms(30);
    server.heal();
    sleep_ms(150);

    let (list, version) = server.list();
    let objects: Vec<String> = list.iter().map(ToString::to_string).collect();
    log!("final state at version {version}: [{}]", objects.join(" "));
}
