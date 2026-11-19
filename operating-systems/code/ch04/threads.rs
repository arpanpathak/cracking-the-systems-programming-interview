// ch04/threads.rs: the same four threads in Rust.
use std::thread;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut handles = Vec::new();
    for i in 0..4 {
        handles.push(thread::spawn(move || {
            println!("thread {i} running");
        }));
    }

    for h in handles {
        h.join().map_err(|_| "worker thread panicked")?;
    }

    println!("all threads joined");
    Ok(())
}
