//! Two LRU caches of the same design, stored differently, so one benchmark loop
//! can cover both.
//!
//! [`arena`] keeps nodes in a `Vec` and links them by `usize` index.
//! [`rc_list`] allocates an `Rc<RefCell<_>>` per node and links them by pointer.

pub mod arena;
pub mod rc_list;

use std::hash::Hash;

/// The operations every cache supports.
pub trait Cache<K, V>
where
    K: Hash + Eq + Clone,
    V: Copy,
{
    /// A cache that holds at most `capacity` entries.
    ///
    /// # Panics
    /// Panics if `capacity == 0`, since a zero-capacity cache cannot store
    /// anything.
    fn new(capacity: usize) -> Self;

    /// Looks up `key`, promoting it to most recently used on a hit.
    fn get(&mut self, key: &K) -> Option<V>;

    /// Inserts or updates `key`, evicting the least recently used entry when
    /// the cache is full.
    fn put(&mut self, key: K, value: V);

    /// How many entries are cached.
    fn len(&self) -> usize;

    /// The variant's name, for benchmark output.
    fn variant() -> &'static str;
}
