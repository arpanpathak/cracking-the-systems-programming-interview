use std::path::{Path, PathBuf};

fn main() {
    let dir = Path::new("/tmp");
    let file = dir.join("data.txt");

    let mut buf = PathBuf::from(dir);
    buf.push("nested");
    buf.push("file.txt");

    println!("file: {}", file.display());
    println!("buf:  {}", buf.display());
    println!("parent: {:?}", buf.parent());
    println!("file_name: {:?}", buf.file_name());
    println!("ext: {:?}", buf.extension());
}