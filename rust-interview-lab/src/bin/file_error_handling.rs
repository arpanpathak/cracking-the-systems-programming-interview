use std::fs;
use std::io;

fn read_file(path: &str) -> Result<String, io::Error> {
    fs::read_to_string(path)
}

fn main() {
    match read_file("missing.txt") {
        Ok(text) => println!("{}", text),
        Err(e) if e.kind() == io::ErrorKind::NotFound => {
            eprintln!("File not found");
        }
        Err(e) => eprintln!("Error: {}", e),
    }
}