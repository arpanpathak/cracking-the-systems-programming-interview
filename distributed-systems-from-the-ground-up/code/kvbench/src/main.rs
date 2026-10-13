//! Command kvbench writes keys to a server from several clients at once and
//! prints the number of writes per second. Every acknowledged key is added
//! to a file, in the format that `kvctl verify` reads.
//!
//! Run it from code/ with:
//!
//!     cargo run --release -p kvbench -- --server http://127.0.0.1:7001 --clients 64 --writes 200 --acked acked.txt

// ANCHOR: imports
use std::error::Error;
use std::fs;
use std::path::PathBuf;
use std::thread;
use std::time::Instant;

use clap::Parser;
use ureq::Agent;
// ANCHOR_END: imports

// ANCHOR: bench
#[derive(Parser)]
struct Options {
    #[arg(long)]
    server: String,

    /// The number of clients that write at the same time.
    #[arg(long, default_value_t = 8)]
    clients: u32,

    /// The number of writes each client makes.
    #[arg(long, default_value_t = 200)]
    writes: u32,

    #[arg(long)]
    acked: PathBuf,
}

/// The writes of one client. It returns the keys that were acknowledged.
fn client(server: &str, number: u32, writes: u32) -> Vec<String> {
    let agent = Agent::new_with_defaults();
    let mut acknowledged = Vec::new();

    for write in 1..=writes {
        let key = format!("key-{number:03}-{write:06}");
        let address = format!("{server}/v1/keys/{key}");

        if agent
            .put(&address)
            .send(format!("value of {key}"))
            .is_ok()
        {
            acknowledged.push(key);
        }
    }

    acknowledged
}

fn main() -> Result<(), Box<dyn Error>> {
    let options = Options::parse();
    let (server, writes) = (options.server.as_str(), options.writes);
    let started = Instant::now();

    let acknowledged: Vec<String> = thread::scope(|scope| {
        let clients: Vec<_> = (1..=options.clients)
            .map(|number| scope.spawn(move || client(server, number, writes)))
            .collect();

        clients
            .into_iter()
            .flat_map(|client| client.join().unwrap_or_default())
            .collect()
    });

    let seconds = started.elapsed().as_secs_f64();
    let rate = acknowledged.len() as f64 / seconds;

    fs::write(&options.acked, acknowledged.join("\n") + "\n")?;

    println!(
        "{} clients: {} writes acknowledged in {seconds:.2} s, {rate:.0} writes per second",
        options.clients,
        acknowledged.len()
    );

    Ok(())
}
// ANCHOR_END: bench
