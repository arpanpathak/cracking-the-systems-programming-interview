// ch06/deadlock.rs: two workers, two mutexes, opposite acquisition order.
// This program is expected to hang; the harness terminates it and records the outcome.
use std::io::{self, Write};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;

fn main() {
    let a = Arc::new(Mutex::new(()));
    let b = Arc::new(Mutex::new(()));

    let t1 = {
        let a = Arc::clone(&a);
        let b = Arc::clone(&b);
        thread::spawn(move || {
            let _la = a.lock().expect("mutex A poisoned");
            println!("worker 1 holds A");
            let _ = io::stdout().flush();
            thread::sleep(Duration::from_millis(50));

            let _lb = b.lock().expect("mutex B poisoned"); // waits for B, held by worker 2
            println!("worker 1 got A and B");
            let _ = io::stdout().flush();
        })
    };

    let t2 = {
        let a = Arc::clone(&a);
        let b = Arc::clone(&b);
        thread::spawn(move || {
            let _lb = b.lock().expect("mutex B poisoned");
            println!("worker 2 holds B");
            let _ = io::stdout().flush();
            thread::sleep(Duration::from_millis(50));

            let _la = a.lock().expect("mutex A poisoned"); // waits for A, held by worker 1
            println!("worker 2 got B and A");
            let _ = io::stdout().flush();
        })
    };

    let _ = t1.join();
    let _ = t2.join();

    println!("finished without deadlock");
}
