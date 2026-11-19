// ch06/trylock.rs: the same two workers, but worker 2 backs off instead of blocking.
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

            let _lb = b.lock().expect("mutex B poisoned");
            println!("worker 1 got A and B");
            let _ = io::stdout().flush();
        })
    };

    let t2 = {
        let a = Arc::clone(&a);
        let b = Arc::clone(&b);
        thread::spawn(move || {
            loop {
                {
                    let _lb = b.lock().expect("mutex B poisoned");
                    println!("worker 2 holds B, tries A");
                    let _ = io::stdout().flush();
                    if let Ok(_la) = a.try_lock() {
                        println!("worker 2 got B and A");
                        let _ = io::stdout().flush();
                        break;
                    }
                }
                thread::sleep(Duration::from_millis(5));
            }
        })
    };

    t1.join().expect("worker 1 panicked");
    t2.join().expect("worker 2 panicked");

    println!("finished without deadlock");
}
