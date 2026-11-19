// ch08/index_arena.rs: Level 1 arena: a minimal, zero-unsafe index pool.
// Nodes live contiguously inside one Vec<T> and link via copyable Id(usize) handles.
struct Arena<T> {
    items: Vec<T>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct Id(usize);

impl<T> Arena<T> {
    fn new() -> Self {
        Self { items: Vec::new() }
    }

    fn alloc(&mut self, value: T) -> Id {
        self.items.push(value);
        Id(self.items.len() - 1)
    }

    fn get(&self, id: Id) -> &T {
        &self.items[id.0]
    }

    fn len(&self) -> usize {
        self.items.len()
    }

    // Reclaims all nodes in O(1) while retaining the backing capacity for reuse.
    fn reset(&mut self) {
        self.items.clear();
    }
}

struct Node {
    value: i64,
    next: Option<Id>,
}

fn main() {
    let mut arena = Arena::new();
    let mut head: Option<Id> = None;

    for i in 0..10_000_i64 {
        head = Some(arena.alloc(Node { value: i, next: head }));
    }

    let mut sum = 0_i64;
    let mut visited = 0_usize;
    let mut cursor = head;
    while let Some(id) = cursor {
        let node = arena.get(id);
        sum += node.value;
        visited += 1;
        cursor = node.next;
    }

    assert_eq!(visited, 10_000);
    assert_eq!(sum, 49_995_000);
    println!("index arena: {} nodes allocated, sum = {sum} (verified)", arena.len());

    arena.reset();
    assert_eq!(arena.len(), 0);
    println!("after reset: {} nodes", arena.len());
}
