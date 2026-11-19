// ch08/free_list.cpp: First-fit free-list allocator with in-band headers,
// block splitting, and adjacent free-block coalescing.
// Written with flat control flow (early returns and small helpers) to keep logic clear.
#include <sys/mman.h>
#include <unistd.h>
#include <cassert>
#include <cstdint>
#include <cstdio>

// Metadata stored immediately before every user payload (24 bytes on 64-bit systems).
struct BlockHeader {
    size_t payload_bytes;    // Usable payload bytes immediately following this header
    bool is_free;            // true = available; false = owned by caller
    BlockHeader* next_block; // Next block in physical address order inside the arena
};

constexpr size_t kMinSplitPayload = 16;

struct FreeListHeap {
    uint8_t* arena_base;
    size_t arena_capacity;
    BlockHeader* head_block;

    static FreeListHeap create(size_t capacity_bytes) {
        void* mapped = mmap(nullptr, capacity_bytes, PROT_READ | PROT_WRITE,
                            MAP_PRIVATE | MAP_ANON, -1, 0);
        if (mapped == MAP_FAILED) {
            perror("mmap");
            return {nullptr, 0, nullptr};
        }

        auto* initial_header = static_cast<BlockHeader*>(mapped);
        initial_header->payload_bytes = capacity_bytes - sizeof(BlockHeader);
        initial_header->is_free = true;
        initial_header->next_block = nullptr;

        return {static_cast<uint8_t*>(mapped), capacity_bytes, initial_header};
    }

    // Splits `block` if the leftover space fits both a new BlockHeader and >= 16 payload bytes.
    static void split_if_large_enough(BlockHeader* block, size_t requested_bytes) {
        size_t leftover_bytes = block->payload_bytes - requested_bytes;
        if (leftover_bytes < sizeof(BlockHeader) + kMinSplitPayload) {
            return;
        }

        // `block + 1` steps past the 24-byte header to the first byte of the user payload.
        uint8_t* payload_start = reinterpret_cast<uint8_t*>(block + 1);
        auto* split_header = reinterpret_cast<BlockHeader*>(payload_start + requested_bytes);

        split_header->payload_bytes = leftover_bytes - sizeof(BlockHeader);
        split_header->is_free = true;
        split_header->next_block = block->next_block;

        block->payload_bytes = requested_bytes;
        block->next_block = split_header;
    }

    // Returns true when `current` and `neighbor` are both free and physically contiguous.
    static bool can_coalesce(const BlockHeader* current, const BlockHeader* neighbor) {
        if (!current->is_free || !neighbor->is_free) return false;
        const uint8_t* current_end =
            reinterpret_cast<const uint8_t*>(current + 1) + current->payload_bytes;
        return reinterpret_cast<const uint8_t*>(neighbor) == current_end;
    }

    // First-fit allocation: returns a payload pointer or nullptr if no free block fits.
    void* alloc(size_t requested_bytes) {
        for (BlockHeader* current = head_block; current != nullptr; current = current->next_block) {
            if (!current->is_free || current->payload_bytes < requested_bytes) {
                continue;
            }
            split_if_large_enough(current, requested_bytes);
            current->is_free = false;
            return reinterpret_cast<uint8_t*>(current + 1);
        }
        return nullptr;
    }

    // Releases a payload pointer and merges any physically adjacent free blocks.
    void free(void* user_payload_ptr) {
        // Step backward by sizeof(BlockHeader) (24 bytes) to recover the hidden header.
        auto* header = reinterpret_cast<BlockHeader*>(
            static_cast<uint8_t*>(user_payload_ptr) - sizeof(BlockHeader));
        header->is_free = true;
        coalesce_adjacent_free_blocks();
    }

    void coalesce_adjacent_free_blocks() {
        BlockHeader* current = head_block;
        while (current != nullptr && current->next_block != nullptr) {
            BlockHeader* neighbor = current->next_block;
            if (!can_coalesce(current, neighbor)) {
                current = neighbor;
                continue;
            }
            // Absorb both the neighbor's payload and its redundant 24-byte header.
            current->payload_bytes += sizeof(BlockHeader) + neighbor->payload_bytes;
            current->next_block = neighbor->next_block;
        }
    }

    void dump_block_map() const {
        printf("  block map:\n");
        int block_index = 0;
        for (BlockHeader* current = head_block; current != nullptr;
             current = current->next_block, ++block_index) {
            size_t byte_offset =
                static_cast<size_t>(reinterpret_cast<uint8_t*>(current) - arena_base);
            printf("    [%d] offset %zu  payload %zu  %s\n",
                   block_index, byte_offset, current->payload_bytes,
                   current->is_free ? "free" : "used");
        }
    }

    void destroy() { munmap(arena_base, arena_capacity); }
};

int main() {
    FreeListHeap heap = FreeListHeap::create(256 * 1024);
    printf("arena: %p, %zu bytes, header %zu bytes\n\n",
           static_cast<void*>(heap.arena_base), heap.arena_capacity, sizeof(BlockHeader));

    void* block_a = heap.alloc(100);
    void* block_b = heap.alloc(200);
    void* block_c = heap.alloc(300);

    printf("after alloc(100), alloc(200), alloc(300):\n");
    heap.dump_block_map();

    heap.free(block_b);
    printf("\nafter free(block_b):\n");
    heap.dump_block_map();

    void* block_d = heap.alloc(150);
    assert(block_d == block_b);
    printf("\nafter alloc(150) into block_b's hole:\n");
    heap.dump_block_map();
    printf("block_d reuses block_b's address: yes\n");

    heap.free(block_a);
    heap.free(block_d);
    heap.free(block_c);
    assert(heap.head_block->is_free && heap.head_block->next_block == nullptr);

    printf("\nafter freeing all blocks (coalesced back to 1 free block):\n");
    heap.dump_block_map();

    heap.destroy();
}
