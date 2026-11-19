// ch08/gen_arena.cpp: Level 2 arena: a generational arena with an intrusive
// free list threaded through empty slots (C++20 counterpart to gen_arena.rs).
//
// Each Handle pairs a slot index with a generation counter. Freeing a slot
// increments its generation, so stale handles return nullptr instead of
// silently aliasing a newer object occupying the recycled slot.
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <optional>
#include <string>
#include <utility>
#include <vector>

struct Handle {
    uint32_t index;
    uint32_t generation;

    bool operator==(const Handle&) const = default;
};

template <typename T>
class GenArena {
public:
    // Inserts `value` into a recycled slot in O(1), or appends a fresh slot.
    Handle insert(T value) {
        if (auto index = pop_free_slot()) {
            Slot& slot = slots_[*index];
            slot.value.emplace(std::move(value));
            slot.next_free.reset();

            return Handle{*index, slot.generation};
        }

        uint32_t index = static_cast<uint32_t>(slots_.size());
        slots_.push_back(Slot{0, std::move(value), std::nullopt});

        return Handle{index, 0};
    }

    // Looks up `handle` in O(1), returning nullptr if the handle is stale or freed.
    const T* get(Handle handle) const {
        if (handle.index >= slots_.size()) {
            return nullptr;
        }

        const Slot& slot = slots_[handle.index];
        if (slot.generation != handle.generation || !slot.value.has_value()) {
            return nullptr;
        }

        return &(*slot.value);
    }

    // Frees `handle` in O(1), bumps its slot generation, and pushes it onto `free_head_`.
    std::optional<T> remove(Handle handle) {
        if (handle.index >= slots_.size()) {
            return std::nullopt;
        }

        Slot& slot = slots_[handle.index];

        // Reject stale handles and double-removes before touching the free list.
        if (slot.generation != handle.generation || !slot.value.has_value()) {
            return std::nullopt;
        }

        // Move the live object out and thread this slot onto the intrusive free list.
        std::optional<T> extracted = std::move(slot.value);
        slot.value.reset();
        slot.next_free = free_head_;

        // Advance generation so every existing copy of `handle` becomes permanently stale.
        slot.generation += 1;
        free_head_ = handle.index;

        return extracted;
    }

    size_t slot_count() const { return slots_.size(); }

private:
    // Production allocators overlay `value` and `next_free` inside a std::variant
    // or union (as Rust's `enum Entry<T>` does) so free links consume zero extra bytes.
    struct Slot {
        uint32_t generation;
        std::optional<T> value;
        std::optional<uint32_t> next_free;
    };

    std::optional<uint32_t> pop_free_slot() {
        if (!free_head_.has_value()) {
            return std::nullopt;
        }

        uint32_t index = *free_head_;
        free_head_ = slots_[index].next_free;
        return index;
    }

    std::vector<Slot> slots_;
    std::optional<uint32_t> free_head_ = std::nullopt;
};

int main() {
    GenArena<std::string> arena;

    // 1. Insert two objects into fresh slots 0 and 1 (both at generation 0).
    Handle alpha = arena.insert("alpha");
    Handle beta = arena.insert("beta");

    assert((alpha == Handle{0, 0}));
    assert((beta == Handle{1, 0}));

    // 2. Remove `alpha`; slot 0 bumps to generation 1 and joins `free_head_`.
    std::optional<std::string> removed = arena.remove(alpha);
    assert(removed.has_value() && *removed == "alpha");
    assert(!arena.remove(alpha).has_value());  // Double-remove safely ignored

    // 3. Insert `gamma`; O(1) reuse of slot 0 without growing the backing vector.
    Handle gamma = arena.insert("gamma");
    assert((gamma == Handle{0, 1}));
    assert(arena.slot_count() == 2);

    // 4. Stale `alpha` handle (index 0, gen 0) is rejected instead of returning "gamma".
    assert(arena.get(alpha) == nullptr);
    assert(arena.get(gamma) != nullptr && *arena.get(gamma) == "gamma");
    assert(arena.get(beta) != nullptr && *arena.get(beta) == "beta");

    printf("reused slot %u at generation %u (backing vector slots = %zu)\n",
           gamma.index, gamma.generation, arena.slot_count());
    printf("stale handle (idx=0, gen=0) -> %s (ABA prevented)\n",
           arena.get(alpha) == nullptr ? "nullptr" : arena.get(alpha)->c_str());
    printf("live  handle (idx=0, gen=1) -> \"%s\"\n", arena.get(gamma)->c_str());
}
