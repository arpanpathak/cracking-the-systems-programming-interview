use std::fs::File;
use std::io::{BufRead, BufReader}; // Huh1 You beed to import this explicitely, interesting!

fn main() -> std::io::Result<()> {
    let file = File::open("log.txt")?;
    let reader = BufReader::new(file);

    for (i, line) in reader.lines().enumerate() {
        let line = line?;
        println!("{}: {}", i + 1, line);
    }

    Ok(())
}