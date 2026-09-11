use std::fs;
use std::io;
use std::path::Path;

fn walk(dir: &Path) -> io::Result<()> {
    for entry in fs::read_dir(dir)? {
        let entry = entry?;
        let path = entry.path();
        let file_type = entry.file_type()?;

        if file_type.is_dir() {
            println!("[DIR]  {}", path.display());
            walk(&path)?;
        } else {
            println!("[FILE] {}", path.display());
        }
    }
    Ok(())
}

fn main() -> io::Result<()> {
    walk(Path::new("."))?;
    Ok(())
}