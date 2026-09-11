//! A bump (arena) allocator over a fixed byte buffer.
//!
//! Bump allocation is the simplest allocator: hand out bytes from a cursor and
//! never free an individual block. It is O(1) per allocation, has no fragmentation
//! bookkeeping, and is freed all at once with [`BumpArena::reset`]. Parsers,
//! request handlers, and per-frame GPU upload buffers use exactly this shape.
//!
//! The point of the exercise is not to beat the system allocator; it is to show
//! that you understand alignment, the memory layout you hand to hardware, and why
//! "free everything at once" is both the strength and the limitation.

/// A fixed-capacity bump allocator.
pub struct BumpArena {
    buffer: Vec<u8>,
    offset: usize,
}

impl BumpArena {
    /// Create an arena backed by `capacity` zeroed bytes.
    pub fn with_capacity(capacity: usize) -> Self {
        Self {
            buffer: vec![0; capacity],
            offset: 0,
        }
    }

    /// Allocate `size` bytes aligned to `align`.
    ///
    /// Returns `None` when the request does not fit. `align` must be a power of
    /// two.
    pub fn alloc(&mut self, size: usize, align: usize) -> Option<&mut [u8]> {
        assert!(align.is_power_of_two(), "align must be a power of two");

        let start = align_up(self.offset, align)?;
        let end = start.checked_add(size)?;
        if end > self.buffer.len() {
            return None;
        }

        self.offset = end;
        Some(&mut self.buffer[start..end])
    }

    /// Bytes handed out so far, including alignment padding.
    pub fn used(&self) -> usize {
        self.offset
    }

    /// Bytes still available before the next allocation.
    pub fn remaining(&self) -> usize {
        self.buffer.len() - self.offset
    }

    /// Total capacity.
    pub fn capacity(&self) -> usize {
        self.buffer.len()
    }

    /// Free everything at once, as an arena does.
    pub fn reset(&mut self) {
        self.offset = 0;
    }
}

fn align_up(offset: usize, align: usize) -> Option<usize> {
    let mask = align - 1;
    offset.checked_add(mask).map(|value| value & !mask)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn allocations_are_aligned() {
        let mut arena = BumpArena::with_capacity(64);

        let first = arena.alloc(1, 8).expect("fits");
        assert_eq!(first.as_ptr() as usize % 8, 0);
        assert_eq!(first.len(), 1);

        let second = arena.alloc(4, 16).expect("fits");
        assert_eq!(second.as_ptr() as usize % 16, 0);

        // The first block occupies 1 byte. Aligning the next block to 16 adds 15
        // bytes of padding, so the arena has consumed 16 + 4 = 20 bytes.
        assert_eq!(arena.used(), 20);
        assert_eq!(arena.remaining(), 44);
    }

    #[test]
    fn exhaustion_returns_none_and_keeps_state() {
        let mut arena = BumpArena::with_capacity(16);
        assert!(arena.alloc(16, 1).is_some());

        let used_before = arena.used();
        assert!(arena.alloc(1, 1).is_none());
        assert_eq!(arena.used(), used_before, "a failed alloc must not advance");
    }

    #[test]
    fn reset_reclaims_everything() {
        let mut arena = BumpArena::with_capacity(32);
        assert!(arena.alloc(20, 4).is_some());
        assert_eq!(arena.remaining(), 12);

        arena.reset();
        assert_eq!(arena.used(), 0);
        assert_eq!(arena.remaining(), arena.capacity());
        assert!(arena.alloc(32, 1).is_some());
    }

    #[test]
    fn zero_sized_allocation_is_allowed() {
        let mut arena = BumpArena::with_capacity(8);
        let empty = arena.alloc(0, 8).expect("fits");
        assert!(empty.is_empty());
        assert_eq!(arena.used(), 0);
    }

    #[test]
    fn writes_are_isolated_between_allocations() {
        let mut arena = BumpArena::with_capacity(16);
        arena
            .alloc(4, 4)
            .expect("fits")
            .copy_from_slice(&[1, 2, 3, 4]);
        let second = arena.alloc(4, 4).expect("fits");
        assert!(second.iter().all(|&byte| byte == 0));
        second.copy_from_slice(&[9, 9, 9, 9]);

        let view = arena.buffer.as_slice();
        assert_eq!(&view[0..4], &[1, 2, 3, 4]);
        assert_eq!(&view[4..8], &[9, 9, 9, 9]);
    }
}
