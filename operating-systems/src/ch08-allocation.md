# 8. Memory Allocation and Management Strategies

While the operating system manages memory in coarse-grained units, typically 4 KiB pages, application-level software requires a mechanism for managing objects of diverse and often much smaller sizes. A memory allocator bridges this granularity gap by requesting large, contiguous regions of memory from the kernel and subdividing them into smaller, appropriately sized blocks for the program.

## 8.1 The Allocator Interface and Efficiency Constraints

A functional allocator provides two primary primitives: `alloc(n)`, which returns an aligned address for `n` bytes of memory, and `free(p)`, which returns a previously allocated block to the allocator for future reuse. The primary efficiency constraint is the high cost of system calls; therefore, an allocator must minimize its interaction with the kernel by requesting large regions and managing the lifecycle of these regions internally.

Allocators are distinguished by three architectural decisions: the placement strategy for new objects, the metadata utilized for block tracking, and the mechanism for reclaimed block reuse.

### 8.1.1 Requesting Raw Arenas from the Kernel (`mmap`)

Both allocators implemented in this chapter acquire their backing memory—an **arena**—directly from the kernel via the POSIX `mmap` system call rather than calling `malloc`:

```text
mmap(nullptr, capacity_bytes, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANON, -1, 0)
```

Each argument encodes a specific architectural contract with the kernel virtual-memory manager (detailed in Section 7.3.1):
- **`nullptr` (`ptr::null_mut()`):** Delegates virtual base-address selection to the kernel, guaranteeing a page-aligned starting address.
- **`capacity_bytes`:** Total contiguous virtual reservation requested (rounded upward by the kernel to whole hardware pages).
- **`PROT_READ | PROT_WRITE`:** Programs the hardware Page Table Entry (PTE) permission bits so the process can both load from and store into the arena while preserving non-executable (`NX = 1`) protection.
- **`MAP_PRIVATE | MAP_ANON`:** Allocates private, zero-initialized anonymous RAM unbacked by any disk file (`MAP_ANON`), ensuring modifications remain strictly isolated to this process (`MAP_PRIVATE`).
- **`-1, 0`:** Because `MAP_ANON` specifies no backing file, POSIX requires passing `-1` as the file descriptor and `0` as the file offset.
- **Error Check and Release:** `mmap` returns the sentinel `MAP_FAILED` (`(void*)-1`) on failure rather than `nullptr`. When the arena is destroyed, `munmap(arena_base, arena_capacity)` unmaps the virtual pages and returns their physical frames to the operating system.

### 8.1.2 Hardware Alignment and Bitwise Rounding

Before subdividing an arena into individual objects, an allocator must enforce **memory alignment**. Modern 64-bit processors transfer data between caches and registers in aligned 8-byte words, 16-byte SIMD vectors, and 64-byte cache lines. A type requiring alignment `A` (always a power of two: 1, 2, 4, 8, 16, or 64 bytes) must start at an address divisible by `A` (`address % A == 0`); unaligned accesses split across cache-line boundaries, break single-line hardware atomicity, or trigger hardware alignment faults (`#AC` / `SIGBUS`). Both the System V AMD64 ABI and ARM64 AAPCS64 therefore require **16-byte alignment** for general-purpose heap allocations.

Given a current cursor `next_offset` and a power-of-two alignment `A = 2^k`, the smallest multiple of `A` greater than or equal to `next_offset` is computed in two instructions:

```text
aligned_offset = (next_offset + A - 1) & ~(A - 1)
```

Because `A = 2^k`, `A - 1` has `k` trailing binary `1` bits, and `~(A - 1)` clears those lowest `k` bits. Adding `A - 1` advances any misaligned offset into the next multiple of `A` while leaving already-aligned offsets unchanged. Tracing three sequential allocations starting from `next_offset = 0` illustrates how alignment padding arises:
1. **`alloc(8, align=8)`:** Offset `0` is already 8-byte aligned (`(0 + 7) & ~7 = 0`). Occupies **bytes `0..7`**, advancing `next_offset` to **`8`**.
2. **`alloc(3, align=8)`:** Offset `8` is already 8-byte aligned (`(8 + 7) & ~7 = 8`). Occupies **bytes `8..10`**, advancing `next_offset` to **`11`**.
3. **`alloc(16, align=16)`:** Offset `11` is not a multiple of 16. Rounding up yields `(11 + 15) & ~15 = 26 & ~15 = 16`. Bytes **`11..15` (5 bytes)** are skipped as **alignment padding** so the 16-byte block begins cleanly at **offset `16`** (**bytes `16..31`**), advancing `next_offset` to **`32`**.

