use std::{
    sync::{
        Arc,
        atomic::{AtomicUsize, Ordering},
    },
    thread,
};

use systems_lab::problems::drills::{
    BlockingQueue,
    HashRing,
    Port,
    Route,
    Semaphore,
    SpinLock,
    ThreadPool,
    count_parallel,
    parallel_sum,
    parse_request_head,
    retry,
};

fn main() {
    // Thread-safe counter
    println!("count_parallel(4, 1000) = {}", count_parallel(4, 1000));

    // Scoped threads
    let values: Vec<i32> = (1..=100).collect();

    println!("parallel_sum(1..=100) = {}", parallel_sum(&values));

    // Spin lock
    let lock = SpinLock::new(0);

    thread::scope(|scope| {
        for _ in 0..4 {
            scope.spawn(|| {
                for _ in 0..1000 {
                    *lock.lock() += 1;
                }
            });
        }
    });

    println!("spin lock total = {}", *lock.lock());

    // Semaphore
    let semaphore = Semaphore::new(2);
    let first = semaphore.try_acquire();
    let second = semaphore.try_acquire();
    let third = semaphore.try_acquire();

    println!("3 try_acquire calls with 2 permits = {first}, {second}, {third}");

    semaphore.release();

    println!("try_acquire after release = {}", semaphore.try_acquire());

    // Bounded blocking queue
    let queue = BlockingQueue::new(2);

    let received = thread::scope(|scope| {
        scope.spawn(|| {
            for item in 1..=5 {
                queue
                    .push(item)
                    .expect("queue closed early");
            }

            queue.close();
        });

        let mut received = Vec::new();

        while let Some(item) = queue.pop() {
            received.push(item);
        }

        received
    });

    println!("blocking queue received {received:?}");

    // Thread pool
    let completed = Arc::new(AtomicUsize::new(0));
    let pool = ThreadPool::new(4);

    for _ in 0..8 {
        let completed = Arc::clone(&completed);

        pool.execute(move || {
            completed.fetch_add(1, Ordering::SeqCst);
        });
    }

    drop(pool); // joins every worker

    println!(
        "thread pool completed {} jobs",
        completed.load(Ordering::SeqCst)
    );

    // Retry with exponential backoff
    let mut attempts = 0;

    let result: Result<&str, &str> = retry(
        5,
        || {
            attempts += 1;

            if attempts < 3 {
                Err("timeout")
            } else {
                Ok("connected")
            }
        },
        |_| true,
    );

    println!("retry = {result:?} after {attempts} attempts");

    // Consistent hashing ring
    let keys = ["job-1", "job-2", "job-3", "job-4"];
    let owners = |ring: &HashRing| -> Vec<String> {
        keys.iter()
            .map(|key| {
                ring.get(key)
                    .unwrap_or("none")
                    .to_string()
            })
            .collect()
    };

    let mut ring = HashRing::new();
    ring.add("node-a", 64);
    ring.add("node-b", 64);

    println!("owners with 2 nodes = {:?}", owners(&ring));

    ring.add("node-c", 64);

    println!("owners with 3 nodes = {:?}", owners(&ring));

    // HTTP request head
    let request = "GET /v1/gpu-workloads/wl-7 HTTP/1.1\r\nHost: api\r\nAccept: */*\r\n\r\n";

    if let Some(head) = parse_request_head(request) {
        println!(
            "request = {} {} {:?}",
            head.method, head.target, head.headers
        );
    }

    // Newtype and enum
    let port = Port::new(8080).map(Port::get);
    let zero = Port::new(0).map(Port::get);

    println!("Port::new(8080) = {port:?}, Port::new(0) = {zero:?}");

    let route = match Route::parse("/v1/gpu-workloads/wl-7") {
        Some(Route::Health) => "health".to_string(),
        Some(Route::List) => "list".to_string(),
        Some(Route::ById(id)) => format!("by id {id}"),
        None => "not found".to_string(),
    };

    println!("Route::parse(\"/v1/gpu-workloads/wl-7\") = {route}");
}
