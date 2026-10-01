//! Sending a file over a socket two ways: a read/write loop, and `sendfile`.
//!
//! The loop moves every byte through a buffer in this process: the kernel
//! copies it into the buffer on `read`, and copies it out again on `write`.
//! `sendfile` asks the kernel to move the bytes from the file to the socket
//! itself, so they never enter user space.
//!
//! Linux only. Run with: cargo run --release --bin zero_copy

#[cfg(target_os = "linux")]
mod linux {
    use std::{
        fs::{self, File},
        io::{self, Read, Write},
        net::{TcpListener, TcpStream},
        os::fd::AsRawFd,
        thread,
        time::{Duration, Instant},
    };

    /// What one transfer cost.
    pub struct Transfer {
        pub bytes: u64,
        pub syscalls: u64,
        pub elapsed: Duration,
    }

    /// A connected socket pair over loopback, with a thread on the far end
    /// that reads and discards everything until the sender closes.
    fn connected_pair() -> io::Result<(TcpStream, thread::JoinHandle<u64>)> {
        let listener = TcpListener::bind("127.0.0.1:0")?;
        let address = listener.local_addr()?;
        let sink = thread::spawn(move || {
            let (mut stream, _) = listener.accept().expect("accept");
            let mut buffer = vec![0u8; 1 << 20];
            let mut total = 0u64;
            loop {
                match stream.read(&mut buffer) {
                    Ok(0) | Err(_) => return total,
                    Ok(read) => total += read as u64,
                }
            }
        });
        Ok((TcpStream::connect(address)?, sink))
    }

    /// Send `file` with `read` into a buffer and `write` out of it.
    pub fn copy_loop(path: &str, buffer_size: usize) -> io::Result<Transfer> {
        let mut file = File::open(path)?;
        let (mut socket, sink) = connected_pair()?;
        let mut buffer = vec![0u8; buffer_size];
        let mut syscalls = 0;

        let start = Instant::now();
        loop {
            let read = file.read(&mut buffer)?;
            syscalls += 1;
            if read == 0 {
                break;
            }
            socket.write_all(&buffer[..read])?;
            syscalls += 1;
        }
        drop(socket);
        let bytes = sink.join().expect("sink thread");
        Ok(Transfer {
            bytes,
            syscalls,
            elapsed: start.elapsed(),
        })
    }

    /// Send `file` with `sendfile`, which moves the bytes inside the kernel.
    pub fn send_file(path: &str) -> io::Result<Transfer> {
        let file = File::open(path)?;
        let length = file.metadata()?.len();
        let (socket, sink) = connected_pair()?;
        let mut offset: libc::off_t = 0;
        let mut syscalls = 0;

        let start = Instant::now();
        while (offset as u64) < length {
            let remaining = (length - offset as u64) as usize;
            // SAFETY: both descriptors are open for the whole call, and the
            // kernel advances `offset` by the number of bytes it sent.
            let sent = unsafe {
                libc::sendfile(socket.as_raw_fd(), file.as_raw_fd(), &mut offset, remaining)
            };
            syscalls += 1;
            if sent < 0 {
                return Err(io::Error::last_os_error());
            }
        }
        drop(socket);
        let bytes = sink.join().expect("sink thread");
        Ok(Transfer {
            bytes,
            syscalls,
            elapsed: start.elapsed(),
        })
    }

    /// Write a scratch file of `size` bytes and return its path.
    pub fn scratch_file(size: usize) -> io::Result<String> {
        let path = std::env::temp_dir().join("zero_copy_demo.bin");
        fs::write(&path, vec![b'z'; size])?;
        Ok(path.to_string_lossy().into_owned())
    }
}

#[cfg(target_os = "linux")]
fn main() -> std::io::Result<()> {
    const SIZE: usize = 256 << 20;

    let path = linux::scratch_file(SIZE)?;
    // One untimed pass, so the file is in the page cache for both runs.
    linux::copy_loop(&path, 64 << 10)?;

    println!(
        "{:<22} {:>10} {:>10} {:>10} {:>12}",
        "method", "MiB", "syscalls", "ms", "MiB/s"
    );
    let runs = [
        ("read/write, 64 KiB", linux::copy_loop(&path, 64 << 10)?),
        ("sendfile", linux::send_file(&path)?),
    ];
    for (name, run) in runs {
        let mib = run.bytes as f64 / (1 << 20) as f64;
        let ms = run.elapsed.as_secs_f64() * 1000.0;
        println!(
            "{name:<22} {mib:>10.0} {:>10} {ms:>10.1} {:>12.0}",
            run.syscalls,
            mib / run.elapsed.as_secs_f64()
        );
    }

    std::fs::remove_file(&path)
}

#[cfg(not(target_os = "linux"))]
fn main() {
    eprintln!("zero_copy uses Linux sendfile; run it on Linux");
}

#[cfg(all(test, target_os = "linux"))]
mod tests {
    use super::linux;

    #[test]
    fn both_methods_deliver_every_byte() {
        let path = linux::scratch_file(3 << 20).expect("scratch file");
        assert_eq!(
            linux::copy_loop(&path, 64 << 10)
                .expect("loop")
                .bytes,
            3 << 20
        );
        assert_eq!(linux::send_file(&path).expect("sendfile").bytes, 3 << 20);
    }
}
