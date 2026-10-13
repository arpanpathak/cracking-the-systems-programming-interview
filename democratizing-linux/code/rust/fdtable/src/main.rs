//! Models the kernel's file tables in user space: names that refer to inodes,
//! open file descriptions that refer to an inode and hold an offset, and a
//! descriptor table for each process. Every object counts the references to
//! it and is released when the count reaches 0. The program repeats the
//! experiments of fdfacts on the model and prints the same lines.
//!
//! Run it from code/rust with:
//!
//! ```text
//! cargo run -p fdtable
//! ```

// ANCHOR: imports
use std::collections::HashMap;
use std::fmt;
// ANCHOR_END: imports

// ANCHOR: inode
/// The errors carry the names of the kernel's error codes for the same cases.
#[derive(Debug)]
enum Error {
    BadDescriptor,
    TooManyFiles,
    NoEntry,
}

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(match self {
            Error::BadDescriptor => "EBADF",
            Error::TooManyFiles => "EMFILE",
            Error::NoEntry => "ENOENT",
        })
    }
}

/// A file: its contents and 2 reference counts. `links` counts the names
/// that refer to it, and `opens` counts the open file descriptions that refer
/// to it. Its number is its key in the kernel's table of inodes.
#[derive(Default)]
struct Inode {
    data: Vec<u8>,
    links: u32,
    opens: u32,
}

/// The kernel's tables: a single directory that maps names to inode numbers,
/// the inodes, and every open file description.
#[derive(Default)]
struct Kernel {
    names: HashMap<&'static str, u64>,
    inodes: HashMap<u64, Inode>,
    open_files: Vec<Description>,
    next: u64,
}

impl Kernel {
    /// Returns the number of a new inode with no name.
    fn allocate(&mut self) -> u64 {
        self.next += 1;
        self.inodes.insert(self.next, Inode::default());

        self.next
    }

    fn inode(&mut self, number: u64) -> Result<&mut Inode, Error> {
        self.inodes.get_mut(&number).ok_or(Error::NoEntry)
    }
}
// ANCHOR_END: inode

// ANCHOR: names
impl Kernel {
    /// Makes an empty file with one name and returns its inode number.
    fn create(&mut self, name: &'static str) -> Result<u64, Error> {
        let number = self.allocate();

        self.inode(number)?.links = 1;
        self.names.insert(name, number);

        Ok(number)
    }

    /// Adds a second name for an existing file.
    fn link(&mut self, existing: &str, added: &'static str) -> Result<(), Error> {
        let number = *self.names.get(existing).ok_or(Error::NoEntry)?;

        self.inode(number)?.links += 1;
        self.names.insert(added, number);

        Ok(())
    }

    /// Removes a name. The file itself is removed only when `release` finds
    /// no other reference to it.
    fn unlink(&mut self, name: &str) -> Result<(), Error> {
        let number = self.names.remove(name).ok_or(Error::NoEntry)?;

        self.inode(number)?.links -= 1;
        self.release(number);

        Ok(())
    }

    /// Frees an inode that has no name and is not open.
    fn release(&mut self, number: u64) {
        if let Some(file) = self.inodes.get(&number)
            && file.links == 0
            && file.opens == 0
        {
            self.inodes.remove(&number);
        }
    }
}
// ANCHOR_END: names

// ANCHOR: tables
/// An open file description: the state created by one open. `file` is the
/// number of its inode, and `refs` counts the descriptors, in all processes,
/// that refer to it.
struct Description {
    file: u64,
    offset: usize,
    append_mode: bool,
    refs: u32,
}

/// One entry of a process's table. `open` is the index of a description in
/// the kernel's table. The close-on-exec flag belongs to the entry.
#[derive(Clone, Copy)]
struct Descriptor {
    open: usize,
    cloexec: bool,
}

/// A process is its descriptor table. The index of an entry is the file
/// descriptor, `None` is a free number, and `limit` is the number of entries
/// the process may use.
struct Process {
    table: Vec<Option<Descriptor>>,
    limit: usize,
}

impl Kernel {
    /// Adds a description for an inode and returns its index.
    fn describe(&mut self, file: u64) -> usize {
        self.open_files.push(Description {
            file,
            offset: 0,
            append_mode: false,
            refs: 0,
        });

        self.open_files.len() - 1
    }

    /// Returns a process with descriptors 0, 1 and 2 open on a terminal,
    /// which is a file without a name.
    fn process(&mut self) -> Result<Process, Error> {
        let mut process = Process {
            table: Vec::new(),
            limit: 1024,
        };

        let terminal = self.allocate();
        let open = self.describe(terminal);

        self.inode(terminal)?.opens = 1;

        for _ in 0..3 {
            self.install(&mut process, open)?;
        }

        Ok(process)
    }
}
// ANCHOR_END: tables

