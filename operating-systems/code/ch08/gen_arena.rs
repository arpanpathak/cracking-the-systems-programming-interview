// ch08/gen_arena.rs: Level 2 arena: a zero-unsafe generational arena with an
// intrusive free list threaded directly through empty slots.
//
// Each handle pairs a slot index with a generation counter. Freeing a slot
// increments its generation, so stale handles return None instead of silently
// reading a newer object that reused the same slot.

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct Handle {
    index: u32,
    generation: u32,
}

enum Entry<T> {
    Occupied(T),
    Free { next_free: Option<u32> },
}

impl<T> Entry<T> {
    fn into_value(self) -> Option<T> {
        match self {
            Entry::Occupied(value) => Some(value),
            Entry::Free { .. } => None,
        }
    }
}

struct Slot<T> {
    generation: u32,
    entry: Entry<T>,
}

impl<T> Slot<T> {
    fn is_occupied(&self) -> bool {
        matches!(self.entry, Entry::Occupied(_))
    }
}

struct GenArena<T> {
    slots: Vec<Slot<T>>,
    free_head: Option<u32>,
}

impl<T> GenArena<T> {
    fn new() -> Self {
        Self {
            slots: Vec::new(),
            free_head: None,
        }
    }

    // Pops the head index from the intrusive free list, if any freed slot exists.
    fn pop_free_slot(&mut self) -> Option<u32> {
        let index = self.free_head?;

        if let Entry::Free { next_free } = self.slots[index as usize].entry {
            self.free_head = next_free;
        }

        Some(index)
    }

    // Inserts `value` into a recycled slot in O(1), or appends a fresh slot.
    fn insert(&mut self, value: T) -> Handle {
        if let Some(index) = self.pop_free_slot() {
            let slot = &mut self.slots[index as usize];
            slot.entry = Entry::Occupied(value);

            return Handle {
                index,
                generation: slot.generation,
            };
        }

        let index = self.slots.len() as u32;
        self.slots.push(Slot {
            generation: 0,
            entry: Entry::Occupied(value),
        });

        Handle {
            index,
            generation: 0,
        }
    }

    // Looks up `handle` in O(1), rejecting stale handles whose generation mismatches.
    fn get(&self, handle: Handle) -> Option<&T> {
        let slot = self.slots.get(handle.index as usize)?;

        if slot.generation != handle.generation {
            return None;
        }

        match &slot.entry {
            Entry::Occupied(value) => Some(value),
            Entry::Free { .. } => None,
        }
    }

    // Frees `handle` in O(1), advances its slot's generation, and pushes it onto `free_head`.
    fn remove(&mut self, handle: Handle) -> Option<T> {
        let slot = self.slots.get_mut(handle.index as usize)?;

        // Reject stale handles and double-removes before modifying the free list.
        if slot.generation != handle.generation || !slot.is_occupied() {
            return None;
        }

        // Thread this slot onto the front of the intrusive free list.
        let next_free = self.free_head;
        let old_entry = std::mem::replace(&mut slot.entry, Entry::Free { next_free });

        // Bump generation so every existing copy of `handle` becomes permanently stale.
        slot.generation = slot.generation.wrapping_add(1);
        self.free_head = Some(handle.index);

        old_entry.into_value()
    }

    fn slot_count(&self) -> usize {
        self.slots.len()
    }
}

fn main() {
    let mut arena = GenArena::new();

    // 1. Insert two objects into fresh slots 0 and 1 (both at generation 0).
    let alpha = arena.insert(String::from("alpha"));
    let beta = arena.insert(String::from("beta"));

    assert_eq!(alpha, Handle { index: 0, generation: 0 });
    assert_eq!(beta, Handle { index: 1, generation: 0 });

    // 2. Remove `alpha`; slot 0 increments to generation 1 and joins `free_head`.
    let removed = arena.remove(alpha);
    assert_eq!(removed.as_deref(), Some("alpha"));
    assert_eq!(arena.remove(alpha), None); // Double-remove safely ignored

    // 3. Insert `gamma`; O(1) reuse of slot 0 without growing the backing Vec.
    let gamma = arena.insert(String::from("gamma"));
    assert_eq!(gamma, Handle { index: 0, generation: 1 });
    assert_eq!(arena.slot_count(), 2);

    // 4. Stale `alpha` handle (index 0, gen 0) is rejected instead of returning "gamma".
    assert_eq!(arena.get(alpha), None);
    assert_eq!(arena.get(gamma).map(String::as_str), Some("gamma"));
    assert_eq!(arena.get(beta).map(String::as_str), Some("beta"));

    println!("reused slot {} at generation {} (backing vec slots = {})",
             gamma.index, gamma.generation, arena.slot_count());
    println!("stale handle (idx=0, gen=0) -> {:?} (ABA prevented)", arena.get(alpha));
    println!("live  handle (idx=0, gen=1) -> {:?}", arena.get(gamma));
}
