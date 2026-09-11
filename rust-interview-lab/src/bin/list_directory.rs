use std::fs;
use std::io;

fn main() -> io::Result<()> {
    for entry in fs::read_dir(".")? {
        let entry = entry?;
        let path = entry.path();

        if path.is_dir() {
            println!("[DIR]  {}", path.display());
        } else {
            println!("[FILE] {}", path.display());
        }
    }
    Ok(())
}
