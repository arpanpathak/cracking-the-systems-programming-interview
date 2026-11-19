// ch19/free_list_allocator.cpp: a first-fit allocator with splitting and coalescing.
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <new>

constexpr size_t kAlignment = 16;
constexpr size_t kArenaBytes = 1024;

/// Stored immediately before every payload. The list links blocks in address order.
struct alignas(kAlignment) BlockHeader {
    size_t payload_bytes;
    bool is_free;
    BlockHeader* next;
};

constexpr size_t kHeaderBytes = sizeof(BlockHeader);
constexpr size_t kMinimumSplitBytes = kHeaderBytes + kAlignment;

/// Rounds `value` up to the next multiple of kAlignment.
size_t align_up(size_t value) {
    return (value + kAlignment - 1) & ~(kAlignment - 1);
}

class FreeListAllocator {
public:
    FreeListAllocator() {
        size_t payload_bytes = kArenaBytes - kHeaderBytes;

        first_ = new (arena_) BlockHeader{payload_bytes, true, nullptr};
    }

    /// Returns a payload of at least `requested_bytes`, or nullptr when no block fits.
    void* allocate(size_t requested_bytes) {
        // A larger request can never fit, and rounding it up could overflow.
        if (requested_bytes > kArenaBytes) return nullptr;

        size_t payload_bytes = align_up(requested_bytes);

        BlockHeader* block = find_first_fit(payload_bytes);
        if (block == nullptr) return nullptr;

        split_if_large(block, payload_bytes);
        block->is_free = false;

        return payload_of(block);
    }

    /// Marks the block free and merges it with free neighbors.
    void release(void* payload) {
        if (payload == nullptr) return;

        header_of(payload)->is_free = true;
        coalesce();
    }

    void print_blocks(const char* title) const {
        printf("%s\n", title);

        for (const BlockHeader* block = first_; block != nullptr; block = block->next) {
            size_t offset = reinterpret_cast<const uint8_t*>(block) - arena_;
            const char* state = block->is_free ? "free" : "used";

            size_t payload_bytes = block->payload_bytes;

            printf("  offset %4zu  payload %4zu  %s\n", offset, payload_bytes, state);
        }
    }

private:
    static uint8_t* payload_of(BlockHeader* block) {
        return reinterpret_cast<uint8_t*>(block) + kHeaderBytes;
    }

    static BlockHeader* header_of(void* payload) {
        uint8_t* header_address = static_cast<uint8_t*>(payload) - kHeaderBytes;

        return reinterpret_cast<BlockHeader*>(header_address);
    }

    BlockHeader* find_first_fit(size_t payload_bytes) const {
        for (BlockHeader* block = first_; block != nullptr; block = block->next) {
            if (block->is_free && block->payload_bytes >= payload_bytes) return block;
        }

        return nullptr;
    }

    /// Cuts the unused tail of `block` into a new free block, if the tail is large enough.
    void split_if_large(BlockHeader* block, size_t payload_bytes) {
        size_t spare_bytes = block->payload_bytes - payload_bytes;
        if (spare_bytes < kMinimumSplitBytes) return;

        uint8_t* tail_address = payload_of(block) + payload_bytes;
        size_t tail_payload_bytes = spare_bytes - kHeaderBytes;

        BlockHeader* following = block->next;

        BlockHeader* tail = new (tail_address) BlockHeader{tail_payload_bytes, true, following};

        block->payload_bytes = payload_bytes;
        block->next = tail;
    }

    /// Merges every pair of free blocks that are next to each other.
    void coalesce() {
        BlockHeader* block = first_;

        while (block->next != nullptr) {
            BlockHeader* following = block->next;

            if (block->is_free && following->is_free) {
                block->payload_bytes += kHeaderBytes + following->payload_bytes;
                block->next = following->next;
                continue;
            }

            block = following;
        }
    }

    alignas(kAlignment) uint8_t arena_[kArenaBytes];
    BlockHeader* first_;
};

int main() {
    FreeListAllocator heap;
    printf("arena %zu bytes, header %zu bytes\n\n", kArenaBytes, kHeaderBytes);

    void* first = heap.allocate(100);
    void* second = heap.allocate(200);
    void* third = heap.allocate(300);
    heap.print_blocks("after allocate(100), allocate(200), allocate(300):");

    heap.release(second);
    heap.print_blocks("\nafter release(second):");

    void* fourth = heap.allocate(150);
    heap.print_blocks("\nafter allocate(150):");
    printf("fourth reuses the block of second: %s\n", fourth == second ? "yes" : "no");

    heap.release(first);
    heap.release(fourth);
    heap.release(third);
    heap.print_blocks("\nafter releasing everything:");
}
