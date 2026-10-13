//! Command syncsim cuts a file into chunks in 2 ways, adds 1 byte at the
//! start of the file, and counts how many chunks have to be uploaded again.
//! It then lets 2 devices change the same file and shows how the second
//! upload is recognised as a conflict.
//!
//! Run it from code/ with:
//!
//!     cargo run -p syncsim

// ANCHOR: imports
use std::collections::BTreeSet;
use std::hash::{DefaultHasher, Hash, Hasher};
// ANCHOR_END: imports

// ANCHOR: chunks
fn checksum(bytes: &[u8]) -> u64 {
    let mut hasher = DefaultHasher::new();

    bytes.hash(&mut hasher);

    hasher.finish()
}

/// Chunks of a fixed size: a cut after every 1024 bytes.
fn fixed(data: &[u8]) -> Vec<&[u8]> {
    data.chunks(1024).collect()
}

/// Chunks whose ends depend on the content: a cut wherever the last 16
/// bytes, taken together, give a number that is divisible by 1024.
fn by_content(data: &[u8]) -> Vec<&[u8]> {
    let cuts: Vec<usize> = (16..data.len())
        .filter(|&end| checksum(&data[end - 16..end]).is_multiple_of(1024))
        .chain([data.len()])
        .collect();
    let starts = [0]
        .into_iter()
        .chain(cuts.iter().copied());

    starts
        .zip(&cuts)
        .map(|(start, &end)| &data[start..end])
        .collect()
}

/// How many chunks of the changed file the server does not have yet.
fn to_upload(before: &[&[u8]], after: &[&[u8]]) -> usize {
    let known: BTreeSet<u64> = before
        .iter()
        .map(|chunk| checksum(chunk))
        .collect();

    after
        .iter()
        .filter(|chunk| !known.contains(&checksum(chunk)))
        .count()
}
// ANCHOR_END: chunks

// ANCHOR: versions
/// The server's record of a file: its version, and which device wrote it.
struct Remote {
    version: u64,
    writer: &'static str,
}

/// The outcome of an upload that says which version it was based on.
enum Upload {
    Accepted {
        version: u64,
    },
    Conflict {
        current: u64,
        written_by: &'static str,
    },
}

impl Remote {
    fn upload(&mut self, device: &'static str, based_on: u64) -> Upload {
        if based_on != self.version {
            return Upload::Conflict {
                current: self.version,
                written_by: self.writer,
            };
        }

        self.version += 1;
        self.writer = device;

        Upload::Accepted {
            version: self.version,
        }
    }
}
// ANCHOR_END: versions

// ANCHOR: main
fn describe(upload: Upload) -> String {
    match upload {
        Upload::Accepted { version } => format!("accepted as version {version}"),
        Upload::Conflict {
            current,
            written_by,
        } => {
            format!("conflict: the server is at version {current}, written by the {written_by}")
        }
    }
}

fn main() {
    // 64 KB whose bytes look random and can be produced again.
    let mut state = 7u64;
    let file: Vec<u8> = std::iter::repeat_with(|| {
        state ^= state << 13;
        state ^= state >> 7;
        state ^= state << 17;

        (state >> 24) as u8
    })
    .take(64 * 1024)
    .collect();
    let edited: Vec<u8> = b"!"
        .iter()
        .chain(&file)
        .copied()
        .collect();

    println!(
        "a file of {} bytes, and the same file with 1 byte added at the start",
        file.len()
    );

    let (before, after) = (fixed(&file), fixed(&edited));
    println!(
        "cuts every 1024 bytes: {} chunks, {} to upload again",
        after.len(),
        to_upload(&before, &after)
    );

    let (before, after) = (by_content(&file), by_content(&edited));
    println!(
        "cuts that depend on the content: {} chunks, {} to upload again",
        after.len(),
        to_upload(&before, &after)
    );

    let mut remote = Remote {
        version: 3,
        writer: "laptop",
    };

    println!("the server holds version 3. the laptop and the phone both change it while offline");
    println!(
        "laptop uploads, based on version 3: {}",
        describe(remote.upload("laptop", 3))
    );
    println!(
        "phone uploads, based on version 3: {}",
        describe(remote.upload("phone", 3))
    );
}
// ANCHOR_END: main
