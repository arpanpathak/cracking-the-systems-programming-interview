// ch08/index_arena.cpp: Level 1 arena: a minimal, zero-raw-pointer index pool.
// Nodes live contiguously inside one std::vector<T> and link via copyable Id handles.
#include <cassert>
#include <cstddef>
#include <cstdio>
#include <optional>
#include <utility>
#include <vector>

struct Id {
    size_t index;
};

template <typename T>
class Arena {
public:
    Id alloc(T value) {
        items_.push_back(std::move(value));
        return Id{items_.size() - 1};
    }

    const T& get(Id id) const { return items_[id.index]; }
    size_t len() const { return items_.size(); }
    void reset() { items_.clear(); }  // Reclaims all nodes while keeping capacity

private:
    std::vector<T> items_;
};

struct Node {
    int value;
    std::optional<Id> next;
};

int main() {
    Arena<Node> arena;
    std::optional<Id> head = std::nullopt;

    for (int i = 0; i < 10'000; ++i) {
        head = arena.alloc(Node{i, head});
    }

    long long sum = 0;
    size_t visited = 0;
    std::optional<Id> cursor = head;
    while (cursor.has_value()) {
        const Node& node = arena.get(*cursor);
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
