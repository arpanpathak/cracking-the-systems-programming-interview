// ch08/index_arena.rs: Level 1 arena: a completely safe, zero-unsafe index pool.
// Nodes live contiguously inside one Vec<T> and reference each other via copyable
// NodeId indices, avoiding raw pointers, self-referential lifetimes, and unsafe blocks.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct NodeId(usize);

struct IndexArena<T> {
    items: Vec<T>,
}

impl<T> IndexArena<T> {
    fn new() -> Self {
        Self { items: Vec::new() }
    }

    fn alloc(&mut self, value: T) -> NodeId {
        let id = self.items.len();
        self.items.push(value);
        NodeId(id)
    }

    fn get(&self, id: NodeId) -> &T {
        &self.items[id.0]
    }

    fn len(&self) -> usize {
        self.items.len()
    }

    // Reclaims all nodes in O(1) while retaining the backing heap buffer for reuse.
    fn reset(&mut self) {
        self.items.clear();
    }
}

struct ListNode {
    value: i64,
    next: Option<NodeId>,
}

fn main() {
    let mut arena = IndexArena::new();
    let mut head: Option<NodeId> = None;

    for i in 0..10_000_i64 {
        head = Some(arena.alloc(ListNode { value: i, next: head }));
    }

    // Traverse the 10,000-node list stored contiguously inside the arena.
    let mut sum: i64 = 0;
    let mut visited: usize = 0;
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
