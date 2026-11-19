// ch08/free_list.cpp: First-fit free-list allocator with in-band headers,
// block splitting, and adjacent free-block coalescing.
#include <sys/mman.h>
#include <unistd.h>
#include <cstdint>
#include <cstdio>

// Metadata stored immediately before every user payload (24 bytes on 64-bit systems).
struct BlockHeader {
    size_t payload_bytes;    // Usable payload bytes immediately following this header
    bool is_free;            // true = available for allocation; false = owned by caller
    BlockHeader* next_block; // Next block in physical address order inside the arena
};

// Minimum usable payload required before splitting a free block, preventing tiny fragments.
constexpr size_t kMinSplitPayload = 16;

struct FreeListHeap {
    uint8_t* arena_base;      // Page-aligned base address returned by mmap()
    size_t arena_capacity;    // Total arena capacity in bytes
    BlockHeader* head_block;  // First block header at offset 0 of the arena

    static FreeListHeap create(size_t capacity_bytes) {
        void* mapped = mmap(nullptr, capacity_bytes, PROT_READ | PROT_WRITE,
                            MAP_PRIVATE | MAP_ANON, -1, 0);
        if (mapped == MAP_FAILED) {
            perror("mmap");
            return {nullptr, 0, nullptr};
        }

        // Initialize the entire arena as one contiguous free block.
        auto* initial_header = static_cast<BlockHeader*>(mapped);
        initial_header->payload_bytes = capacity_bytes - sizeof(BlockHeader);
        initial_header->is_free = true;
        initial_header->next_block = nullptr;

        return {static_cast<uint8_t*>(mapped), capacity_bytes, initial_header};
    }

    // First-fit allocation: finds the first free block large enough for `requested_bytes`.
    void* alloc(size_t requested_bytes) {
        for (BlockHeader* current = head_block; current != nullptr; current = current->next_block) {
            if (!current->is_free || current->payload_bytes < requested_bytes) {
                continue;
            }

            size_t leftover_bytes = current->payload_bytes - requested_bytes;
            // Split the block only if the remaining space can hold both a new BlockHeader
            // and at least `kMinSplitPayload` (16) bytes of usable payload.
            if (leftover_bytes >= sizeof(BlockHeader) + kMinSplitPayload) {
                // In C++, `current + 1` advances by sizeof(BlockHeader) (24 bytes) to the start
                // of the payload. Adding `requested_bytes` locates the exact start of the remainder.
                uint8_t* payload_start = reinterpret_cast<uint8_t*>(current + 1);
                auto* split_header = reinterpret_cast<BlockHeader*>(payload_start + requested_bytes);

                split_header->payload_bytes = leftover_bytes - sizeof(BlockHeader);
                split_header->is_free = true;
                split_header->next_block = current->next_block;

                current->payload_bytes = requested_bytes;
                current->next_block = split_header;
            }

            current->is_free = false;
            // Return the pointer immediately after the header (the start of the user payload).
            return reinterpret_cast<uint8_t*>(current + 1);
        }

        return nullptr;
    }

    // Releases a previously allocated payload pointer and merges adjacent free blocks.
    void free(void* user_payload_ptr) {
        // Step backward by one `sizeof(BlockHeader)` (24 bytes) to recover the hidden header.
        BlockHeader* header = reinterpret_cast<BlockHeader*>(
            static_cast<uint8_t*>(user_payload_ptr) - sizeof(BlockHeader));
        header->is_free = true;
        coalesce_adjacent_free_blocks();
    }

    // Linear pass merging any two physically adjacent free blocks into one larger block.
    void coalesce_adjacent_free_blocks() {
        BlockHeader* current = head_block;
        while (current != nullptr && current->next_block != nullptr) {
            BlockHeader* neighbor = current->next_block;
            uint8_t* current_end_addr =
                reinterpret_cast<uint8_t*>(current + 1) + current->payload_bytes;
            bool is_physically_adjacent =
                reinterpret_cast<uint8_t*>(neighbor) == current_end_addr;

            if (current->is_free && neighbor->is_free && is_physically_adjacent) {
                // Reclaim both the neighbor's payload AND its now-redundant 24-byte header.
                current->payload_bytes += sizeof(BlockHeader) + neighbor->payload_bytes;
                current->next_block = neighbor->next_block;
            } else {
                current = current->next_block;
            }
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

    // Reuses block_b's 200-byte hole: 150B used + 24B new header + 26B free remainder.
    void* block_d = heap.alloc(150);
    printf("\nafter alloc(150) into block_b's hole:\n");
    heap.dump_block_map();
    printf("block_d reuses block_b's address: %s\n", block_d == block_b ? "yes" : "no");

    heap.free(block_a);
    heap.free(block_d);
    heap.free(block_c);

    printf("\nafter freeing all blocks (coalesced back to 1 free block):\n");
    heap.dump_block_map();

    heap.destroy();
}
