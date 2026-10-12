//! Builds a small content-addressed store for model artifacts and runs it
//! through the situations such a store exists for.
//!
//! A blob is stored under the SHA-256 digest of its bytes. An artifact is cut
//! into chunks, each chunk is a blob, and a manifest lists the chunks. The
//! program pushes two versions of a model that differ in their last quarter,
//! pulls the second to a machine that has the first, corrupts one stored
//! chunk, and removes what nothing refers to any more.
//!
//! Run it from code/rust with:
//!
//! ```text
//! cargo run -p cas
//! ```

use std::collections::{BTreeMap, BTreeSet};
use std::fmt::Write as _;

use sha2::{Digest as _, Sha256};

// ANCHOR: store
/// Names a blob: "sha256:" followed by the hash of its bytes in hex.
#[derive(Clone, PartialEq, Eq, PartialOrd, Ord)]
struct Digest(String);

impl Digest {
    /// Computes the name of some bytes.
    fn of(data: &[u8]) -> Self {
        let mut name = String::from("sha256:");
        for byte in Sha256::digest(data) {
            write!(name, "{byte:02x}").expect("writing to a String");
        }
        Digest(name)
    }

    /// Returns the first twelve hex digits, for printing.
    fn short(&self) -> &str {
        &self.0[..19]
    }
}

/// The ways reading from a store can fail.
#[derive(Debug)]
enum StoreError {
    /// The store holds no blob of this name.
    NotFound(String),
    /// A blob's bytes no longer match its name.
    Corrupt(String),
    /// A chunk of an artifact could not be read.
    Chunk(usize, Box<StoreError>),
}

impl std::fmt::Display for StoreError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            StoreError::NotFound(d) => write!(f, "{d}: not found"),
            StoreError::Corrupt(d) => write!(f, "{d}: contents do not match the digest"),
            StoreError::Chunk(i, e) => write!(f, "chunk {i}: {e}"),
        }
    }
}

/// Holds blobs by digest and tags by name.
#[derive(Default)]
struct Store {
    /// Maps each digest to the bytes it names.
    blobs: BTreeMap<Digest, Vec<u8>>,
    /// Maps a name people use, such as "llm:v1", to a manifest's digest.
    tags: BTreeMap<&'static str, Digest>,
}

impl Store {
    /// Stores a blob and returns its digest and whether it was new. Bytes the
    /// store already holds are not stored a second time.
    fn put(&mut self, data: &[u8]) -> (Digest, bool) {
        let d = Digest::of(data);
        if self.blobs.contains_key(&d) {
            return (d, false);
        }
        self.blobs.insert(d.clone(), data.to_vec());
        (d, true)
    }

    /// Returns a blob after checking that its bytes still hash to its name.
    fn get(&self, d: &Digest) -> Result<&[u8], StoreError> {
        let data = self
            .blobs
            .get(d)
            .ok_or_else(|| StoreError::NotFound(d.short().to_owned()))?;
        if Digest::of(data) != *d {
            return Err(StoreError::Corrupt(d.short().to_owned()));
        }
        Ok(data)
    }
}
// ANCHOR_END: store

// ANCHOR: push
impl Store {
    /// Cuts an artifact into chunks, stores each chunk, stores a manifest that
    /// lists the chunks' digests in order, and points the tag at the manifest.
    /// Returns the manifest's digest, the number of chunks, and how many were
    /// new to the store.
    fn push(&mut self, tag: &'static str, artifact: &[u8]) -> (Digest, usize, usize) {
        let mut lines = String::new();
        let (mut chunks, mut added) = (0, 0);
        for chunk in artifact.chunks(CHUNK_SIZE) {
            let (d, fresh) = self.put(chunk);
            added += usize::from(fresh);
            chunks += 1;
            writeln!(lines, "{} {}", d.0, chunk.len()).expect("writing to a String");
        }
        let (manifest, _) = self.put(lines.as_bytes());
        self.tags.insert(tag, manifest.clone());
        (manifest, chunks, added)
    }

    /// Reads a manifest and returns the digests it lists.
    fn chunks_of(&self, manifest: &Digest) -> Result<Vec<Digest>, StoreError> {
        let text = String::from_utf8_lossy(self.get(manifest)?);
        Ok(text
            .lines()
            .filter_map(|line| line.split(' ').next())
            .map(|d| Digest(d.to_owned()))
            .collect())
    }
}
// ANCHOR_END: push

// ANCHOR: pull
impl Store {
    /// Copies a tagged artifact from a remote store into this one, fetching
    /// only the chunks this store does not hold. Returns the number of chunks
    /// and bytes fetched.
    fn pull(&mut self, remote: &Store, tag: &'static str) -> Result<(usize, usize), StoreError> {
        let manifest = &remote.tags[tag];
        let (mut fetched, mut bytes) = (0, 0);
        for d in remote.chunks_of(manifest)? {
            if self.blobs.contains_key(&d) {
                continue;
            }
            let data = remote.get(&d)?;
            fetched += 1;
            bytes += data.len();
            self.blobs.insert(d, data.to_vec());
        }
        self.blobs
            .insert(manifest.clone(), remote.get(manifest)?.to_vec());
        self.tags.insert(tag, manifest.clone());
        Ok((fetched, bytes))
    }

