//! Runs `a | b | c` the way a shell does: each command's standard output is
//! the write end of a pipe, and the next command's standard input is the read
//! end of the same pipe.
//!
//! It runs the pipelines listed in main and prints the last command's output and how each
//! command terminated.
//!
//! Run it from code/rust with:
//!
//! ```text
//! cargo run -p pipeline
//! ```

// ANCHOR: imports
use std::io::{self, PipeReader, Read};
use std::os::unix::process::ExitStatusExt;
use std::process::{Child, Command, Stdio};
// ANCHOR_END: imports

// ANCHOR: start
/// Runs the commands of a pipeline. Command `i` writes to pipe `i` and reads
/// from pipe `i - 1`; the first command reads /dev/null. Returns the children
/// and the read end of the last pipe.
fn start(stages: &[Vec<&str>]) -> io::Result<(Vec<Child>, PipeReader)> {
    let mut input = None;
    let mut children = Vec::with_capacity(stages.len());

    for stage in stages {
        let (reader, writer) = io::pipe()?;
        let stdin = input.take().map_or_else(Stdio::null, Stdio::from);

        // The `Command` owns the parent's copies of both ends. It is dropped
        // when this statement ends, which closes them and leaves the child's
        // copies as the only ones.
        let child = Command::new(stage[0])
            .args(&stage[1..])
            .stdin(stdin)
            .stdout(writer)
            .spawn()?;

        children.push(child);
        input = Some(reader);
    }

    let output = input.ok_or(io::ErrorKind::InvalidInput)?;

    Ok((children, output))
}
// ANCHOR_END: start

// ANCHOR: status
/// Waits for a command and reports how it terminated: with an exit status,
/// or by a signal.
fn ending(child: &mut Child) -> io::Result<String> {
    let status = child.wait()?;

    let text = match (status.signal(), status.code()) {
        (Some(signal), _) => format!("killed by signal {signal}"),
        (None, Some(code)) => format!("exited with status {code}"),
        (None, None) => status.to_string(),
    };

    Ok(text)
}
// ANCHOR_END: status

// ANCHOR: run
/// Starts a pipeline, reads the last command's output to the end of the
/// stream, and prints the output and each command's termination.
fn run(line: &str) -> io::Result<()> {
    let stages: Vec<Vec<&str>> = line
        .split(" | ")
        .map(|stage| stage.split_whitespace().collect())
        .collect();

    let (mut children, mut output) = start(&stages)?;

    let mut text = String::new();
    output.read_to_string(&mut text)?;

    let words: Vec<&str> = text.split_whitespace().collect();

    println!("{line}");
    println!("  output: {}", words.join(" "));

    for (stage, child) in stages.iter().zip(&mut children) {
        println!("  {}: {}", stage[0], ending(child)?);
    }

    Ok(())
}
// ANCHOR_END: run

fn main() -> io::Result<()> {
    run("seq 1 100000 | grep 7 | wc -l")?;
    run("yes | head -n 3")
}