## 8.2 Arena Allocation: The Bump Allocator

The bump allocator represents the simplest form of memory management. It maintains a single offset (`next_offset`) within a contiguous memory region, known as an **arena**. Allocation is performed by rounding `next_offset` upward to the required alignment, verifying sufficient remaining space (`aligned_offset + requested_bytes <= arena_capacity`), and advancing `next_offset` by the requested size.

The computational complexity of allocation in a bump allocator is O(1), consisting of only a few arithmetic operations with zero per-object metadata overhead. However, this speed is traded for a lack of granularity in deallocation: the allocator cannot free individual objects. Instead, it provides a `reset` operation that rewinds `next_offset = 0` and clears the entire arena at once. This model is highly effective for **arena allocation**, where a group of objects with identical lifetimes (such as request-scoped objects in a web server or nodes in a parse tree) are allocated together and discarded as a single unit.

<figure>
<img src="figures/ch08_bump.svg" alt="Bump allocator sequential byte layout showing 8-byte, 3-byte, 5-byte alignment padding, and 16-byte aligned allocations"/>
</figure>

**Listing 8-1. A bump allocator with explicit alignment rounding (C++20).**

```cpp
{{#include ../code/ch08/bump.cpp}}
```

**Output 8-1. Three allocations demonstrating 5 bytes of alignment padding, followed by an O(1) reset.**

```text
{{#include ../code/out/ch08_bump.out}}
```

**Listing 8-2. The same bump allocator in Rust.**

```rust
{{#include ../code/ch08/bump.rs}}
```

**Output 8-2.**

```text
{{#include ../code/out/ch08_bump_rs.out}}
```

## 8.3 Explicit Management: Free-List Allocation

To support the independent deallocation of individual objects, an allocator must track the size and ownership state of each allocated region. A **free-list allocator** accomplishes this by embedding an **in-band `BlockHeader`** immediately preceding every user payload in memory:

```text
[ BlockHeader (24 bytes): payload_bytes | is_free | next_block ] [ User Payload (payload_bytes) ]
^                                                                ^
header pointer                                                   pointer returned to caller
```

This layout establishes two direct pointer-arithmetic invariants:
- **On `alloc()`:** After finding a suitable free `BlockHeader* current`, the allocator advances past the 24-byte header (`current + 1` in C++ pointer arithmetic, or `current.cast::<u8>().add(HEADER_BYTES)` in Rust) and returns that payload address to the caller.
- **On `free(user_payload_ptr)`:** Because the caller supplies only the payload pointer, the allocator subtracts `sizeof(BlockHeader)` (24 bytes) from `user_payload_ptr` to recover the hidden `BlockHeader`, reads `payload_bytes`, and sets `is_free = true`.

### 8.3.1 First-Fit Search, Splitting, and Coalescing

The allocator's performance and fragmentation profile are governed by three policies:
1. **Allocation Policy (First-Fit):** Starting at `head_block`, `alloc(requested_bytes)` traverses the block list in address order and selects the first block satisfying `is_free && payload_bytes >= requested_bytes`.
2. **Splitting (Suppressing Internal Fragmentation):** When a chosen free block is significantly larger than `requested_bytes`—for example, satisfying `alloc(150)` inside a 200-byte hole—handing out all 200 bytes wastes 50 bytes of **internal fragmentation**. Whenever `leftover_bytes = payload_bytes - requested_bytes >= sizeof(BlockHeader) + MIN_SPLIT_PAYLOAD` (`24 + 16 = 40` bytes), the allocator writes a new `BlockHeader` immediately after the 150-byte payload, carving a reusable free block of `200 - 150 - 24 = 26` bytes and linking it into the list.
3. **Coalescing (Eliminating External Fragmentation):** Freeing adjacent blocks without merging them shatters the arena into small, unusable holes—**external fragmentation**. Upon `free()`, `coalesce_adjacent_free_blocks()` verifies physical contiguity (`neighbor == current + sizeof(BlockHeader) + current->payload_bytes`) and merges consecutive free blocks into a single unified region, reclaiming both the neighbor's payload and its redundant 24-byte header (`150 + 24 + 26 = 200` bytes restored).

