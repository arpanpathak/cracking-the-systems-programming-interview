// ch08/bump.cpp: A linear bump (arena) allocator with explicit power-of-two alignment.
// Allocations advance a single monotonic offset; individual objects cannot be freed,
// and reset() reclaims the entire arena in O(1) time.
#include <sys/mman.h>
#include <unistd.h>
#include <cstdint>
#include <cstdio>

struct BumpAllocator {
    uint8_t* arena_base;     // Page-aligned start address returned by mmap()
    size_t arena_capacity;   // Total size of the virtual mapping in bytes
    size_t next_offset;      // Byte offset of the next unallocated byte

    static BumpAllocator create(size_t capacity_bytes) {
        // Request a private, zero-initialized anonymous virtual memory region from the kernel.
        // Passing nullptr lets the kernel choose the virtual base address; fd = -1 and offset = 0
        // are required by POSIX when mapping anonymous (non-file-backed) memory.
        void* mapped = mmap(nullptr, capacity_bytes, PROT_READ | PROT_WRITE,
                            MAP_PRIVATE | MAP_ANON, -1, 0);
        if (mapped == MAP_FAILED) {
            perror("mmap");
            return {nullptr, 0, 0};
        }

        return {static_cast<uint8_t*>(mapped), capacity_bytes, 0};
    }

    // Allocates `requested_bytes` aligned upward to a power-of-two `alignment` boundary.
    void* alloc(size_t requested_bytes, size_t alignment) {
        // Round `next_offset` up to the smallest multiple of `alignment` >= `next_offset`.
        // Example: next_offset = 11, alignment = 16:
        //   (11 + 15) & ~15  =  26 & 0xFFFF...FFF0  =  16  (inserts 5 bytes of padding: 11..15).
        size_t aligned_offset = (next_offset + alignment - 1) & ~(alignment - 1);
        if (aligned_offset + requested_bytes > arena_capacity) {
            return nullptr;  // Arena exhausted
        }

        next_offset = aligned_offset + requested_bytes;
        return arena_base + aligned_offset;
    }

    // Reclaims all allocations simultaneously by rewinding the bump pointer to zero.
    void reset() { next_offset = 0; }

    // Returns the entire virtual memory mapping to the operating system.
    void destroy() { munmap(arena_base, arena_capacity); }
};

int main() {
    BumpAllocator allocator = BumpAllocator::create(64 * 1024);
    printf("arena: %p, %zu bytes\n\n",
           static_cast<void*>(allocator.arena_base), allocator.arena_capacity);

    // 1. Offset 0 is already 8-byte aligned -> occupies bytes [0, 8), next_offset becomes 8.
    void* first_block = allocator.alloc(8, 8);
    // 2. Offset 8 is already 8-byte aligned -> occupies bytes [8, 11), next_offset becomes 11.
    void* small_block = allocator.alloc(3, 8);
    // 3. Offset 11 is NOT 16-byte aligned -> inserts 5 bytes of padding [11, 16),
    //    then allocates 16 bytes at [16, 32), advancing next_offset to 32.
    void* aligned_block = allocator.alloc(16, 16);

    printf("alloc(8,  align=8)  -> %p (offset 0,  bytes 0..7)\n", first_block);
    printf("alloc(3,  align=8)  -> %p (offset 8,  bytes 8..10)\n", small_block);
    printf("alloc(16, align=16) -> %p (offset 16, bytes 16..31 after 5B padding)\n", aligned_block);
    printf("next_offset         -> %zu\n\n", allocator.next_offset);

    // Resetting rewinds next_offset to 0 so the arena can be reused immediately.
    allocator.reset();
    void* reused_block = allocator.alloc(8, 8);
    printf("after reset, alloc(8, align=8) -> %p (reuses offset 0: %s)\n",
           reused_block, reused_block == first_block ? "yes" : "no");

    allocator.destroy();
}
