#[derive(Debug, Default, Clone, Copy)]
struct Job {
    start: u32,
    end: u32,
    profit: u64,
}

fn max_profit(mut jobs: Vec<Job>) -> u64 {
    // Sort by end time so every job that could come before
    // job `i` in a schedule sits somewhere in jobs[..i].
    jobs.sort_unstable_by_key(|job| job.end);

    // dp[i] = best profit achievable using only the first `i` jobs.
    let mut dp = vec![0; jobs.len() + 1];

    for (i, job) in jobs.iter().enumerate() {
        // Binary search for how many earlier jobs finish by the time
        // this one starts. Those are exactly the jobs compatible with it,
        // and since they form a prefix, dp[prev] is their best profit.
        let prev = jobs[..i].partition_point(|j| j.end <= job.start);

        // Either skip this job (keep dp[i]),
        // or take it on top of the best compatible prefix.
        dp[i + 1] = dp[i].max(dp[prev] + job.profit);
    }

    // After considering every job, the last entry holds the answer.
    dp[jobs.len()]
}

fn main() {
    let jobs = vec![
        Job { start: 1, end: 3, profit: 50 },
        Job { start: 2, end: 4, profit: 10 },
        Job { start: 3, end: 5, profit: 40 },
        Job { start: 3, end: 6, profit: 70 },
    ];

    println!("{}", max_profit(jobs)); // 120
}
