use std::fs::OpenOptions;
use std::io::Write;

fn main() -> std::io::Result<()> {
    let mut file = OpenOptions::new()
        .create(true)   // create if missing
        .append(true)   // always write at the end
        .open("log.txt")?;

    writeln!(file, "New log line")?;
    writeln!(file, "Another line")?;

    Ok(())
}
