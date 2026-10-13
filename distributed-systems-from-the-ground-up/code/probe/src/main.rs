//! Command probe measures how long a shard is unavailable when its leader
//! is lost. It writes keys for a number of seconds, trying each node in turn
//! until one accepts the write, and reports the longest pause between 2
//! acknowledged writes.
//!
//! Run it from code/ with:
//!
//!     cargo run --release -p probe -- --seconds 20 --acked acked.txt \
//!         --server http://127.0.0.1:7001 --server http://127.0.0.1:7002 --server http://127.0.0.1:7003

// ANCHOR: imports
use std::error::Error;
use std::fs::File;
use std::io::{BufWriter, Write};
use std::path::PathBuf;
use std::thread;
use std::time::{Duration, Instant};

use clap::Parser;
use ureq::Agent;
// ANCHOR_END: imports

// ANCHOR: options
#[derive(Parser)]
struct Options {
    /// The HTTP address of a node. Given once for each node of the shard.
    #[arg(long = "server", required = true)]
    servers: Vec<String>,

    #[arg(long, default_value_t = 20)]
    seconds: u64,

    /// The file that receives the key of every acknowledged write.
    #[arg(long)]
    acked: PathBuf,
}
// ANCHOR_END: options

// ANCHOR: probe
fn main() -> Result<(), Box<dyn Error>> {
    let options = Options::parse();
    let agent: Agent = Agent::config_builder()
        .timeout_global(Some(Duration::from_secs(2)))
        .build()
        .into();
    let mut file = BufWriter::new(File::create(&options.acked)?);

    let started = Instant::now();
    let (mut server, mut number, mut refused) = (0, 1, 0);
    let (mut last_success, mut longest, mut longest_at) = (started, Duration::ZERO, Duration::ZERO);

    while started.elapsed() < Duration::from_secs(options.seconds) {
        let key = format!("key-{number:06}");
        let address = format!("{}/v1/keys/{key}", options.servers[server]);

        if agent
            .put(&address)
            .send(format!("value of {key}"))
            .is_err()
        {
            // This node did not accept the write. Try the next one.
            refused += 1;
            server = (server + 1) % options.servers.len();
            thread::sleep(Duration::from_millis(20));

            continue;
        }

        let pause = last_success.elapsed();

        if pause > longest {
            (longest, longest_at) = (pause, started.elapsed());
        }

        last_success = Instant::now();
        writeln!(file, "{key}")?;
        number += 1;
    }

    file.flush()?;

    println!(
        "{} writes acknowledged in {} seconds, {refused} attempts refused",
        number - 1,
        options.seconds
    );
    println!(
        "the longest pause between 2 acknowledged writes was {:.2} s, ending {:.1} s after the start",
        longest.as_secs_f64(),
        longest_at.as_secs_f64()
    );

    Ok(())
}
// ANCHOR_END: probe
