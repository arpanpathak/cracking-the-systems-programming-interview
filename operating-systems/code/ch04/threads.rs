// ch04/threads.rs: the same four threads in Rust.
use std::thread;

fn main() {
    let mut handles = Vec::new();
    for i in 0..4 {
        handles.push(thread::spawn(move || {
            println!("thread {i} running");
        }));
    }

    for h in handles {
        h.join().unwrap();
    }

    println!("all threads joined");
}
