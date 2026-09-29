use std::{
    collections::VecDeque,
    sync::{Arc, Condvar, Mutex},
    thread
};

#[derive(Default)]
struct SyncQueue {
    items: Mutex<VecDeque<i32>>,
    not_empty: Condvar,
}

impl SyncQueue {

    fn push(&self, item: i32) {
        if let Ok(mut q) = self.items.lock() {
            q.push_back(item);
            self.not_empty.notify_one();
        }
    }

    fn pop(&self) -> Option<i32> {
        let q = self.items.lock().ok()?;
        let mut q = self
            .not_empty
            .wait_while(q, |q| q.is_empty())
            .ok()?;
        q.pop_front()

    }
}

fn main() {
    let q = Arc::new(SyncQueue::default());

    // producer 
    let producer = {
        let q = Arc::clone(&q);
        thread::spawn(move || { 
            for i in 0..5 {
                q.push(i);
                println!("Producer pushed {i}");
            }
        })
    };


    let consumer = {
        let q = Arc::clone(&q);
        thread::spawn(move || { 
            for _ in 0..5 {
                println!("Cosnumer popped: {:?}", q.pop());
            }
        })
    };


    producer.join().unwrap();
    consumer.join().unwrap();

}
