# 7. Virtual Memory

Every process believes it owns a contiguous range of memory starting near
zero. No process does. The belief is manufactured by the hardware's
memory-management unit, consulting a table the kernel maintains, on every
single memory access. This chapter opens that mechanism: pages, page
tables, the fault that fills a page on first touch, the guard page that
turns an access into a signal, and the TLB that keeps the whole thing
fast.

<div class="callout glance">
<span class="label">At a glance</span>

- Memory is addressed in fixed-size pages, mapped to physical frames by
  a per-process page table.
- The kernel fills pages on first touch; a page fault is the normal
  event that starts that process.
- `mprotect` can turn any page into a trap; guard pages are built from
  that.
- The TLB caches translations; its size is visible in memory-access
  latency.

</div>

## 7.1 Pages and frames

Divide both the virtual address space and physical memory into fixed-size
chunks: **pages** on the virtual side, **frames** on the physical side,
4 KiB on the machines in this book. A page is the unit of mapping. The
page table is the per-process list of mappings: virtual page 3 goes to
physical frame 9, page 4 to frame 0, page 5 to nothing at all.

Two properties fall out of the division. First, a process's pages need
not be contiguous in physical memory — Figure 7-1 scatters them on
purpose. The process sees a straight line of addresses; the hardware
translates each access through the table, and physical order is
irrelevant. Second, protection attaches per page: a page is readable,
writable, executable, or absent, and the table records it. Isolation,
from Chapter 1, is this table.

<figure>
<img src="diagrams/ch07_vm_paging.svg" alt="Virtual pages mapping through a page table to scattered physical frames"/>
</figure>

The translation happens inside the MMU, on every access, in hardware —
the kernel is not consulted for ordinary loads and stores. The kernel
enters the picture only when a translation fails: the page is absent, or
the access violates the page's protection. That event is the **page
fault**, and it is the subject of the next two sections.

## 7.2 The page table walk

A 64-bit address space is too large for one flat table: 2^48 addressable
bytes at 4 KiB per page is 2^36 pages, and a table with one entry per
page would not fit in memory. Real processors page the page table:
x86-64 and arm64 split the virtual address into indices that walk a
four-level tree, as Figure 7-2 draws.

<figure>
<img src="diagrams/ch07_pagewalk.svg" alt="A virtual address split into four 9-bit indices and a 12-bit offset, walking four table levels"/>
</figure>

The walk costs up to four memory reads, on every access that is not
cached. The **translation lookaside buffer** — the TLB — is the cache of
recent translations, a few hundred to a few thousand entries kept inside
the MMU. An access whose translation is in the TLB pays nothing extra;
an access whose translation is not there pays the walk. Programs that
touch many pages in a short window exhaust the TLB, and Section 7.4
measures the resulting latency steps.

The kernel's role is to keep the table current. When a page fault
reports an absent page, the kernel decides among four responses: map a
fresh zeroed page (first touch of the heap or stack), map a page of a
file on disk (demand paging), copy a shared page before a write
(copy-on-write, from Chapter 3), or declare the access illegal and send
the process a signal. The fault is not an error; it is the kernel's
scheduled moment to do its part of the illusion.

<div class="callout keyidea">
<span class="label">Key idea</span>

Ordinary accesses are pure hardware: MMU, TLB, table. The kernel runs
only on faults — absence, protection, or a write to a shared page — and
its four responses are map, page in, copy, or kill.

</div>

## 7.3 Pages, observed: the guard page

The next listing makes three facts tangible: the page size, the page
alignment of mappings, and the trap that a protected page produces. It
maps three pages, writes each, then changes the middle page's protection
to none. Writing through the guard page faults; the handler records the
faulting address and the program resumes via `sigsetjmp`.

**Listing 7-1. Page size, page alignment, and a guard page (C++20).**

```cpp
{{#include ../code/ch07/pagesize.cpp}}
```

**Output 7-1. The fault lands exactly on the protected page; the neighbors are untouched.**

```text
{{#include ../code/out/ch07_pagesize.out}}
```

