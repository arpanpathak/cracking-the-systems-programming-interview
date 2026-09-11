use std::env;
use std::thread;
use std::time::{Duration, Instant};

const SIZE: usize = 1_000_000_000;

fn seq_i32(data: &[i32]) -> (i32, Duration) {
    let t = Instant::now();
    let sum = data.iter().sum::<i32>();
    (sum, t.elapsed())
}

fn par_i32(data: &[i32], n: usize) -> (i32, Duration) {
    let t = Instant::now();
    let sum = thread::scope(|s| {
        let handles: Vec<_> = (0..n)
            .map(|i| {
                s.spawn(move || {
                    let chunk = data.len() / n;
                    let start = i * chunk;
                    let end = if i == n - 1 { data.len() } else { start + chunk };
                    data[start..end].iter().sum::<i32>()
                })
            })
            .collect();
        handles.into_iter().map(|h| h.join().unwrap()).sum::<i32>()
    });
    (sum, t.elapsed())
}

fn seq_i64(data: &[i64]) -> (i64, Duration) {
    let t = Instant::now();
    let sum = data.iter().sum::<i64>();
    (sum, t.elapsed())
}

fn par_i64(data: &[i64], n: usize) -> (i64, Duration) {
    let t = Instant::now();
    let sum = thread::scope(|s| {
        let handles: Vec<_> = (0..n)
            .map(|i| {
                s.spawn(move || {
                    let chunk = data.len() / n;
                    let start = i * chunk;
                    let end = if i == n - 1 { data.len() } else { start + chunk };
                    data[start..end].iter().sum::<i64>()
                })
            })
            .collect();
        handles.into_iter().map(|h| h.join().unwrap()).sum::<i64>()
    });
    (sum, t.elapsed())
}

fn seq_i128(data: &[i128]) -> (i128, Duration) {
    let t = Instant::now();
    let sum = data.iter().sum::<i128>();
    (sum, t.elapsed())
}

fn par_i128(data: &[i128], n: usize) -> (i128, Duration) {
    let t = Instant::now();
    let sum = thread::scope(|s| {
        let handles: Vec<_> = (0..n)
            .map(|i| {
                s.spawn(move || {
                    let chunk = data.len() / n;
                    let start = i * chunk;
                    let end = if i == n - 1 { data.len() } else { start + chunk };
                    data[start..end].iter().sum::<i128>()
                })
            })
            .collect();
        handles.into_iter().map(|h| h.join().unwrap()).sum::<i128>()
    });
    (sum, t.elapsed())
}

fn main() {
    let n: usize = env::args()
        .nth(1)
        .and_then(|s| s.parse().ok())
        .unwrap_or(8);

    {
        let data: Vec<i32> = vec![1; SIZE];
        let (s1, t1) = seq_i32(&data);
        let (s2, t2) = par_i32(&data, n);
        assert_eq!(s1, s2);
        println!("i32   seq sum = {s1}, elapsed = {t1:?}");
        println!("i32   par sum = {s2}, elapsed = {t2:?}  (n = {n})");
    }

    {
        let data: Vec<i64> = vec![1; SIZE];
        let (s1, t1) = seq_i64(&data);
        let (s2, t2) = par_i64(&data, n);
        assert_eq!(s1, s2);
        println!("i64   seq sum = {s1}, elapsed = {t1:?}");
        println!("i64   par sum = {s2}, elapsed = {t2:?}  (n = {n})");
    }

    {
        let data: Vec<i128> = vec![1; SIZE];
        let (s1, t1) = seq_i128(&data);
        let (s2, t2) = par_i128(&data, n);
        assert_eq!(s1, s2);
        println!("i128  seq sum = {s1}, elapsed = {t1:?}");
        println!("i128  par sum = {s2}, elapsed = {t2:?}  (n = {n})");
    }
}
