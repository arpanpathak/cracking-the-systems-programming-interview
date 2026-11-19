// ch08/free_list.cpp: a first-fit allocator with headers, splitting, and coalescing.
#include <sys/mman.h>
#include <unistd.h>
#include <cstdint>
#include <cstdio>

struct Block {
    size_t size;    // payload bytes available in this block
    bool free;
    Block* next;
};

struct Heap {
    uint8_t* base;
    size_t size;
    Block* free_head;

    static Heap create(size_t bytes) {
        void* p = mmap(nullptr, bytes, PROT_READ | PROT_WRITE,
                       MAP_PRIVATE | MAP_ANON, -1, 0);
        if (p == MAP_FAILED) {
            perror("mmap");
            return {nullptr, 0, nullptr};
        }

        Heap h{static_cast<uint8_t*>(p), bytes, static_cast<Block*>(p)};
        h.free_head->size = bytes - sizeof(Block);
        h.free_head->free = true;
        h.free_head->next = nullptr;

        return h;
    }

    void* alloc(size_t n) {
        for (Block* b = free_head; b != nullptr; b = b->next) {
            if (!b->free || b->size < n) continue;

            size_t rest = b->size - n;
            if (rest >= sizeof(Block) + 16) {
                // Split: carve a free block out of the remainder.
                Block* nb = reinterpret_cast<Block*>(
                    reinterpret_cast<uint8_t*>(b + 1) + n);
                nb->size = rest - sizeof(Block);
                nb->free = true;
                nb->next = b->next;

                b->size = n;
                b->next = nb;
            }

            b->free = false;
            return reinterpret_cast<uint8_t*>(b + 1);
        }

        return nullptr;
    }

    void free(void* p) {
        Block* b = reinterpret_cast<Block*>(static_cast<uint8_t*>(p)) - 1;
        b->free = true;
        coalesce();
    }

    void coalesce() {
        Block* b = free_head;
        while (b != nullptr && b->next != nullptr) {
            Block* n = b->next;
            uint8_t* b_end = reinterpret_cast<uint8_t*>(b + 1) + b->size;
            bool adjacent = reinterpret_cast<uint8_t*>(n) == b_end;

            if (b->free && n->free && adjacent) {
                b->size += sizeof(Block) + n->size;
                b->next = n->next;
            } else {
                b = b->next;
            }
        }
    }

    void dump() {
        printf("  block map:\n");

        int i = 0;
        for (Block* b = free_head; b != nullptr; b = b->next, ++i) {
            printf("    [%d] offset %zu size %zu %s\n", i,
                   static_cast<size_t>(reinterpret_cast<uint8_t*>(b) - base),
                   b->size, b->free ? "free" : "used");
        }
    }

    void destroy() { munmap(base, size); }
};

int main() {
    Heap h = Heap::create(256 * 1024);
    printf("arena: %p, %zu bytes, header %zu bytes\n\n",
           static_cast<void*>(h.base), h.size, sizeof(Block));

    void* a = h.alloc(100);
    void* b = h.alloc(200);
    void* c = h.alloc(300);

    printf("after alloc(100), alloc(200), alloc(300):\n");
    h.dump();

    h.free(b);
    printf("\nafter free(b):\n");
    h.dump();

    void* d = h.alloc(150);
    printf("\nafter alloc(150) into the hole left by b:\n");
    h.dump();
    printf("d reuses b's block: %s\n", d == b ? "yes" : "no");

    h.free(a);
    h.free(d);
    h.free(c);

    printf("\nafter freeing everything:\n");
    h.dump();

    h.destroy();
}