<figure>
<img src="figures/ch08_freelist.svg" alt="Free-list allocator unified trace showing initial allocations, block splitting of 200 B into 150 B plus 26 B, and coalescing back to 200 B"/>
</figure>

**Listing 8-3. A first-fit free-list allocator with splitting and coalescing (C++20).**

```cpp
{{#include ../code/ch08/free_list.cpp}}
```

**Output 8-3. The block map after initial allocations, free, split reuse, and full coalescing.**

```text
{{#include ../code/out/ch08_free_list.out}}
```

**Listing 8-4. The same free-list allocator in Rust.**

```rust
{{#include ../code/ch08/free_list.rs}}
```

**Output 8-4.**

```text
{{#include ../code/out/ch08_free_list_rs.out}}
```

## 8.4 Production Allocator Architecture: Boundary Tags, Size Classes, and `mmap`

The educational free-list allocator in Listing 8-3 demonstrates core mechanics, yet exhibits three bottlenecks under multi-threaded production workloads: O(N) linear free-list search, O(N) coalescing traversal, and global lock contention across cores. Production allocators (`jemalloc`, `tcmalloc`, `mimalloc`, and `glibc ptmalloc2`) eliminate these bottlenecks through a three-tier hierarchy.

### 8.4.1 Knuth's Boundary Tags for O(1) Bidirectional Coalescing

In Listing 8-3, coalescing a freed block with its *preceding* physical neighbor required scanning the list from `head_block` in O(N) time because each header links only forward. Donald Knuth's **Boundary Tag** architecture eliminates linear scanning by replicating the 8-byte block descriptor (`payload_bytes | allocated_bit`, exploiting the fact that 16-byte aligned sizes leave the lowest 4 bits zero) as both a **Header** before the payload and a **Footer** immediately after the payload:
- **Forward Coalescing (O(1)):** Add `current->size` to `current` to inspect the next physical block's Header directly.
- **Backward Coalescing (O(1)):** Step backward 8 bytes prior to `current`'s Header to read the previous physical block's **Footer**. When the footer's allocated bit is `0`, subtract its encoded size to jump directly to the predecessor's Header and merge in constant time.

### 8.4.2 Segregated Size Classes and Per-Thread Caches (`tcache`)

Rather than searching a heterogeneous list of arbitrary block sizes under a single global mutex, production allocators partition small allocations into **segregated size classes** (discrete fixed-size bins such as `16 B`, `32 B`, `48 B`, `64 B`, ..., `4 KiB`). Each bin manages a homogeneous slab of identically sized slots, eliminating external fragmentation within a size class and reducing allocation and deallocation to O(1) stack pop and push operations.

To eliminate multi-core lock contention, each thread maintains a private **thread-local cache (`tcache`)** storing pre-allocated slots for every small size class. The vast majority of small `malloc()` and `free()` calls complete in Ring 3 against thread-private cache lines with zero atomic operations and zero mutex acquisitions, contacting central arenas only when a thread-local bin empties or overflows.

### 8.4.3 The `brk` / Arena vs. `mmap` Allocation Threshold (`M_MMAP_THRESHOLD`)

Sub-allocating small objects out of persistent arenas amortizes system-call overhead, whereas placing a multi-megabyte temporary buffer inside a shared arena risks retaining large physical memory spans if a single tiny allocation remains live near the end of the arena. Production allocators enforce a size threshold (**`M_MMAP_THRESHOLD`**, typically **128 KiB**):
- **Allocations `&lt; 128 KiB`:** Served from per-thread `tcache` bins and central size-class arenas backed by persistent `mmap` / `brk` spans.
- **Allocations `&ge; 128 KiB`:** Routed directly to standalone kernel `mmap(MAP_PRIVATE | MAP_ANON)` mappings. Upon `free()`, the allocator invokes `munmap()` immediately, returning the physical frames directly to the operating system kernel.

<figure>
<img src="figures/ch08_allocator_hierarchy.svg" alt="Production allocator three-tier architecture showing per-thread caches, central arenas with Knuth boundary tags, and direct mmap for large allocations"/>
</figure>

<div class="callout keyidea">
<span class="label">Key idea</span>

Memory allocators reconcile kernel page granularity with fine-grained object lifetimes: bump allocators trade individual deallocation for O(1) bulk resets, free-list allocators enforce splitting and coalescing via in-band headers, and production allocators achieve lock-free O(1) scaling via per-thread size-class caches, Knuth boundary tags, and direct `mmap` above 128 KiB.

</div>
