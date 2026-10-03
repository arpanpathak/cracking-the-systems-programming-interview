//! Choose non-overlapping jobs for a GPU, where each job needs memory and cores.
//!
//! A job runs only on a GPU with enough memory and enough cores. For one GPU the
//! task is weighted interval scheduling: sort by end time, then take or skip each
//! job. The same table is reused for every GPU, and the best GPU wins.

#[derive(Debug, Default, Clone, Copy)]
struct Gpu {
    mem_gb: u32,
    cores: u32,
}

#[derive(Debug, Default, Clone, Copy)]
struct Job {
    start: u32,
    end: u32,
    mem_gb: u32,
    cores: u32,
    profit: u64,
}

impl Gpu {
    /// A job fits when the GPU has at least its memory and at least its cores.
    fn fits(&self, job: &Job) -> bool {
        (0..=self.mem_gb).contains(&job.mem_gb) && (0..=self.cores).contains(&job.cores)
    }
}

/// The best profit from work that runs on one GPU.
///
/// Every job it picks runs on the same GPU. That is the right model when a workload
/// is pinned to one device. Spreading the jobs over several GPUs is a different
/// problem, and the chapter measures what it is worth on the sample data.
fn max_profit(gpus: &[Gpu], mut jobs: Vec<Job>) -> u64 {
    jobs.sort_unstable_by_key(|job| job.end);

    // prev[i] = how many jobs finish by the time job `i` starts. The end times
    // are sorted, so each count is the length of a prefix, found in one search.
    let prev: Vec<usize> = jobs
        .iter()
        .map(|job| jobs.partition_point(|earlier| earlier.end <= job.start))
        .collect();

    // dp[i] = best profit using only the first `i` jobs. Reused for every GPU.
    let mut dp = vec![0; jobs.len() + 1];

    let pick_jobs_dp = |gpu: &Gpu| {
        for index in 0..jobs.len() {
            let job = &jobs[index];
            dp[index + 1] = if gpu.fits(job) {
                dp[index].max(dp[prev[index]] + job.profit)
            } else {
                dp[index]
            };
        }
        dp[jobs.len()]
    };

    gpus.iter()
        .map(pick_jobs_dp)
        .max()
        .unwrap_or(0)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn large() -> Gpu {
        Gpu {
            mem_gb: 80,
            cores: 108,
        }
    }

    fn small() -> Gpu {
        Gpu {
            mem_gb: 16,
            cores: 40,
        }
    }

    fn sample_jobs() -> Vec<Job> {
        vec![
            Job {
                start: 1,
                end: 3,
                mem_gb: 12,
                cores: 20,
                profit: 50,
            },
            Job {
                start: 2,
                end: 4,
                mem_gb: 8,
                cores: 10,
                profit: 10,
            },
            Job {
                start: 3,
                end: 5,
                mem_gb: 40,
                cores: 60,
                profit: 40,
            },
            Job {
                start: 3,
                end: 6,
                mem_gb: 60,
                cores: 90,
                profit: 70,
            },
        ]
    }

    #[test]
    fn the_large_gpu_runs_the_best_pair() {
        assert_eq!(max_profit(&[large()], sample_jobs()), 120);
    }

    #[test]
    fn the_small_gpu_skips_what_does_not_fit() {
        assert_eq!(max_profit(&[small()], sample_jobs()), 50);
    }

    #[test]
    fn the_best_gpu_wins() {
        assert_eq!(max_profit(&[large(), small()], sample_jobs()), 120);
    }

    #[test]
    fn no_gpu_or_no_job_earns_nothing() {
        assert_eq!(max_profit(&[], sample_jobs()), 0);
        assert_eq!(max_profit(&[large()], Vec::new()), 0);
    }

    #[test]
    fn cores_alone_can_disqualify_a_job() {
        let jobs = vec![Job {
            start: 0,
            end: 1,
            mem_gb: 1,
            cores: 200,
            profit: 9,
        }];
        assert_eq!(max_profit(&[large()], jobs), 0);
    }
}

fn main() {
    let gpus = vec![
        Gpu {
            mem_gb: 80,
            cores: 108,
        },
        Gpu {
            mem_gb: 16,
            cores: 40,
        },
    ];

    let jobs = vec![
        Job {
            start: 1,
            end: 3,
            mem_gb: 12,
            cores: 20,
            profit: 50,
        },
        Job {
            start: 2,
            end: 4,
            mem_gb: 8,
            cores: 10,
            profit: 10,
        },
        Job {
            start: 3,
            end: 5,
            mem_gb: 40,
            cores: 60,
            profit: 40,
        },
        Job {
            start: 3,
            end: 6,
            mem_gb: 60,
            cores: 90,
            profit: 70,
        },
    ];

    println!("{}", max_profit(&gpus, jobs)); // 120
}