// ANCHOR: install
impl Kernel {
    /// Puts a description in the lowest free entry, counts the new reference,
    /// and returns the number of the entry.
    fn install(&mut self, process: &mut Process, open: usize) -> Result<usize, Error> {
        let fd = process
            .table
            .iter()
            .take_while(|entry| entry.is_some())
            .count();

        if fd >= process.limit {
            return Err(Error::TooManyFiles);
        }

        if fd == process.table.len() {
            process.table.push(None);
        }

        self.open_files[open].refs += 1;
        process.table[fd] = Some(Descriptor {
            open,
            cloexec: false,
        });

        Ok(fd)
    }

    /// Finds the inode behind a name and creates a description for it, with
    /// offset 0.
    fn open(&mut self, process: &mut Process, name: &str) -> Result<usize, Error> {
        let file = *self.names.get(name).ok_or(Error::NoEntry)?;
        let open = self.describe(file);
        let fd = self.install(process, open)?;

        self.inode(file)?.opens += 1;

        Ok(fd)
    }

    /// Makes a second descriptor for an existing description.
    fn dup(&mut self, process: &mut Process, fd: usize) -> Result<usize, Error> {
        let entry = process.lookup(fd)?;

        self.install(process, entry.open)
    }
}

impl Process {
    /// Returns the entry of a descriptor.
    fn lookup(&self, fd: usize) -> Result<Descriptor, Error> {
        self.table
            .get(fd)
            .copied()
            .flatten()
            .ok_or(Error::BadDescriptor)
    }
}
// ANCHOR_END: install

// ANCHOR: close
impl Kernel {
    /// Frees an entry and drops its reference to the description. The last
    /// reference closes the description, which drops its reference to the
    /// inode.
    fn close(&mut self, process: &mut Process, fd: usize) -> Result<(), Error> {
        let entry = process.lookup(fd)?;
        let open = &mut self.open_files[entry.open];

        process.table[fd] = None;
        open.refs -= 1;

        if open.refs == 0 {
            let file = open.file;

            self.inode(file)?.opens -= 1;
            self.release(file);
        }

        Ok(())
    }

    /// Makes descriptor `to` refer to the description of descriptor `from`,
    /// closing whatever `to` referred to before.
    fn dup2(&mut self, process: &mut Process, from: usize, to: usize) -> Result<(), Error> {
        let entry = process.lookup(from)?;

        if from == to {
            return Ok(());
        }

        if process.lookup(to).is_ok() {
            self.close(process, to)?;
        }

        if process.table.len() <= to {
            process.table.resize(to + 1, None);
        }

        self.open_files[entry.open].refs += 1;
        process.table[to] = Some(Descriptor {
            open: entry.open,
            cloexec: false,
        });

        Ok(())
    }
}
// ANCHOR_END: close

// ANCHOR: io
impl Kernel {
    /// Copies `data` into the file at the description's offset and advances
    /// the offset. In append mode the offset first moves to the end of the
    /// file.
    fn write(&mut self, process: &Process, fd: usize, data: &str) -> Result<(), Error> {
        let open = &mut self.open_files[process.lookup(fd)?.open];
        let file = self.inodes.get_mut(&open.file).ok_or(Error::NoEntry)?;

        if open.append_mode {
            open.offset = file.data.len();
        }

        let end = open.offset + data.len();

        if end > file.data.len() {
            file.data.resize(end, 0);
        }

        file.data[open.offset..end].copy_from_slice(data.as_bytes());
        open.offset = end;

        Ok(())
    }

    /// Returns up to `n` bytes from the description's offset and advances the
    /// offset.
    fn read(&mut self, process: &Process, fd: usize, n: usize) -> Result<String, Error> {
        let open = &mut self.open_files[process.lookup(fd)?.open];
        let file = self.inodes.get(&open.file).ok_or(Error::NoEntry)?;

        let end = (open.offset + n).min(file.data.len());
        let data = String::from_utf8_lossy(&file.data[open.offset..end]).into_owned();

        open.offset = end;

        Ok(data)
    }
}
// ANCHOR_END: io

// ANCHOR: fork
impl Kernel {
    /// Returns a child whose table has a copy of every entry. The copies
    /// refer to the parent's descriptions, and each copy is counted.
    fn fork(&mut self, parent: &Process) -> Process {
        for entry in parent.table.iter().flatten() {
            self.open_files[entry.open].refs += 1;
        }

        Process {
            table: parent.table.clone(),
            limit: parent.limit,
        }
    }

    /// Closes every descriptor that has the close-on-exec flag.
    fn exec(&mut self, process: &mut Process) -> Result<(), Error> {
        for fd in 0..process.table.len() {
            if process.table[fd].is_some_and(|entry| entry.cloexec) {
                self.close(process, fd)?;
            }
        }

        Ok(())
    }
}
// ANCHOR_END: fork