Two details in the listing carry real systems weight. The handler is
registered for both `SIGSEGV` and `SIGBUS`, because the two systems
report protection violations differently: Linux raises `SIGSEGV`, macOS
raises `SIGBUS` — the same fault, two signals, and portable code handles
both. And the faulting address comes from `siginfo_t`, which the kernel
fills with the exact virtual address the instruction touched; production
allocators use exactly this to grow the heap on demand instead of
pre-mapping it.

**Listing 7-2. The same mapping machinery through Rust's libc bindings.**

```rust
{{#include ../code/ch07/pagesize.rs}}
```

**Output 7-2.**

```text
{{#include ../code/out/ch07_pagesize_rs.out}}
```

The Rust listing stops before the fault, because catching a `SIGBUS`
inside a Rust program requires a handler that long-jumps out of
arbitrary code — possible, but not a pattern to encourage. The C++
listing demonstrates the fault; the Rust listing demonstrates the
mapping interface that the fault protects.

Guard pages appear throughout production systems: below every thread's
stack, to convert stack overflow into a clean fault instead of silent
corruption; at the end of arenas, to catch out-of-bounds writes in
allocators and debuggers. `mprotect` plus a signal handler is the entire
mechanism.

<div class="callout experiment">
<span class="label">Experiment</span>

Change `PROT_NONE` to `PROT_READ` in Listing 7-1 and rerun. The write
faults, the handler records the address, and the program continues — a
page that permits reads but traps writes is how debuggers implement
watchpoints and how copy-on-write starts.

</div>

## 7.4 Files and the TLB, measured

Mapping is also how files reach memory. `mmap` attaches a file's pages
to the address space; loads from the mapped region read the file, and on
Linux, stores write it back under the kernel's page-cache machinery. The
next listing counts characters through `read`, which copies the file
into a buffer, and through `mmap`, which makes the file's pages
addressable directly.

**Listing 7-3. The same file through read(2) and through mmap (C++20).**

```cpp
{{#include ../code/ch07/mmap_file.cpp}}
```

**Output 7-3. Identical counts; the mechanisms differ.**

```text
{{#include ../code/out/ch07_mmap_file.out}}
```

`read` copies: disk to kernel page cache, page cache to the program's
buffer. `mmap` copies once: the program's pages *are* the page cache.
For a file read once into memory, the two are equivalent. For a file
touched repeatedly, or shared between processes, mapping wins; for a
stream processed once, `read` wins. The choice is about copies and
lifetime, not correctness — both counted 4,128,768.

The TLB experiment closes the chapter. It walks a growing working set,
one access per page, and prints the latency at each size. When the
working set fits the L1/L2 caches and the TLB, each access costs one or
two nanoseconds. When the TLB is exhausted — around 16 MiB on this
machine, 4,096 pages — every access pays a page walk, and the curve
steps up.

**Listing 7-4. One access per page, sweeping the working set upward (C++20).**

```cpp
{{#include ../code/ch07/tlb.cpp}}
```

**Output 7-4. The steps mark the TLB and cache boundaries; exact values are machine-specific.**

```text
{{#include ../code/out/ch07_tlb.out}}
```

The plateau from 16 MiB upward is the TLB miss cost, flat because every
access pays the same walk. The smaller steps below it are the cache
levels from Chapter 2. The numbers will differ on another machine; the
shape — flat, then a step, then flat — will not.

<div class="callout summary">
<span class="label">Summary</span>

- Pages map to frames through a per-process, hardware-walked page
  table; protection attaches per page.
- The walk is four memory reads; the TLB caches translations and its
  size sets a working-set cliff.
- A page fault is the kernel's cue to map, page in, copy-on-write, or
  kill; first touch of heap and stack is a fault.
- `mprotect` turns pages into traps: guard pages, watchpoints, and the
  signal that follows (SIGSEGV on Linux, SIGBUS on macOS).
- `mmap` attaches files to the address space; the page cache is the
  mapping.
- Chapter 8 descends from pages into the allocator that carves them
  into objects.

</div>
