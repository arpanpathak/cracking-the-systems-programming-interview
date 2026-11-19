// ch12/files.rs: the same file operations through the Rust standard library.
use std::fs::OpenOptions;
use std::io::{Read, Seek, SeekFrom, Write};
use std::os::unix::fs::MetadataExt;

fn main() -> std::io::Result<()> {
    let path = "/tmp/osbook_files_rs.txt";

    let mut f = OpenOptions::new()
        .create(true)
        .read(true)
        .write(true)
        .truncate(true)
        .open(path)?;

    let line = b"operating systems\n";   // 18 bytes
    f.write_all(line)?;
    f.write_all(line)?;

    // The file offset is a per-open-description cursor.
    println!("offset after two writes: {}", f.stream_position()?);

    f.seek(SeekFrom::Start(0))?;
    let mut buf = [0u8; 64];
    let n = f.read(&mut buf)?;
    println!(
        "read back {n} bytes:\n{}",
        String::from_utf8_lossy(&buf[..n])
    );

    let meta = f.metadata()?;
    println!(
        "inode {}, size {} bytes, {} blocks",
        meta.ino(),
        meta.len(),
        meta.blocks()
    );

    f.sync_all()?;
    drop(f);
    std::fs::remove_file(path)?;
    Ok(())
}
