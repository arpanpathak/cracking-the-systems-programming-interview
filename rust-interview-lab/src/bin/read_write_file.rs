use std::fs;
use std::io;
use std::path::{Path, PathBuf}; // Added Path here to change &PathBuf to &Path for idiomatic borrowing

// Fixed to be idiomatic by using &Path instead of &PathBuf, and returning the String
fn read_content_of_file(path: &Path) -> io::Result<String> {
    let content = fs::read_to_string(path)?;
    Ok(content)
}

fn main() -> io::Result<()> {
    // Write a file (creates or overwrites)
    fs::write("hello.txt", "Hello, NVIDIA!\n")?;

    // --- Demo 1: Non-mutating .join() ---
    let base_dir = PathBuf::from(".");
    let joined_path = base_dir.join("hello.txt");

    // --- Demo 2: In-place .push() ---
    let mut mut_base_dir = PathBuf::from(".");
    mut_base_dir.push("hello.txt");

    // Read it back as a String using your function and a joined path
    let text = read_content_of_file(&joined_path)?;
    println!("File contents (via .join()):\n{}", text);

    let text_inplace = read_content_of_file(&mut_base_dir)?;
    println!("File contents (via .push()):\n{}", text_inplace);

    Ok(())
}
