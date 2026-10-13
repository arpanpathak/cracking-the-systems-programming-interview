//! Models the kernel's page cache for one file: pages read from a disk are
//! kept in memory, sequential reads fetch pages ahead of the reader, writes
//! change only the cached page until a sync, and the page used least recently
//! is evicted when the cache is full.
//!
//! Run it from code/rust with:
//!
//! ```text
//! cargo run -p pagecache
//! ```

// ANCHOR: imports
use std::collections::BTreeMap;
// ANCHOR_END: imports

// ANCHOR: types
/// The largest number of pages one disk request reads ahead.
const MAX_WINDOW: usize = 8;

/// Holds the pages of a file and counts the requests made to it. The contents
/// of a page are reduced to one byte.
struct Disk {
    pages: Vec<u8>,
    requests: usize,
    written: usize,
}

impl Disk {
    fn new() -> Disk {
        Disk {
            pages: vec![b'-'; 16],
            requests: 0,
            written: 0,
        }
    }
}

/// A cached copy of a disk page. `dirty` is set when the copy has been
/// written and the disk has not. `used` is the time of the last access.
#[derive(Default)]
struct Page {
    value: u8,
    dirty: bool,
    used: usize,
}

/// Maps page numbers to cached pages. `next` is the page that a sequential
/// reader would ask for next, and `window` is the current number of pages to
/// read ahead.
struct Cache {
    disk: Disk,
    pages: BTreeMap<usize, Page>,
    capacity: usize,
    clock: usize,
    next: usize,
    window: usize,
}

impl Cache {
    fn new(capacity: usize) -> Cache {
        Cache {
            disk: Disk::new(),
            pages: BTreeMap::new(),
            capacity,
            clock: 0,
            next: 0,
            window: 0,
        }
    }
}
// ANCHOR_END: types

// ANCHOR: read
impl Cache {
    /// Returns the contents of a page. A page that is cached costs no disk
    /// request. For a page that is missing, `read` makes one request for a
    /// window of pages. The window doubles while the reads are sequential and
    /// returns to 1 page when they are not.
    fn read(&mut self, index: usize) -> u8 {
        if !self.pages.contains_key(&index) {
            if index == self.next {
                self.window = (2 * self.window.max(1)).min(MAX_WINDOW);
            } else {
                self.window = 1;
            }

            self.load(index, self.window);
        }

        self.next = index + 1;

        self.touch(index).value
    }

    /// Reads `count` pages starting at `index` from the disk in one request.
    fn load(&mut self, index: usize, count: usize) {
        self.disk.requests += 1;

        for i in index..(index + count).min(self.disk.pages.len()) {
            if !self.pages.contains_key(&i) {
                let value = self.disk.pages[i];

                self.insert(i, value);
            }
        }
    }

    /// Records an access to a page and returns the page. A page that is not
    /// cached is created empty.
    fn touch(&mut self, index: usize) -> &mut Page {
        self.clock += 1;

        let page = self.pages.entry(index).or_default();
        page.used = self.clock;

        page
    }
}
// ANCHOR_END: read

// ANCHOR: write
impl Cache {
    /// Changes a page in the cache and marks it dirty. It makes no disk
    /// request.
    fn write(&mut self, index: usize, value: u8) {
        if !self.pages.contains_key(&index) {
            self.insert(index, 0);
        }

        let page = self.touch(index);
        page.value = value;
        page.dirty = true;
    }

    /// Writes every dirty page to the disk and returns the number written.
    fn sync(&mut self) -> usize {
        let before = self.disk.written;

        for (&index, page) in &mut self.pages {
            clean(&mut self.disk, index, page);
        }

        self.disk.written - before
    }
}

/// Writes one page to the disk if it is dirty.
fn clean(disk: &mut Disk, index: usize, page: &mut Page) {
    if page.dirty {
        disk.pages[index] = page.value;
        disk.written += 1;
        page.dirty = false;
    }
}
// ANCHOR_END: write

// ANCHOR: evict
impl Cache {
    /// Adds a page to the cache. When the cache is full it first evicts the
    /// page whose last access is the oldest. A dirty page is written to the
    /// disk before it is removed.
    fn insert(&mut self, index: usize, value: u8) {
        if self.pages.len() == self.capacity {
            let oldest = self
                .pages
                .iter()
                .min_by_key(|(_, page)| page.used)
                .map(|(&index, _)| index);

            if let Some(oldest) = oldest
                && let Some(mut page) = self.pages.remove(&oldest)
            {
                clean(&mut self.disk, oldest, &mut page);
            }
        }

        self.clock += 1;

        let page = Page {
            value,
            dirty: false,
            used: self.clock,
        };

        self.pages.insert(index, page);
    }

    /// Returns the numbers of the cached pages in increasing order.
    fn held(&self) -> Vec<usize> {
        self.pages.keys().copied().collect()
    }
}
// ANCHOR_END: evict

// ANCHOR: trace
/// Reads the given pages through a new cache and returns the number of disk
/// requests.
fn requests(order: impl Iterator<Item = usize>) -> usize {
    let mut cache = Cache::new(32);

    for index in order {
        cache.read(index);
    }

    cache.disk.requests
}

/// Formats page numbers the way Go prints a slice.
fn list(pages: &[usize]) -> String {
    let words: Vec<String> = pages.iter().map(usize::to_string).collect();

    format!("[{}]", words.join(" "))
}

fn main() {
    println!("16 pages read in order: {} disk requests", requests(0..16));
    println!(
        "16 pages read in reverse order: {} disk requests",
        requests((0..16).rev())
    );
    println!(
        "16 pages read in order, 2 times: {} disk requests",
        requests((0..16).chain(0..16))
    );

    let mut cache = Cache::new(4);

    cache.write(3, b'x');
    println!(
        "write of x to page 3: {} pages written, the disk holds {}",
        cache.disk.written,
        char::from(cache.disk.pages[3])
    );

    let written = cache.sync();
    println!(
        "sync: {written} page written, the disk holds {}",
        char::from(cache.disk.pages[3])
    );

    for index in [2, 1, 0, 3] {
        cache.read(index);
    }

    cache.read(8);
    println!(
        "capacity 4, pages 3 2 1 0 3 used, then page 8: cache holds {}",
        list(&cache.held())
    );

    cache.write(1, b'y');

    for index in [0, 3, 8, 12] {
        cache.read(index);
    }

    println!(
        "write of y to page 1, then pages 0 3 8 12 used: cache holds {}, the disk holds {}",
        list(&cache.held()),
        char::from(cache.disk.pages[1])
    );
}
// ANCHOR_END: trace
