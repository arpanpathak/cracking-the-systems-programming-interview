// ch12/sparse.rs: the same sparse-file experiment in Rust.
use std::fs::OpenOptions;
use std::io::{Read, Seek, SeekFrom, Write};
use std::os::unix::fs::MetadataExt;

fn main() -> std::io::Result<()> {
    let path = "/tmp/osbook_sparse_rs.txt";

    let mut f = OpenOptions::new()
        .create(true)
        .read(true)
        .write(true)
        .truncate(true)
        .open(path)?;

    let island = [b'a'; 4096];
    f.write_all(&island)?;                     // bytes 0..4096
    f.seek(SeekFrom::Start(4 * 1024 * 1024))?; // jump to 4 MiB
    f.write_all(&island)?;                     // bytes 4M..4M+4096
    f.set_len(8 * 1024 * 1024)?;               // extend to 8 MiB

    let meta = f.metadata()?;
    println!("logical size : {} bytes", meta.len());
    println!(
        "blocks used  : {} x 512 bytes = {} bytes",
        meta.blocks(),
        meta.blocks() * 512
    );

    // Read the hole: the file system supplies zeros.
    f.seek(SeekFrom::Start(2 * 1024 * 1024))?;
    let mut probe = [1u8; 16];
    let n = f.read(&mut probe)?;
    let all_zero = probe.iter().all(|&b| b == 0);

    println!(
        "hole at 2 MiB reads back {n} bytes, all zero: {}",
        if all_zero { "yes" } else { "no" }
    );

    drop(f);
    std::fs::remove_file(path)?;
    Ok(())
}
