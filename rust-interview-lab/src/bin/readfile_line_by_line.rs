use std::fs::File;
use std::io::{BufRead, BufReader}; // BufRead brings `lines()` into scope.

fn main() -> std::io::Result<()> {
    let file = File::open("log.txt")?;
    let reader = BufReader::new(file);

    for (i, line) in reader.lines().enumerate() {
        let line = line?;
        println!("{}: {}", i + 1, line);
    }

    Ok(())
}