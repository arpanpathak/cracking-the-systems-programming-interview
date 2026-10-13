//! Command objectsim stores an object the way an object store does: cut
//! into chunks, each chunk named by its checksum and kept on 3 nodes. It
//! then damages one copy of a chunk and reads the object back.
//!
//! Run it from code/ with:
//!
//!     cargo run -p objectsim

// ANCHOR: imports
use std::collections::HashMap;

use crc32fast::hash;
// ANCHOR_END: imports

// ANCHOR: store
const CHUNK: usize = 4 * 1024 * 1024;
const COPIES: usize = 3;

/// A storage node: chunks by their checksum.
#[derive(Default)]
struct Node {
    chunks: HashMap<u32, Vec<u8>>,
}

struct ObjectStore {
    nodes: Vec<Node>,
    /// For each object, the checksums of its chunks in order.
    objects: HashMap<String, Vec<u32>>,
}

impl ObjectStore {
    /// The nodes that hold a chunk: 3 in a row, starting from its checksum.
    fn homes(&self, checksum: u32) -> impl Iterator<Item = usize> {
        let count = self.nodes.len();

        (0..COPIES).map(move |copy| (checksum as usize + copy) % count)
    }

    /// Stores an object and returns how many chunks were written and how
    /// many were already there.
    fn put(&mut self, name: &str, data: &[u8]) -> (usize, usize) {
        let checksums: Vec<u32> = data
            .chunks(CHUNK)
            .map(hash)
            .collect();
        let written = data
            .chunks(CHUNK)
            .filter(|chunk| self.store(chunk))
            .count();
        let present = checksums.len() - written;

        self.objects
            .insert(name.to_owned(), checksums);

        (written, present)
    }

    /// Stores a chunk on its 3 nodes and returns `true`, or returns `false`
    /// when a chunk with the same checksum is already there.
    fn store(&mut self, chunk: &[u8]) -> bool {
        let checksum = hash(chunk);
        let homes: Vec<usize> = self.homes(checksum).collect();

        if self.nodes[homes[0]]
            .chunks
            .contains_key(&checksum)
        {
            return false;
        }

        for home in homes {
            self.nodes[home]
                .chunks
                .insert(checksum, chunk.to_vec());
        }

        true
    }

    /// Reads an object. A copy whose checksum does not match is skipped and
    /// replaced from a good copy.
    fn get(&mut self, name: &str) -> Option<(Vec<u8>, usize)> {
        let checksums = self.objects.get(name)?.clone();
        let (mut data, mut repaired) = (Vec::new(), 0);

        for checksum in checksums {
            let (chunk, fixed) = self.chunk(checksum)?;

            data.extend_from_slice(&chunk);
            repaired += fixed;
        }

        Some((data, repaired))
    }

    /// Reads 1 chunk from a node whose copy matches the checksum, replaces
    /// the copies that do not match, and returns the chunk with the number
    /// of copies it replaced.
    fn chunk(&mut self, checksum: u32) -> Option<(Vec<u8>, usize)> {
        let homes: Vec<usize> = self.homes(checksum).collect();
        let intact = |node: &Node| {
            node.chunks
                .get(&checksum)
                .filter(|chunk| hash(chunk) == checksum)
                .cloned()
        };
        let good = homes
            .iter()
            .find_map(|&home| intact(&self.nodes[home]))?;
        let damaged: Vec<usize> = homes
            .into_iter()
            .filter(|&home| intact(&self.nodes[home]).is_none())
            .collect();

        for &home in &damaged {
            self.nodes[home]
                .chunks
                .insert(checksum, good.clone());
        }

        Some((good, damaged.len()))
    }
}
// ANCHOR_END: store

// ANCHOR: main
fn main() {
    let mut store = ObjectStore {
        nodes: std::iter::repeat_with(Node::default)
            .take(6)
            .collect(),
        objects: HashMap::new(),
    };

    // 10 MB whose bytes depend on their position, so every chunk differs.
    let video: Vec<u8> = (0..10 * 1024 * 1024u32)
        .map(|position| (position / 4099 % 251) as u8)
        .collect();

    let (written, present) = store.put("video.mp4", &video);
    println!("video.mp4, 10 MB: {written} chunks written, {present} already there");

    let (written, present) = store.put("copy-of-video.mp4", &video);
    println!(
        "copy-of-video.mp4, the same bytes: {written} chunks written, {present} already there"
    );

    let per_node: Vec<String> = store
        .nodes
        .iter()
        .map(|node| node.chunks.len().to_string())
        .collect();
    println!("chunks on each of the 6 nodes: {}", per_node.join(" "));

    // A disk returns wrong bytes for one copy of the first chunk.
    let first = store.objects["video.mp4"][0];
    let home = (first as usize) % store.nodes.len();

    if let Some(chunk) = store.nodes[home]
        .chunks
        .get_mut(&first)
    {
        chunk[1000] ^= 0xff;
    }

    println!("1 byte is damaged in the copy of chunk 1 on node {home}");

    match store.get("video.mp4") {
        Some((data, repaired)) => println!(
            "video.mp4 read back: {} bytes, equal to the original: {}, copies repaired: {repaired}",
            data.len(),
            data == video
        ),
        None => println!("video.mp4 could not be read"),
    }
}
// ANCHOR_END: main
