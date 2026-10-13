//! Command kvctl tests a kvd server from another process or another machine.
//! `load` writes keys and records each write the server acknowledged, and
//! `verify` reads every recorded key back.
//!
//! Run it from code/ with:
//!
//!     cargo run -p kvctl -- load --server http://127.0.0.1:7001 --count 1000 --acked acked.txt
//!     cargo run -p kvctl -- verify --server http://127.0.0.1:7001 --acked acked.txt

// ANCHOR: imports
use std::error::Error;
use std::fs::{self, File};
use std::io::{BufWriter, Write};
use std::path::PathBuf;

use clap::{Parser, Subcommand};
use ureq::Agent;
// ANCHOR_END: imports

// ANCHOR: options
#[derive(Parser)]
struct Options {
    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand)]
enum Command {
    /// Write keys until the count is reached or a write fails.
    Load {
        #[arg(long)]
        server: String,
        #[arg(long, default_value_t = 1000)]
        count: u32,
        /// The file that receives the key of every acknowledged write.
        #[arg(long)]
        acked: PathBuf,
    },
    /// Read back every key in the file of acknowledged writes.
    Verify {
        #[arg(long)]
        server: String,
        #[arg(long)]
        acked: PathBuf,
    },
}
// ANCHOR_END: options

// ANCHOR: load
/// Writes `count` keys. A key is recorded in `acked` only after the server
/// has answered with a success status.
fn load(agent: &Agent, server: &str, count: u32, acked: &PathBuf) -> Result<(), Box<dyn Error>> {
    let mut file = BufWriter::new(File::create(acked)?);
    let mut written = 0;

    for number in 1..=count {
        let key = format!("key-{number:06}");

        if let Err(error) = agent
            .put(format!("{server}/v1/keys/{key}"))
            .send(format!("value of {key}"))
        {
            println!("write {number} failed: {error}");

            break;
        }

        writeln!(file, "{key}")?;
        written += 1;
    }

    file.flush()?;
    println!("{written} writes acknowledged");

    Ok(())
}
// ANCHOR_END: load

// ANCHOR: verify
/// Reads every acknowledged key and compares the value with the one that
/// was written.
fn verify(agent: &Agent, server: &str, acked: &PathBuf) -> Result<(), Box<dyn Error>> {
    let keys = fs::read_to_string(acked)?;
    let (mut found, mut missing) = (0, 0);

    for key in keys.lines() {
        let value = match agent
            .get(format!("{server}/v1/keys/{key}"))
            .call()
        {
            Ok(mut response) => response
                .body_mut()
                .read_to_string()?,
            Err(ureq::Error::StatusCode(404)) => String::new(),
            Err(error) => return Err(error.into()),
        };

        if value == format!("value of {key}") {
            found += 1;
        } else {
            missing += 1;
        }
    }

    println!(
        "{} acknowledged, {found} found, {missing} missing",
        found + missing
    );

    Ok(())
}
// ANCHOR_END: verify

fn main() -> Result<(), Box<dyn Error>> {
    let agent = Agent::new_with_defaults();

    match Options::parse().command {
        Command::Load {
            server,
            count,
            acked,
        } => load(&agent, &server, count, &acked),
        Command::Verify { server, acked } => verify(&agent, &server, &acked),
    }
}
