use std::fs;
use std::io;

fn main() -> io::Result<()> {
    fs::write("a.txt", "hello")?;

    fs::copy("a.txt", "b.txt")?;
    fs::rename("b.txt", "c.txt")?;
    fs::remove_file("a.txt")?;

    println!("Done");
    Ok(())
}
