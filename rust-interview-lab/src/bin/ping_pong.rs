use std::sync::mpsc::sync_channel;
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;

fn main() {
    let (tx, rx) = sync_channel::<u32>(0);          // <-- 0, not 1
    let rx = Arc::new(Mutex::new(rx));
    let (tx2, rx2) = (tx.clone(), Arc::clone(&rx));

    let pong = thread::spawn(move || {
        for _ in 0..5 {
            let i = rx2.lock().unwrap().recv().unwrap();  // takes ping's i
            println!("pong {i}");
            tx2.send(i).unwrap();
            thread::sleep(Duration::from_millis(500));// blocks until ping recv's
        }
    });

    for i in 0..5 {
        println!("ping {i}");
        tx.send(i).unwrap();                 // blocks until pong recv's it
        rx.lock().unwrap().recv().unwrap();  // blocks until pong printed + sent back
        thread::sleep(Duration::from_millis(500));
    }

    pong.join().unwrap();
}
