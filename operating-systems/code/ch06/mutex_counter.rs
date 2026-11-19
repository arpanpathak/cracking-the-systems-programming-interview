// ch06/mutex_counter.rs: the same guarded counter in Rust.
use std::sync::{Arc, Mutex};
use std::thread;

fn main() {
    const THREADS: usize = 8;
    const ITERS: u64 = 5_000_000;

    let counter = Arc::new(Mutex::new(0u64));
    let mut handles = Vec::new();

    for _ in 0..THREADS {
        let c = Arc::clone(&counter);
        handles.push(thread::spawn(move || {
            for _ in 0..ITERS {
                *c.lock().unwrap() += 1;
            }
        }));
    }

    for h in handles {
        h.join().unwrap();
    }

    println!(
        "expected {}, observed {}",
        THREADS as u64 * ITERS,
        *counter.lock().unwrap()
    );
}
