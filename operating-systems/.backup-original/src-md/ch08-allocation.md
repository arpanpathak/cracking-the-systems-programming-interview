# 8. Memory Allocation

Pages are the kernel's unit; objects are the program's. Between the two
sits the **allocator** — the code behind `malloc`, `new`, and `Box` — which
carves pages into objects of arbitrary size, recycles them when they are
freed, and does both quickly enough that programs treat allocation as
free. This chapter builds two allocators from scratch: the bump
allocator that never recycles, and the free-list allocator that does.

<div class="callout glance">
<span class="label">At a glance</span>

- Allocation is a policy problem over pages: where each object lives,
  what metadata records it, when memory returns to the pool.
- A bump allocator is a single offset; allocation is an add, and reuse
  requires a reset.
- A free list threads freed blocks together; allocation searches,
  splits, and coalesces.

</div>

## 8.1 The allocator's contract

An allocator sits between the program and the kernel. Upward, it serves
`alloc(n)` — n bytes, suitably aligned, belonging to the caller until
`free` — and `free(p)` — the bytes return to the pool. Downward, it
obtains memory from the kernel in large chunks, with `mmap` as Chapter 7
showed, and only occasionally: a 64 KiB chunk serves many small
requests before another kernel call is needed.

Three design decisions separate every allocator ever written. **Where
does an object live?** Bump allocators append; free lists search for a
hole. **What metadata records the layout?** The bump allocator keeps one
offset; the free list embeds a header in front of every block. **When
does memory return to the kernel?** Almost never — allocators keep freed
memory for reuse, because kernel round trips are the most expensive
operation the allocator performs. The rest of the chapter makes each
decision concrete.

<div class="callout keyidea">
<span class="label">Key idea</span>

An allocator is a user-space memory manager with a small contract:
serve requests from large kernel chunks, and recycle freed space so the
kernel is rarely called. The trade is metadata against speed and waste.

</div>

## 8.2 The bump allocator

The simplest allocator keeps one pointer: the offset of the first free
byte in an arena. `alloc(n, align)` rounds the offset up to the
requested alignment, checks the space, advances the offset past `n`, and
returns the old position. `free` does nothing. `reset` sets the offset
to zero and reuses everything. Figure 8-1 is the entire data structure.

<figure>
<img src="diagrams/ch08_bump.svg" alt="A bump allocator arena with three allocations and the offset pointer marking the next free byte"/>
</figure>

**Listing 8-1. The bump allocator (C++20).**

```cpp
{{#include ../code/ch08/bump.cpp}}
```

**Output 8-1. Allocation is an add; reset reuses the arena.**

```text
{{#include ../code/out/ch08_bump.out}}
```

**Listing 8-2. The same allocator in Rust.**

```rust
{{#include ../code/ch08/bump.rs}}
```

**Output 8-2.**

```text
{{#include ../code/out/ch08_bump_rs.out}}
```

The numbers to read: offsets 0, 8, 16 — the three allocations with their
alignment padding, back to back. No headers, no search, no bookkeeping
beyond one integer. The cost of that speed is the inability to free a
single object: memory returns only when the whole arena resets.

That trade is not a defect; it is the allocator's niche. A bump
allocator is the right tool wherever a batch of objects shares one
lifetime — a frame of a video game, a request in a server, a parse
tree. Allocate during the batch, reset when it ends. The pattern has a
name, **arena allocation**, and most high-throughput systems use it
somewhere.

<div class="callout experiment">
<span class="label">Experiment</span>

Make `alloc` fail by requesting 100 KiB from the 64 KiB arena. The
null return is the allocator's honest failure mode. Real allocators
then grow the arena with another `mmap`; add that and observe how the
bump allocator becomes a list of arenas.

</div>

## 8.3 The free list

Freeing individual objects requires memory of what is free. The
free-list allocator keeps that memory in **headers**, one per block,
stored immediately before the block's payload. A header records the
block's size, whether it is free, and a pointer to the next block. Freed
blocks are chained through those pointers; allocation walks the chain
and takes the first block that fits — **first fit**.

Figure 8-2 draws the structure and its two operations. **Splitting**
carves a large free block into the requested part and a smaller free
remainder, so a 200-byte request does not waste a 2 KiB hole.
**Coalescing** merges adjacent free blocks back into one, so freed
neighbors become reusable as a unit.

<figure>
<img src="diagrams/ch08_freelist.svg" alt="A free list of headers and payloads, with a split and a coalesce step"/>
</figure>

**Listing 8-3. First fit with headers, splitting, and coalescing (C++20).**

```cpp
{{#include ../code/ch08/free_list.cpp}}
```

**Output 8-3. The block map evolves exactly as Figure 8-2 predicts.**

```text
{{#include ../code/out/ch08_free_list.out}}
```

**Listing 8-4. The same allocator in Rust, raw pointers and all.**

```rust
{{#include ../code/ch08/free_list.rs}}
```

**Output 8-4.**

```text
{{#include ../code/out/ch08_free_list_rs.out}}
```

Follow the block map against the figure. After three allocations the
arena holds three used blocks and one large free remainder, offsets 0,
124, 348, 672 — each block is its 24-byte header plus payload, so 100
bytes occupy 124. Freeing `b` marks the middle block free without
merging, because its neighbors are used. Allocating 150 bytes finds that
hole first, splits it into a 150-byte used block and a 26-byte free
remainder, and returns `b`'s old address — first fit reuses the most
recently freed hole. Freeing everything coalesces the entire arena back
into one block of 262,120 bytes, which is the arena minus one header.

The implementation choices here are exactly the ones production
allocators make and extend. First fit is one policy; best fit scans the
whole list for the tightest hole, and next fit resumes the search where
it left off. One free list becomes many — segregated by size class, so
a 16-byte request never scans past 16-byte blocks. Threads get their own
arenas, so allocation rarely contends. And the metadata can shrink from
a 24-byte header to a few bits, when the size is implied by the size
class. Every real allocator — glibc's `malloc`, macOS's scalable zone
allocator, jemalloc, tcmalloc — is a combination of these extensions
around the same core.

<div class="callout caution">
<span class="label">Watch out</span>

Two failure modes follow from the header design. A buffer overflow
before a payload corrupts the header, and the allocator then walks
garbage on the next free — the classic crash far from the bug. And
freed memory is not zeroed; reading it returns old data, which is the
information leak that `calloc` and Rust's zeroing avoid. The allocator
is fast because it does not clean up after you.

</div>

<div class="callout summary">
<span class="label">Summary</span>

- Allocators serve objects from kernel pages; the kernel is called
  rarely, the metadata is consulted always.
- Bump allocation is one offset: allocation is an add, reuse is a
  reset, and per-object free does not exist — the arena pattern's
  engine.
- Free lists record each block in a header and chain the freed ones;
  allocation searches (first fit), splits, and coalesces.
- Production allocators extend the same core with size classes, thread
  caches, and compact metadata.
- With allocation in hand, the next chapter returns to the kernel
  boundary itself and measures what a system call costs.

</div>
