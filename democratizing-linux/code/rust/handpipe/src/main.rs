//! Builds a pipe by hand, with the same parts the kernel uses: a ring of
//! pages for the bytes, a lock, a place for a reader to sleep and a place for
//! a writer to sleep, and a count of the open ends.
//!
//! It traces a small ring call by call, repeats the capacity measurement of
//! pipefacts on a ring of the kernel's size, and sends 1048576 bytes from a
//! writer thread to a reader.
//!
//! Run it from code/rust with:
//!
//! ```text
//! cargo run -p handpipe
//! ```

// ANCHOR: imports
use std::fmt;
use std::thread;

use parking_lot::{Condvar, Mutex};
// ANCHOR_END: imports

// ANCHOR: page
/// One slot of the ring: a block of memory, and the position and length of
/// the bytes in it that have not been read yet.
struct Page {
    data: Vec<u8>,
    offset: usize,
    length: usize,
}

/// The storage of a pipe. `head` counts the pages ever put into use and
/// `tail` counts the pages ever emptied, so `head - tail` pages are in use,
/// and a counter's remainder after division by the number of slots is its
/// slot.
struct Ring {
    pages: Vec<Page>,
    head: usize,
    tail: usize,
}

impl Ring {
    fn new(slots: usize, page_size: usize) -> Ring {
        let pages = (0..slots)
            .map(|_| Page {
                data: vec![0; page_size],
                offset: 0,
                length: 0,
            })
            .collect();

        Ring {
            pages,
            head: 0,
            tail: 0,
        }
    }

    fn empty(&self) -> bool {
        self.head == self.tail
    }

    fn full(&self) -> bool {
        self.head - self.tail == self.pages.len()
    }

    /// The page that a counter refers to.
    fn slot(&mut self, counter: usize) -> &mut Page {
        let slots = self.pages.len();

        &mut self.pages[counter % slots]
    }
}
// ANCHOR_END: page

// ANCHOR: put
/// Copies as many bytes as both slices allow and returns the count.
fn copy(to: &mut [u8], from: &[u8]) -> usize {
    let n = to.len().min(from.len());
    to[..n].copy_from_slice(&from[..n]);

    n
}

impl Ring {
    /// Copies as much of `data` as the ring has room for and returns the
    /// number of bytes it copied. The bytes go first into the unused end of
    /// the newest page, then into free slots, one page each.
    fn put(&mut self, data: &[u8]) -> usize {
        let mut copied = 0;

        if !self.empty() {
            let newest = self.slot(self.head - 1);
            let end = newest.offset + newest.length;

            let n = copy(&mut newest.data[end..], data);
            newest.length += n;
            copied += n;
        }

        while copied < data.len() && !self.full() {
            let next = self.slot(self.head);
            next.offset = 0;
            next.length = copy(&mut next.data, &data[copied..]);

            copied += next.length;
            self.head += 1;
        }

        copied
    }
}
// ANCHOR_END: put

// ANCHOR: take
impl Ring {
    /// Moves up to `buf.len()` of the oldest bytes into `buf` and returns the
    /// number it moved. A slot becomes free when the last byte of its page
    /// has been taken.
    fn take(&mut self, buf: &mut [u8]) -> usize {
        let mut moved = 0;

        while moved < buf.len() && !self.empty() {
            let oldest = self.slot(self.tail);
            let unread = oldest.offset..oldest.offset + oldest.length;

            let n = copy(&mut buf[moved..], &oldest.data[unread]);
            oldest.offset += n;
            oldest.length -= n;
            moved += n;

            if oldest.length == 0 {
                self.tail += 1;
            }
        }

        moved
    }
}
// ANCHOR_END: take

// ANCHOR: pipe
/// What a write returns when no reader is left.
#[derive(Debug)]
struct BrokenPipe;

impl fmt::Display for BrokenPipe {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str("EPIPE")
    }
}

/// What the lock guards: the ring and the count of the open ends.
struct State {
    ring: Ring,
    readers: usize,
    writers: usize,
}

/// A ring shared by a reader and a writer thread. `readable` is where a reader sleeps while
/// the ring is empty, and `writable` is where a writer sleeps while the ring
/// is full.
struct Pipe {
    state: Mutex<State>,
    readable: Condvar,
    writable: Condvar,
}

impl Pipe {
    fn new(slots: usize, page_size: usize) -> Pipe {
        let state = State {
            ring: Ring::new(slots, page_size),
            readers: 1,
            writers: 1,
        };

        Pipe {
            state: Mutex::new(state),
            readable: Condvar::new(),
            writable: Condvar::new(),
        }
    }
}
// ANCHOR_END: pipe

// ANCHOR: write
impl Pipe {
    /// Returns when every byte of `data` is in the ring, or when no reader is
    /// left. While the ring is full it sleeps on `writable`.
    fn write(&self, data: &[u8]) -> Result<usize, BrokenPipe> {
        let mut state = self.state.lock();
        let mut written = 0;

        while written < data.len() {
            if state.readers == 0 {
                return Err(BrokenPipe);
            }

            let n = state.ring.put(&data[written..]);
            written += n;

            if n == 0 {
                self.writable.wait(&mut state);
                continue;
            }

            self.readable.notify_all();
        }

        Ok(written)
    }
}
// ANCHOR_END: write

