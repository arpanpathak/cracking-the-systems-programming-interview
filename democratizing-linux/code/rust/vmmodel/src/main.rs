//! Models an address space: a list of mappings, a page table that is filled
//! on demand by page faults, a shared zero page, and copy-on-write after
//! fork.
//!
//! Run it from code/rust with:
//!
//! ```text
//! cargo run -p vmmodel
//! ```

// ANCHOR: imports
use std::cell::Cell;
use std::collections::HashMap;
use std::fmt;
use std::rc::Rc;
// ANCHOR_END: imports

// ANCHOR: types
const PAGE_SIZE: usize = 4096;

/// The result of an access that no mapping allows. The kernel sends the
/// process the signal `SIGSEGV`.
#[derive(Debug)]
struct Segv;

impl fmt::Display for Segv {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str("SIGSEGV")
    }
}

/// A page of physical memory. The reference count of the `Rc` is the number
/// of page table entries that refer to it.
type Frame = Rc<[u8; PAGE_SIZE]>;

/// The physical memory shared by all address spaces: the number of frames
/// allocated, and the frame of zeros that every read of an untouched page
/// maps.
struct Memory {
    frames: Cell<usize>,
    zero: Frame,
}

impl Memory {
    fn allocate(&self, contents: [u8; PAGE_SIZE]) -> Frame {
        self.frames.set(self.frames.get() + 1);

        Rc::new(contents)
    }
}

/// A range of virtual pages and the access it permits.
#[derive(Clone, Copy)]
struct Mapping {
    start: usize,
    pages: usize,
    writable: bool,
}

/// A page table entry: the frame behind a virtual page, and whether the
/// processor may write to it without a fault.
#[derive(Clone)]
struct Entry {
    frame: Frame,
    writable: bool,
}

/// The address space of a process.
struct Space {
    memory: Rc<Memory>,
    mappings: Vec<Mapping>,
    table: HashMap<usize, Entry>,
    faults: usize,
    next_page: usize,
}

impl Space {
    fn new() -> Space {
        let memory = Memory {
            frames: Cell::new(0),
            zero: Rc::new([0; PAGE_SIZE]),
        };

        Space {
            memory: Rc::new(memory),
            mappings: Vec::new(),
            table: HashMap::new(),
            faults: 0,
            next_page: 16,
        }
    }
}
// ANCHOR_END: types

// ANCHOR: mmap
impl Space {
    /// Records a new mapping and returns its address. It allocates no frame
    /// and writes no page table entry.
    fn mmap(&mut self, pages: usize, writable: bool) -> usize {
        let start = self.next_page;

        self.mappings.push(Mapping {
            start,
            pages,
            writable,
        });
        self.next_page += pages + 1;

        start * PAGE_SIZE
    }

    /// Returns the mapping that contains a page.
    fn find(&self, page: usize) -> Option<Mapping> {
        self.mappings
            .iter()
            .copied()
            .find(|mapping| (mapping.start..mapping.start + mapping.pages).contains(&page))
    }
}
// ANCHOR_END: mmap

// ANCHOR: access
impl Space {
    /// Returns the byte at an address. The processor uses the page table
    /// entry when one exists, and faults when none does.
    fn read(&mut self, address: usize) -> Result<u8, Segv> {
        let (page, offset) = (address / PAGE_SIZE, address % PAGE_SIZE);

        if !self.table.contains_key(&page) {
            self.fault(page, false)?;
        }

        self.table
            .get(&page)
            .map(|entry| entry.frame[offset])
            .ok_or(Segv)
    }

    /// Stores a byte at an address. It faults when the page has no entry or
    /// the entry does not permit writing.
    fn write(&mut self, address: usize, value: u8) -> Result<(), Segv> {
        let (page, offset) = (address / PAGE_SIZE, address % PAGE_SIZE);

        if !self.table.get(&page).is_some_and(|entry| entry.writable) {
            self.fault(page, true)?;
        }

        let entry = self.table.get_mut(&page).ok_or(Segv)?;

        // A writable entry is the only user of its frame, so `make_mut`
        // returns the frame itself.
        Rc::make_mut(&mut entry.frame)[offset] = value;

        Ok(())
    }
}
// ANCHOR_END: access

// ANCHOR: fault
impl Space {
    /// The kernel's page fault handler. It checks the access against the
    /// mappings and then repairs the page table entry so that the access can
    /// be repeated.
    fn fault(&mut self, page: usize, write: bool) -> Result<(), Segv> {
        let mapping = self.find(page).ok_or(Segv)?;

        if write && !mapping.writable {
            return Err(Segv);
        }

        self.faults += 1;

        let entry = match (write, self.table.remove(&page)) {
            // A read of an untouched page maps the shared zero frame.
            (false, _) => Entry {
                frame: Rc::clone(&self.memory.zero),
                writable: false,
            },

            // A write to an untouched page gets a new frame of zeros.
            (true, None) => Entry {
                frame: self.memory.allocate([0; PAGE_SIZE]),
                writable: true,
            },

            // The frame has no other user. Writing is enabled in place.
            (true, Some(entry)) if Rc::strong_count(&entry.frame) == 1 => Entry {
                frame: entry.frame,
                writable: true,
            },

            // The frame is shared. The writer gets a private copy.
            (true, Some(entry)) => Entry {
                frame: self.memory.allocate(*entry.frame),
                writable: true,
            },
        };

        self.table.insert(page, entry);

        Ok(())
    }
}
// ANCHOR_END: fault

// ANCHOR: fork
impl Space {
    /// Returns a child with the same mappings and a page table that refers to
    /// the same frames. Every entry is made read-only in the parent and in
    /// the child, so that the first write by either causes a fault.
    fn fork(&mut self) -> Space {
        for entry in self.table.values_mut() {
            entry.writable = false;
        }

        Space {
            memory: Rc::clone(&self.memory),
            mappings: self.mappings.clone(),
            table: self.table.clone(),
            faults: 0,
            next_page: self.next_page,
        }
    }
}
// ANCHOR_END: fork

// ANCHOR: trace
impl Space {
    /// Prints a step with the fault count of a space and the number of frames
    /// allocated.
    fn report(&self, step: &str) {
        println!(
            "{step:<34} faults {}, frames {}",
            self.faults,
            self.memory.frames.get()
        );
    }
}

fn run() -> Result<(), Segv> {
    let mut parent = Space::new();
    let base = parent.mmap(4, true);
    parent.report("mmap of 4 pages:");

    parent.write(base, b'a')?;
    parent.report("write to page 0:");

    let value = parent.read(base + PAGE_SIZE)?;
    parent.report(&format!("read of page 1, value {value}:"));

    parent.write(base + PAGE_SIZE, b'x')?;
    parent.report("write to page 1:");

    let mut child = parent.fork();
    child.report("fork, in the child:");

    child.write(base, b'b')?;
    child.report("child writes page 0:");

    parent.write(base, b'c')?;
    parent.report("parent writes page 0:");

    println!(
        "page 0 holds {:?} in the parent and {:?} in the child",
        char::from(parent.read(base)?),
        char::from(child.read(base)?)
    );

    if let Err(error) = parent.write(base + 100 * PAGE_SIZE, 1) {
        println!("write outside every mapping: {error}");
    }

    let read_only = parent.mmap(1, false);

    if let Err(error) = parent.write(read_only, 1) {
        println!("write to a read-only mapping: {error}");
    }

    Ok(())
}

fn main() {
    if let Err(error) = run() {
        println!("{error}");
    }
}
// ANCHOR_END: trace
