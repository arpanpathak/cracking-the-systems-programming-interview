//! Bounded worker pool with ordered results.
//!
//! Cloud CLIs/SDKs often fan out API calls across a bounded number of workers.
//! This example maps `Vec<T>` to `Vec<R>` with N threads and preserves input
//! order in the output. It demonstrates `Arc<Mutex<_>>`, channels, scoped
//! ownership, and panic-free dispatch.

use std::sync::{mpsc, Arc, Mutex};
use std::thread;

pub fn map_order<T, R, F>(worker_count: usize, inputs: Vec<T>, mapper: F) -> Vec<R>
where
    T: Send + 'static,
    R: Send + 'static,
    F: Fn(T) -> R + Send + Sync + 'static,
{
    assert!(worker_count > 0, "worker_count must be > 0");
    assert!(!inputs.is_empty(), "inputs must not be empty");

    let expected = inputs.len();
    let mapper = Arc::new(mapper);
    let (job_tx, job_rx) = mpsc::channel::<(usize, T)>();
    let job_rx = Arc::new(Mutex::new(job_rx));
    let (result_tx, result_rx) = mpsc::channel::<(usize, R)>();

    let mut handles = Vec::with_capacity(worker_count);
    for _worker_id in 0..worker_count {
        let mapper = Arc::clone(&mapper);
        let job_rx = Arc::clone(&job_rx);
        let result_tx = result_tx.clone();
        handles.push(thread::spawn(move || {
            loop {
                let job = {
                    let guard = job_rx.lock().expect("job_rx poisoned");
                    guard.recv()
                };
                match job {
                    Ok((idx, input)) => {
                        let output = mapper(input);
                        if result_tx.send((idx, output)).is_err() {
                            break;
                        }
                    }
                    Err(_) => break, // all senders dropped
                }
            }
        }));
    }

    // Send all jobs, then close the job channel so workers finish after draining it.
    for (idx, input) in inputs.into_iter().enumerate() {
        job_tx
            .send((idx, input))
            .expect("bounded by memory; channel only blocks until a worker receives");
    }
    drop(job_tx);

    // Drop our result sender. Only the worker clones remain, so `iter()` ends
    // after every worker exits.
    drop(result_tx);

    // Reassemble results in input order.
    let mut ordered: Vec<Option<R>> = Vec::new();
    for (idx, value) in result_rx.iter() {
        if ordered.len() <= idx {
            ordered.resize_with(idx + 1, || None);
        }
        ordered[idx] = Some(value);
    }

    for handle in handles {
        let _ = handle.join();
    }

    assert_eq!(
        ordered.len(),
        expected,
        "every job must produce exactly one result"
    );
    ordered
        .into_iter()
        .map(|value| value.expect("all results present"))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn maps_all_inputs_and_preserves_order() {
        let inputs: Vec<i32> = (0..100).collect();
        let results = map_order(4, inputs, |x| x * x);
        assert_eq!(results.len(), 100);
        for (i, value) in results.iter().enumerate() {
            assert_eq!(*value, (i as i32) * (i as i32));
        }
    }

    #[test]
    fn one_worker_works() {
        let results = map_order(1, vec![1, 2, 3], |x| x + 10);
        assert_eq!(results, vec![11, 12, 13]);
    }
}