// ANCHOR: read
impl Pipe {
    /// Returns as soon as it has moved at least one byte into `buf`. While
    /// the ring is empty and a writer exists it sleeps on `readable`. It
    /// returns 0 when the ring is empty and no writer is left: the end of the
    /// stream.
    fn read(&self, buf: &mut [u8]) -> usize {
        let mut state = self.state.lock();

        self.readable
            .wait_while(&mut state, |state| state.ring.empty() && state.writers > 0);

        let n = state.ring.take(buf);

        if n > 0 {
            self.writable.notify_all();
        }

        n
    }
}
// ANCHOR_END: read

// ANCHOR: close
impl Pipe {
    /// Gives up a write end. A reader asleep on an empty ring wakes and finds
    /// that no writer is left.
    fn close_writer(&self) {
        self.state.lock().writers -= 1;
        self.readable.notify_all();
    }

    /// Gives up a read end. A writer asleep on a full ring wakes and finds
    /// that no reader is left.
    fn close_reader(&self) {
        self.state.lock().readers -= 1;
        self.writable.notify_all();
    }
}
// ANCHOR_END: close

// ANCHOR: trace
impl Ring {
    /// Renders the ring as one cell per slot: the unread bytes in its page,
    /// or a dot for a free slot.
    fn picture(&self) -> String {
        let slots = self.pages.len();
        let mut cells = vec![".".to_string(); slots];

        for counter in self.tail..self.head {
            cells[counter % slots] = self.pages[counter % slots].length.to_string();
        }

        format!("[{}]", cells.join(" "))
    }
}

/// Applies the calls of the trace to a ring of 4 pages of 8 bytes and prints
/// the ring after each.
fn small_ring() {
    let mut ring = Ring::new(4, 8);
    let mut buf = [0u8; 32];

    let calls = [
        ("put", 12),
        ("take", 3),
        ("put", 30),
        ("take", 5),
        ("put", 30),
    ];

    println!("ring of 4 pages of 8 bytes");

    for (op, n) in calls {
        let done = match op {
            "put" => ring.put(&buf[..n]),
            _ => ring.take(&mut buf[..n]),
        };

        println!(
            "{op:<4} {n:2}: {done:2} bytes   head {}  tail {}   {}",
            ring.head,
            ring.tail,
            ring.picture()
        );
    }
}
// ANCHOR_END: trace

// ANCHOR: kernelsize
/// Puts whole blocks into the ring until it accepts none and returns the
/// number of bytes accepted.
fn fill(ring: &mut Ring, block: &[u8]) -> usize {
    let mut total = 0;

    loop {
        let n = ring.put(block);

        if n == 0 {
            return total;
        }

        total += n;
    }
}

/// Repeats the capacity measurement of pipefacts on a ring with the kernel's
/// dimensions: 16 pages of 4096 bytes.
fn kernel_size() {
    const PAGE_SIZE: usize = 4096;

    let mut ring = Ring::new(16, PAGE_SIZE);
    let mut block = [0u8; PAGE_SIZE];

    let steps = [
        (0, "new pipe"),
        (1, "after reading 1 byte"),
        (PAGE_SIZE - 1, "after reading 4096 bytes in total"),
    ];

    for (count, label) in steps {
        ring.take(&mut block[..count]);

        let accepted = fill(&mut ring, &block);
        println!("{label}: {accepted} bytes accepted");
    }
}
// ANCHOR_END: kernelsize

// ANCHOR: transfer
/// Sends one megabyte through a pipe of the kernel's size. Byte `i` of the
/// stream has the value `i` mod 256, which lets the reader verify the order.
fn transfer() {
    const TOTAL: usize = 1 << 20;

    let pipe = Pipe::new(16, 4096);
    let mut buf = vec![0u8; 30_000];

    thread::scope(|scope| {
        scope.spawn(|| {
            let mut chunk = vec![0u8; 100_000];

            for sent in (0..TOTAL).step_by(chunk.len()) {
                chunk.truncate(TOTAL - sent);

                for (i, byte) in chunk.iter_mut().enumerate() {
                    *byte = (sent + i) as u8;
                }

                if pipe.write(&chunk).is_err() {
                    break;
                }
            }

            pipe.close_writer();
        });

        let (mut received, mut in_order) = (0, true);

        loop {
            let n = pipe.read(&mut buf);

            if n == 0 {
                break;
            }

            for (i, byte) in buf[..n].iter().enumerate() {
                in_order = in_order && *byte == (received + i) as u8;
            }

            received += n;
        }

        println!("1048576 bytes written: {received} bytes read, in order: {in_order}");
    });

    println!("write end closed: read returns {}", pipe.read(&mut buf));

    pipe.close_reader();

    if let Err(error) = pipe.write(b"hello") {
        println!("read end closed: write fails with {error}");
    }
}
// ANCHOR_END: transfer

fn main() {
    small_ring();
    println!();
    kernel_size();
    println!();
    transfer();
}
