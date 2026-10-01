//! Mapping a file into memory with `mmap`.
//!
//! A mapping makes a file's bytes addressable like a slice. The kernel loads a
//! page the first time it is touched, which shows up as a page fault. The flags
//! decide where writes go: through a `MAP_SHARED` mapping they reach the file,
//! and through a `MAP_PRIVATE` mapping they stay in a private copy of the page.
//!
//! Run with: cargo run --bin mmap_file

use std::{
    fs::{self, File},
    io,
    os::fd::AsRawFd,
    path::Path,
    ptr::NonNull,
    slice,
};

/// A file mapped into this process's address space. Unmapped when dropped.
struct Mapping {
    ptr: NonNull<u8>,
    len: usize,
}

impl Mapping {
    /// Map the first `len` bytes of `file` for reading and writing.
    ///
    /// `shared` chooses `MAP_SHARED`, whose writes reach the file, over
    /// `MAP_PRIVATE`, whose writes stay in this process.
    fn new(file: &File, len: usize, shared: bool) -> io::Result<Self> {
        let flags = if shared {
            libc::MAP_SHARED
        } else {
            libc::MAP_PRIVATE
        };

        // SAFETY: a null address lets the kernel choose where to place the
        // mapping, and the descriptor is open for reading and writing. The
        // result is checked against MAP_FAILED before it is used.
        let address = unsafe {
            libc::mmap(
                std::ptr::null_mut(),
                len,
                libc::PROT_READ | libc::PROT_WRITE,
                flags,
                file.as_raw_fd(),
                0,
            )
        };
        if address == libc::MAP_FAILED {
            return Err(io::Error::last_os_error());
        }

        let ptr = NonNull::new(address.cast::<u8>()).ok_or_else(io::Error::last_os_error)?;
        Ok(Self { ptr, len })
    }

    fn bytes(&self) -> &[u8] {
        // SAFETY: the mapping is `len` bytes long and stays valid until drop.
        unsafe { slice::from_raw_parts(self.ptr.as_ptr(), self.len) }
    }

    fn bytes_mut(&mut self) -> &mut [u8] {
        // SAFETY: as in `bytes`, and `&mut self` makes this the only borrow.
        unsafe { slice::from_raw_parts_mut(self.ptr.as_ptr(), self.len) }
    }

    /// Write the changed pages of a shared mapping back to the file now.
    fn sync(&self) -> io::Result<()> {
        // SAFETY: the range is exactly the mapping created in `new`.
        let result = unsafe { libc::msync(self.ptr.as_ptr().cast(), self.len, libc::MS_SYNC) };
        if result == 0 {
            Ok(())
        } else {
            Err(io::Error::last_os_error())
        }
    }
}

impl Drop for Mapping {
    fn drop(&mut self) {
        // SAFETY: the range is exactly the mapping created in `new`, and no
        // borrow of it can outlive `self`.
        unsafe {
            libc::munmap(self.ptr.as_ptr().cast(), self.len);
        }
    }
}

/// The size of one page of memory on this machine.
fn page_size() -> usize {
    // SAFETY: `sysconf` reads a system constant and has no side effects.
    let size = unsafe { libc::sysconf(libc::_SC_PAGESIZE) };
    usize::try_from(size).expect("page size is positive")
}

/// Minor page faults this process has taken so far: faults the kernel served
/// from memory, without reading the disk.
fn minor_faults() -> u64 {
    // SAFETY: `getrusage` fills the struct it is given and nothing else.
    let usage = unsafe {
        let mut usage = std::mem::zeroed::<libc::rusage>();
        libc::getrusage(libc::RUSAGE_SELF, &mut usage);
        usage
    };
    u64::try_from(usage.ru_minflt).expect("fault count is not negative")
}

/// Read one byte from every page, so each page is touched once.
fn touch_every_page(bytes: &[u8], page: usize) -> u64 {
    bytes
        .iter()
        .step_by(page)
        .map(|&byte| u64::from(byte))
        .sum()
}

/// The first five bytes of the file at `path`, as text.
fn file_prefix(path: &Path) -> io::Result<String> {
    let bytes = fs::read(path)?;
    Ok(String::from_utf8_lossy(&bytes[..5]).into_owned())
}

fn main() -> io::Result<()> {
    const PAGES: usize = 64;

    let page = page_size();
    let len = PAGES * page;
    let path = std::env::temp_dir().join("mmap_file_demo.bin");
    fs::write(&path, vec![b'a'; len])?;
    let file = File::options()
        .read(true)
        .write(true)
        .open(&path)?;

    println!("page size {page} bytes, file {PAGES} pages ({len} bytes)\n");

    let mut shared = Mapping::new(&file, len, true)?;

    let before = minor_faults();
    touch_every_page(shared.bytes(), page);
    let first = minor_faults() - before;

    let before = minor_faults();
    touch_every_page(shared.bytes(), page);
    let second = minor_faults() - before;

    println!("first pass over the mapping:  {first} minor faults");
    println!("second pass over the mapping: {second} minor faults\n");

    shared.bytes_mut()[..5].copy_from_slice(b"HELLO");
    shared.sync()?;
    drop(shared);
    println!(
        "after writing HELLO through MAP_SHARED, the file starts with {:?}",
        file_prefix(&path)?
    );

    let mut private = Mapping::new(&file, len, false)?;
    private.bytes_mut()[..5].copy_from_slice(b"world");
    println!(
        "after writing world through MAP_PRIVATE, the mapping holds {:?}",
        String::from_utf8_lossy(&private.bytes()[..5])
    );
    drop(private);
    println!("and the file still starts with {:?}", file_prefix(&path)?);

    fs::remove_file(&path)
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A scratch file of `pages` pages of `b'a'`, unique to one test.
    fn scratch(name: &str, pages: usize) -> (std::path::PathBuf, File, usize) {
        let len = pages * page_size();
        let path = std::env::temp_dir().join(format!("mmap_file_test_{name}.bin"));
        fs::write(&path, vec![b'a'; len]).expect("write scratch file");
        let file = File::options()
            .read(true)
            .write(true)
            .open(&path)
            .expect("open scratch file");
        (path, file, len)
    }

    #[test]
    fn shared_writes_reach_the_file() {
        let (path, file, len) = scratch("shared", 2);
        let mut mapping = Mapping::new(&file, len, true).expect("map");
        mapping.bytes_mut()[..5].copy_from_slice(b"HELLO");
        mapping.sync().expect("msync");
        drop(mapping);
        assert_eq!(file_prefix(&path).expect("read"), "HELLO");
        fs::remove_file(path).expect("remove");
    }

    #[test]
    fn private_writes_stay_in_the_process() {
        let (path, file, len) = scratch("private", 2);
        let mut mapping = Mapping::new(&file, len, false).expect("map");
        mapping.bytes_mut()[..5].copy_from_slice(b"world");
        assert_eq!(&mapping.bytes()[..5], b"world");
        drop(mapping);
        assert_eq!(file_prefix(&path).expect("read"), "aaaaa");
        fs::remove_file(path).expect("remove");
    }
}
