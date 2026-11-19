// ch08/bump.cpp: the simplest allocator: hand out memory, never reclaim it.
#include <sys/mman.h>
#include <unistd.h>
#include <cstdint>
#include <cstdio>

struct Bump {
    uint8_t* base;
    size_t size;
    size_t offset;

    static Bump create(size_t bytes) {
        void* p = mmap(nullptr, bytes, PROT_READ | PROT_WRITE,
                       MAP_PRIVATE | MAP_ANON, -1, 0);
        if (p == MAP_FAILED) {
            perror("mmap");
            return {nullptr, 0, 0};
        }

        return {static_cast<uint8_t*>(p), bytes, 0};
    }

    void* alloc(size_t n, size_t align) {
        size_t aligned = (offset + align - 1) & ~(align - 1);
        if (aligned + n > size) return nullptr;

        offset = aligned + n;
        return base + aligned;
    }

    void reset() { offset = 0; }
    void destroy() { munmap(base, size); }
};

int main() {
    Bump b = Bump::create(64 * 1024);
    printf("arena: %p, %zu bytes\n\n", static_cast<void*>(b.base), b.size);

    void* a = b.alloc(8, 8);
    void* c = b.alloc(3, 8);
    void* d = b.alloc(16, 16);

    printf("alloc(8,8)   -> %p (offset 0)\n", a);
    printf("alloc(3,8)   -> %p (offset 8)\n", c);
    printf("alloc(16,16) -> %p (offset 16)\n", d);

    // The only way to reuse memory is to reset the whole arena.
    b.reset();
    void* e = b.alloc(8, 8);
    printf("after reset, alloc(8,8) -> %p (same as first: %s)\n", e,
           e == a ? "yes" : "no");

    b.destroy();
}