    /// Reassembles a tagged artifact, verifying every chunk on the way.
    fn read(&self, tag: &str) -> Result<Vec<u8>, StoreError> {
        let mut artifact = Vec::new();
        for (i, d) in self.chunks_of(&self.tags[tag])?.iter().enumerate() {
            let data = self.get(d).map_err(|e| StoreError::Chunk(i, Box::new(e)))?;
            artifact.extend_from_slice(data);
        }
        Ok(artifact)
    }
}
// ANCHOR_END: pull

// ANCHOR: gc
impl Store {
    /// Removes every blob that no tag leads to. It first marks the manifests
    /// the tags name and the chunks those manifests list, then sweeps the
    /// rest. Returns the number of blobs and bytes removed.
    fn collect(&mut self) -> (usize, usize) {
        let mut live = BTreeSet::new();
        for manifest in self.tags.values() {
            live.extend(self.chunks_of(manifest).unwrap_or_default());
            live.insert(manifest.clone());
        }
        let (before, bytes_before) = self.size();
        self.blobs.retain(|d, _| live.contains(d));
        let (after, bytes_after) = self.size();
        (before - after, bytes_before - bytes_after)
    }
}
// ANCHOR_END: gc

impl Store {
    /// Returns the number of blobs in the store and their total size.
    fn size(&self) -> (usize, usize) {
        (self.blobs.len(), self.blobs.values().map(Vec::len).sum())
    }
}

/// The size of the pieces an artifact is cut into.
const CHUNK_SIZE: usize = 8 * 1024;

/// Returns n bytes that stand for a model's weights. The bytes come from a
/// fixed sequence, so every run and both languages produce the same.
fn weights(n: usize, seed: u32) -> Vec<u8> {
    let mut x = seed;
    (0..n)
        .map(|_| {
            x = x.wrapping_mul(1_664_525).wrapping_add(1_013_904_223);
            (x >> 24) as u8
        })
        .collect()
}

// ANCHOR: main
fn main() -> Result<(), StoreError> {
    // Version 1 is 64 KiB. Version 2 is a fine-tuned copy: the first three
    // quarters are unchanged and the last quarter is new.
    let v1 = weights(64 * 1024, 1);
    let v2 = [&v1[..48 * 1024], &weights(16 * 1024, 2)].concat();

    let mut registry = Store::default();
    let (m1, chunks, added) = registry.push("llm:v1", &v1);
    println!(
        "push llm:v1: {chunks} chunks, {added} new; manifest {}",
        m1.short()
    );
    let (m2, chunks, added) = registry.push("llm:v2", &v2);
    println!(
        "push llm:v2: {chunks} chunks, {added} new; manifest {}",
        m2.short()
    );
    let (blobs, bytes) = registry.size();
    println!(
        "the registry holds {blobs} blobs and {bytes} bytes for {} bytes of artifacts",
        v1.len() + v2.len()
    );

    let mut node = Store::default();
    let (fetched, n) = node.pull(&registry, "llm:v1")?;
    println!("thor-1 pulls llm:v1: {fetched} chunks fetched, {n} bytes");
    let (fetched, n) = node.pull(&registry, "llm:v2")?;
    println!("thor-1 pulls llm:v2: {fetched} chunks fetched, {n} bytes");

    println!("one bit flips in a chunk stored on thor-1:");
    let fourth = node.chunks_of(&node.tags["llm:v1"])?[3].clone();
    node.blobs.get_mut(&fourth).expect("the chunk was pulled")[100] ^= 1;
    if let Err(e) = node.read("llm:v1") {
        println!("  read llm:v1: {e}");
    }
    // The bad chunk is dropped and pulled again, by name, from the registry.
    node.blobs.remove(&fourth);
    let (fetched, n) = node.pull(&registry, "llm:v1")?;
    println!("  thor-1 drops the chunk and pulls llm:v1 again: {fetched} chunk fetched, {n} bytes");
    let got = node.read("llm:v1")?;
    println!(
        "  read llm:v1: {} bytes, digest {}",
        got.len(),
        Digest::of(&got).short()
    );

    println!("the tag llm:v1 is deleted from the registry:");
    registry.tags.remove("llm:v1");
    let (removed, n) = registry.collect();
    let (blobs, bytes) = registry.size();
    println!("  collected {removed} blobs, {n} bytes; {blobs} blobs and {bytes} bytes remain");
    Ok(())
}
// ANCHOR_END: main
