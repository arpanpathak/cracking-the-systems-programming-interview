// ch06/prodcons.rs: the same bounded buffer with Mutex + Condvar.
use std::collections::VecDeque;
use std::sync::{Arc, Condvar, Mutex};
use std::thread;

const CAPACITY: usize = 8;
const PRODUCERS: usize = 2;
const CONSUMERS: usize = 2;
const ITEMS_PER_PRODUCER: u64 = 100_000;

type BufferResult<T> = Result<T, &'static str>;

const POISONED: &str = "a thread panicked while it held the buffer mutex";
const PANICKED: &str = "a worker thread panicked";

struct Buffer {
    q: VecDeque<u64>,
    capacity: usize,
}

impl Buffer {
    fn is_full(&self) -> bool {
        self.q.len() == self.capacity
    }

    fn is_empty(&self) -> bool {
        self.q.is_empty()
    }
}

fn main() -> BufferResult<()> {
    let buffer = Buffer {
        q: VecDeque::new(),
        capacity: CAPACITY,
    };

    let buf = Arc::new((Mutex::new(buffer), Condvar::new()));

    let mut producers = Vec::new();
    let mut consumers = Vec::new();

    for p in 0..PRODUCERS {
        let b = Arc::clone(&buf);
        producers.push(thread::spawn(move || -> BufferResult<u64> {
            let (lock, cv) = &*b;
            let first = p as u64 * ITEMS_PER_PRODUCER + 1;
            let mut sum = 0u64;

            for v in first..first + ITEMS_PER_PRODUCER {
                let g = lock
                    .lock()
                    .map_err(|_| POISONED)?;

                let mut g = cv
                    .wait_while(g, |buffer| buffer.is_full())
                    .map_err(|_| POISONED)?;

                g.q.push_back(v);
                sum += v;

                cv.notify_all();
            }

            Ok(sum)
        }));
    }

    for _ in 0..CONSUMERS {
        let b = Arc::clone(&buf);
        consumers.push(thread::spawn(move || -> BufferResult<u64> {
            let (lock, cv) = &*b;
            let mut sum = 0u64;
            let total = PRODUCERS as u64 * ITEMS_PER_PRODUCER;

            for _ in 0..total / CONSUMERS as u64 {
                let g = lock
                    .lock()
                    .map_err(|_| POISONED)?;

                let mut g = cv
                    .wait_while(g, |buffer| buffer.is_empty())
                    .map_err(|_| POISONED)?;

                sum += g
                    .q
                    .pop_front()
                    .ok_or("the buffer was empty after the wait")?;

                cv.notify_all();
            }

            Ok(sum)
        }));
    }

    let mut produced = 0;
    let mut consumed = 0;

    for handle in producers {
        let sum = handle
            .join()
            .map_err(|_| PANICKED)?;

        produced += sum?;
    }

    for handle in consumers {
        let sum = handle
            .join()
            .map_err(|_| PANICKED)?;

        consumed += sum?;
    }

    let total = PRODUCERS as u64 * ITEMS_PER_PRODUCER;
    let expected = total * (total + 1) / 2;

    println!("produced sum {produced}");
    println!("consumed sum {consumed}");
    println!("expected     {expected}");

    let all_equal = produced == consumed && consumed == expected;
    let verdict = if all_equal { "yes" } else { "NO" };

    println!("match        {verdict}");

    Ok(())
}