// ANCHOR: experiments
fn numbers(kernel: &mut Kernel) -> Result<(), Error> {
    let mut process = kernel.process()?;

    kernel.close(&mut process, 0)?;

    let fd = kernel.open(&mut process, "file")?;
    println!("descriptor 0 closed: the next open returns {fd}");

    Ok(())
}

fn limit(kernel: &mut Kernel) -> Result<(), Error> {
    let mut process = kernel.process()?;
    let mut highest = 0;

    process.limit = 32;

    let error = loop {
        match kernel.open(&mut process, "file") {
            Ok(fd) => highest = highest.max(fd),
            Err(error) => break error,
        }
    };

    println!(
        "limit of 32 descriptors: the highest number obtained is {highest}, the next open fails with {error}"
    );

    Ok(())
}

fn offsets(kernel: &mut Kernel) -> Result<(), Error> {
    let mut process = kernel.process()?;

    let first = kernel.open(&mut process, "file")?;
    let duplicate = kernel.dup(&mut process, first)?;
    let second = kernel.open(&mut process, "file")?;

    kernel.write(&process, first, "hello")?;

    let shared = kernel.open_files[process.lookup(duplicate)?.open].offset;
    let separate = kernel.open_files[process.lookup(second)?.open].offset;

    println!(
        "after a write of 5 bytes: offset through the duplicate {shared}, through a second open {separate}"
    );

    Ok(())
}

fn flags(kernel: &mut Kernel) -> Result<(), Error> {
    let mut process = kernel.process()?;

    let first = kernel.open(&mut process, "file")?;
    let duplicate = kernel.dup(&mut process, first)?;

    kernel.open_files[process.lookup(duplicate)?.open].append_mode = true;

    if let Some(entry) = &mut process.table[duplicate] {
        entry.cloexec = true;
    }

    let original = process.lookup(first)?;

    println!(
        "set on the duplicate, read on the original: O_APPEND {}, close-on-exec {}",
        kernel.open_files[original.open].append_mode, original.cloexec
    );

    Ok(())
}
// ANCHOR_END: experiments

// ANCHOR: lifetime
fn names(kernel: &mut Kernel) -> Result<(), Error> {
    kernel.create("first")?;
    kernel.link("first", "second")?;

    let (a, b) = (kernel.names["first"], kernel.names["second"]);

    println!(
        "a second name for the file: same inode {}, link count {}",
        a == b,
        kernel.inode(b)?.links
    );

    Ok(())
}

fn unlinked(kernel: &mut Kernel) -> Result<(), Error> {
    let mut process = kernel.process()?;
    let file = kernel.create("unlinked")?;

    kernel.inode(file)?.data = b"hello".to_vec();

    let fd = kernel.open(&mut process, "unlinked")?;

    kernel.unlink("unlinked")?;

    let links = kernel.inode(file)?.links;
    let data = kernel.read(&process, fd, 16)?;

    println!(
        "the name removed, the file still open: link count {links}, read through the descriptor returns {data:?}"
    );

    kernel.close(&mut process, fd)
}
// ANCHOR_END: lifetime

// ANCHOR: redirect
/// Forks a child, points its descriptors 1 and 2 at the given descriptors,
/// and has it write "out" and then "err". Returns the file's contents.
fn redirect(
    kernel: &mut Kernel,
    shell: &Process,
    file: u64,
    stdout: usize,
    stderr: usize,
) -> Result<String, Error> {
    let mut child = kernel.fork(shell);

    kernel.dup2(&mut child, stdout, 1)?;
    kernel.dup2(&mut child, stderr, 2)?;
    kernel.exec(&mut child)?;

    kernel.write(&child, 1, "out\n")?;
    kernel.write(&child, 2, "err\n")?;

    let text = String::from_utf8_lossy(&kernel.inode(file)?.data).into_owned();
    let words: Vec<&str> = text.split_whitespace().collect();

    Ok(words.join(" "))
}

fn redirections(kernel: &mut Kernel) -> Result<(), Error> {
    let mut shell = kernel.process()?;
    let file = kernel.create("output")?;
    let stdout = kernel.open(&mut shell, "output")?;

    let text = redirect(kernel, &shell, file, stdout, stdout)?;
    println!("> file 2>&1: the file holds {text:?}");

    kernel.inode(file)?.data.clear();

    let first = kernel.open(&mut shell, "output")?;
    let second = kernel.open(&mut shell, "output")?;

    let text = redirect(kernel, &shell, file, first, second)?;
    println!("> file 2> file: the file holds {text:?}");

    Ok(())
}
// ANCHOR_END: redirect

fn main() -> Result<(), Error> {
    let experiments = [
        numbers,
        limit,
        offsets,
        flags,
        names,
        unlinked,
        redirections,
    ];

    for experiment in experiments {
        let mut kernel = Kernel::default();

        kernel.create("file")?;
        experiment(&mut kernel)?;
    }

    Ok(())
}
