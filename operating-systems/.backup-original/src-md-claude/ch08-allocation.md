# 8. Memory Allocation

The kernel gives memory to a process in whole pages of 4 KiB. A program,
however, needs objects of many sizes, most of them far smaller than a
page. A **memory allocator** closes this gap. It is the code behind
`malloc`, `new`, and `Box`, and it obtains pages from the kernel, divides
them into blocks of the requested sizes, and reuses blocks that the
program has freed.

In this chapter, we write two allocators. The first, a bump allocator,
hands out memory with one addition and never frees a single object. The
second, a free-list allocator, can free and reuse individual blocks. For
each one, we print the addresses it returns and compare them with a
figure.

<div class="callout glance">
<span class="label">This chapter covers</span>

- what a program expects from an allocator
- the bump allocator and arena allocation
- alignment
- block headers and the free list
- first fit, splitting, and coalescing
- what production allocators add

</div>

## 8.1 What an allocator provides

An allocator offers two operations to a program. The call `alloc(n)`
returns the address of `n` bytes that belong to the caller until they are
freed. The returned address must also be *aligned*, which means that it is
a multiple of some power of two, such as 8 or 16, as the type of the
object requires. The call `free(p)` returns the block at address `p` to
the allocator, which may then use it for a later request.

The allocator obtains its memory from the kernel with `mmap`, as in
Chapter 7. It requests a large region at a time, for example 64 KiB, and
serves many small requests from that region before it calls the kernel
again. A system call takes much longer than the allocation itself, so an
allocator makes as few of them as possible. For the same reason, an
allocator usually keeps freed memory for reuse and does not return it to
the kernel.

Allocators differ in three decisions. They place a new object in
different ways, either at the end of the used space or in a gap left by a
freed object. They also record different information about the blocks
they have handed out. Finally, they differ in whether, and how, a freed
block becomes available again. The two allocators of this chapter make
opposite choices.

<div class="callout keyidea">
<span class="label">Key idea</span>

An allocator requests large regions from the kernel and divides them into
blocks for the program. It reuses freed blocks so that it rarely needs
another system call.

</div>

## 8.2 The bump allocator

A **bump allocator** manages one region of memory, called an **arena**,
and keeps a single number, the offset of the first unused byte. To
allocate `n` bytes with alignment `align`, it rounds the offset up to a
multiple of `align`, checks that `n` more bytes fit in the arena, and
advances the offset by `n`. The address at the rounded offset is the
result. The allocator has no `free` operation for one object. Its `reset`
operation sets the offset back to zero, which frees every object at once.
Figure 8-1 shows an arena after three allocations.

<figure>
<img src="figures/ch08_bump.svg" alt="A bump allocator arena with three allocations and the offset pointer marking the next free byte"/>
</figure>

**Listing 8-1. A bump allocator (C++20).**

```cpp
{{#include ../code/ch08/bump.cpp}}
```

**Output 8-1. Three allocations and a reset.**

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

All three allocations start where Figure 8-1 shows them, at offsets 0, 8,
and 16. Allocation one occupies bytes 0 to 7. Allocation two needs 3 bytes
and occupies bytes 8 to 10, so the offset becomes 11. Allocation three
requires an alignment of 16, so our allocator rounds 11 up to 16 and
leaves bytes 11 to 15 unused. After `reset`, a new allocation returns the
very first address again.

A bump allocator stores no information about individual objects and never
searches, so an allocation takes only a few instructions. In exchange, the
program cannot free one object and keep the others. This restriction is
acceptable when a group of objects is created together and discarded
together. Examples are the objects of one frame in a video game, the
objects of one request in a server, and the nodes of a parse tree. The
program allocates them during the frame or request and resets the arena at
the end. This technique is called **arena allocation**.

<div class="callout experiment">
<span class="label">Experiment</span>

Request 100 KiB from the 64 KiB arena. `alloc` returns a null pointer,
because the request does not fit. Then extend the allocator so that it
maps a second arena with `mmap` when the first one is full. The allocator
then manages a list of arenas.

