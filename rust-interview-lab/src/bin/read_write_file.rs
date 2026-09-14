use std::fs;
use std::io;
use std::path::{Path, PathBuf};

// `&Path` accepts both a `&Path` and a `&PathBuf` argument; `&PathBuf` would not.
fn read_content_of_file(path: &Path) -> io::Result<String> {
    fs::read_to_string(path)
}

fn main() -> io::Result<()> {
    fs::write("hello.txt", "Hello, NVIDIA!\n")?;

    // `join` builds a new PathBuf and leaves `base_dir` unchanged.
    let base_dir = PathBuf::from(".");
    let joined_path = base_dir.join("hello.txt");

    // `push` mutates the PathBuf in place instead of returning a new one.
    let mut mut_base_dir = PathBuf::from(".");
    mut_base_dir.push("hello.txt");

    let text = read_content_of_file(&joined_path)?;
    println!("File contents (via .join()):\n{}", text);

    let text_inplace = read_content_of_file(&mut_base_dir)?;
    println!("File contents (via .push()):\n{}", text_inplace);

    Ok(())
}
