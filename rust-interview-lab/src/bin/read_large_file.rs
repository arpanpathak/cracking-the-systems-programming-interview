use std::fs::File;
use std::io::{self, BufRead, BufReader};

fn main() -> io::Result<()> {
    let file = File::open("large.txt")?;
    let mut reader = BufReader::new(file);
    let mut line = String::new();

    while match reader.read_line(&mut line) {
        Ok(0) => false, // EOF, stop
        Ok(_) => {
            process(line.trim_end());
            line.clear();
            true // keep reading
        }
        Err(e) if e.kind() == io::ErrorKind::InvalidData => {
            eprintln!("skipping bad line: {e}");
            line.clear();
            true
        }
        Err(e) => return Err(e), // return works inside the condition
    } {}

    Ok(())
}

fn process(line: &str) {
    println!("{line}");
}
