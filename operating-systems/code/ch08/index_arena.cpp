// ch08/index_arena.cpp: Level 1 arena: a safe, zero-raw-pointer index pool.
// All nodes live contiguously inside one std::vector; integer indices replace
// raw pointers, eliminating dangling references and per-node heap allocations.
#include <cassert>
#include <cstddef>
#include <cstdio>
#include <optional>
#include <vector>

struct NodeId {
    size_t index;
};

template <typename T>
class IndexArena {
public:
    NodeId alloc(T value) {
        size_t id = items_.size();
        items_.push_back(std::move(value));
        return NodeId{id};
    }

    const T& get(NodeId id) const { return items_[id.index]; }
    size_t len() const { return items_.size(); }
    void reset() { items_.clear(); }  // Reclaims all nodes while keeping backing capacity

private:
    std::vector<T> items_;
};

struct ListNode {
    int value;
    std::optional<NodeId> next;
};

int main() {
    IndexArena<ListNode> arena;
    std::optional<NodeId> head = std::nullopt;

    for (int i = 0; i < 10'000; ++i) {
        head = arena.alloc(ListNode{i, head});
    }

    // Walk the 10,000-node list stored contiguously inside the arena.
    long long sum = 0;
    size_t visited = 0;
    std::optional<NodeId> cursor = head;
    while (cursor.has_value()) {
        const ListNode& node = arena.get(*cursor);
        sum += node.value;
        ++visited;
        cursor = node.next;
    }

    assert(visited == 10'000);
    assert(sum == 49'995'000);
    printf("index arena: %zu nodes allocated, sum = %lld (verified)\n", arena.len(), sum);

    arena.reset();
    assert(arena.len() == 0);
    printf("after reset: %zu nodes\n", arena.len());
}
