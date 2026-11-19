# Chapter 8: Memory Allocation and Management Strategies

While the operating system manages memory in coarse-grained units—typically 4 KiB pages—application-level software requires a mechanism for managing objects of diverse and often much smaller sizes. A memory allocator bridges this granularity gap by requesting large, contiguous regions of memory from the kernel and subdividing them into smaller, appropriately sized blocks for the program.

## 8.1 The Allocator Interface and Efficiency Constraints

A functional allocator provides two primary primitives: `alloc(n)`, which returns an aligned address for $n$ bytes of memory, and `free(p)`, which returns a previously allocated block to the allocator for future reuse. The primary efficiency constraint is the high cost of system calls; therefore, an allocator must minimize its interaction with the kernel by requesting large regions and managing the lifecycle of these regions internally.

Allocators are distinguished by three architectural decisions: the placement strategy for new objects, the metadata utilized for block tracking, and the mechanism for reclaimed block reuse.

## 8.2 Arena Allocation: The Bump Allocator

The bump allocator represents the simplest form of memory management. It maintains a single offset within a contiguous memory region, known as an **arena**. Allocation is performed by rounding the current offset to the required alignment, verifying sufficient remaining space, and advancing the offset by the requested size.

The computational complexity of allocation in a bump allocator is negligible, consisting only of a few arithmetic operations. However, this speed is traded for a lack of granularity in deallocation: the allocator cannot free individual objects. Instead, it provides a `reset` operation that clears the entire arena at once. This model is highly effective for **arena allocation**, where a group of objects with identical lifetimes (such as request-scoped objects in a web server or nodes in a parse tree) are allocated together and discarded as a single unit.

## 8.3 Explicit Management: Free-List Allocation

To support the independent deallocation of individual objects, an allocator must implement a mechanism for tracking free memory. A **free-list allocator** accomplishes this by embedding metadata, or a **header**, immediately preceding each allocated or free block. This header typically stores the block's size, its status (free or used), and a pointer to the next block in the free list.

The allocator's performance and fragmentation characteristics are defined by its search and reclamation policies:
- **Allocation Policy (e.g., First-Fit):** The allocator traverses the free list to find the first block that satisfies the requested size.
- **Splitting:** When a chosen block is significantly larger than the requested size, the allocator divides it into a used portion and a new, smaller free block to minimize internal fragmentation.
- **Coalescing:** To combat external fragmentation, the allocator merges adjacent free blocks into larger, contiguous regions during the `free` operation.

Production-grade allocators, such as `jemalloc` or `tcmalloc`, extend these principles by implementing **size classes** (maintaining separate free lists for different size ranges), **per-thread arenas** (to reduce contention in multi-threaded environments), and highly optimized metadata structures to minimize the memory overhead of the headers themselves.