</div>

## 8.3 The free list

To free individual objects, an allocator must record which parts of its
arena are in use. A **free-list allocator** stores this record inside the
arena. In front of each block, it places a **header**, a small structure
that holds the size of the block, a flag that tells whether the block is
free, and a pointer to the next block. In our implementation, a header
occupies 24 bytes. The bytes after the header, which the program uses, are
called the **payload**.

To allocate, the allocator follows the pointers from header to header and
takes the first free block that is large enough. This policy is called
**first fit**. Two further operations, shown in Figure 8-2, keep the arena
usable over time.

- **Splitting.** When the chosen block is larger than the request, the
  allocator divides it into a block of the requested size and a smaller
  free block.
- **Coalescing.** When a block is freed and a neighboring block is also
  free, the allocator merges them into one larger free block.

<figure>
<img src="figures/ch08_freelist.svg" alt="A free list of headers and payloads, with a split and a coalesce step"/>
</figure>

**Listing 8-3. A first-fit allocator with splitting and coalescing (C++20).**

```cpp
{{#include ../code/ch08/free_list.cpp}}
```

**Output 8-3. The block map after each step.**

```text
{{#include ../code/out/ch08_free_list.out}}
```

**Listing 8-4. The same allocator in Rust, using raw pointers.**

```rust
{{#include ../code/ch08/free_list.rs}}
```

**Output 8-4.**

```text
{{#include ../code/out/ch08_free_list_rs.out}}
```

Let us follow the block map in Output 8-3. The program first allocates
100, 200, and 300 bytes, which we call blocks `a`, `b`, and `c`. Each
block occupies its payload plus a 24-byte header, so `a` takes 124 bytes,
and `b` begins at offset 124. Block `c` begins at 124 + 224 = 348, and the
free remainder of the arena begins at 348 + 324 = 672.

Next, the program frees `b`. Its header is marked free, but nothing is
merged, because both neighbors are in use.

The program then allocates 150 bytes. The first free block that is large
enough is the former block `b`, with a payload of 200 bytes. The allocator
splits it into a used block of 150 bytes and a new free block. The new
block needs a header of 24 bytes, which leaves 200 - 150 - 24 = 26 bytes
of payload. The request therefore receives the address that `b` had.

Finally, the program frees all blocks. The allocator merges them into a
single free block of 262,120 bytes, which is the arena size of 262,144
bytes minus one header.

Production allocators, such as `malloc` in glibc, the default allocator of
macOS, jemalloc, and tcmalloc, start from the same ideas and extend them.

- Some use other search policies. *Best fit* searches the whole list for
  the smallest block that is large enough. *Next fit* continues each
  search where the previous one ended.
- Most keep a separate free list for each range of sizes, called a *size
  class*, so that a request for 16 bytes examines only blocks of about 16
  bytes.
- Most give each thread an arena of its own, so that threads seldom wait
  for one another.
- Some store less than a full header for each block, because the size
  class already determines the block size.

<div class="callout caution">
<span class="label">Watch out</span>

Headers that lie next to payloads make two kinds of bugs possible. If a
program writes past the end of a block, it overwrites the header of the
next block. The allocator then reads invalid data during a later `alloc`
or `free`, and the program crashes far from the faulty write. In addition,
an allocator does not clear freed memory, so a newly allocated block can
contain data from an earlier use. `calloc` returns zeroed memory for this
reason.

</div>

<div class="callout summary">
<span class="label">Summary</span>

- An allocator obtains large regions from the kernel and divides them into
  blocks. It reuses freed blocks to avoid system calls.
- A bump allocator keeps one offset. Allocation is an addition, and only a
  reset frees memory. It suits objects that are discarded together.
- A free-list allocator places a header before each block. It allocates by
  first fit, splits blocks that are too large, and coalesces neighboring
  free blocks.
- Production allocators add size classes, per-thread arenas, and smaller
  metadata.

In Chapter 9, we return to the boundary between a program and the kernel
and measure the cost of a system call.

</div>
