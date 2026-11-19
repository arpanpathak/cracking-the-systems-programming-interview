# 7. Virtual Memory

In Chapter 3, we saw that every process has its own address space, laid
out as one continuous range of addresses. Physical memory is not arranged
in that way. The addresses that a program uses are **virtual addresses**,
and the hardware translates each of them into a location in physical
memory by consulting a table that the kernel maintains. This scheme is
called **virtual memory**.

In this chapter, we describe pages and page tables, and we follow the
steps by which the hardware translates an address. We then explain page
faults, protect a page so that writing to it raises a signal, read a file
through `mmap`, and measure the cost of translation as a program uses more
and more pages.

<div class="callout glance">
<span class="label">This chapter covers</span>

- pages, frames, and the page table
- the four-level page table walk on x86-64 and arm64
- the translation lookaside buffer (TLB)
- page faults and the four ways the kernel responds to them
- `mprotect` and guard pages
- reading a file with `read` and with `mmap`
- access latency as a function of working-set size

</div>

## 7.1 Pages and frames

Virtual memory divides addresses into blocks of a fixed size. A block of
the virtual address space is a **page**, and a block of physical memory is
a **frame**. Pages and frames have the same size, which is 4 KiB (4,096
bytes) on the machines used in this book. Each process has a **page
table**, which records the frame that holds each of its pages. In Figure
7-1, for example, page 0 is stored in frame 3, page 1 in frame 7, and page
5 has no frame.

This division has two consequences. First, the pages of a process can lie
anywhere in physical memory, in any order, as Figure 7-1 shows. A program
uses consecutive virtual addresses, and the hardware finds the frame for
each one. Second, each entry of the page table carries permission bits,
which state whether the page may be read, written, or executed. The
isolation between processes that we described in Chapter 1 is implemented
with these tables. A process can access only the frames that its own page
table maps.

<figure>
<img src="figures/ch07_vm_paging.svg" alt="Virtual pages mapping through a page table to scattered physical frames"/>
</figure>

The memory management unit (MMU) of Chapter 2 performs the translation in
hardware, for every load and every store. The kernel takes no part in an
ordinary access. It becomes involved only when a translation fails, either
because the page has no frame or because the access violates the
permission bits of the page. This event is a **page fault**, and we study
it in Section 7.2.

## 7.2 The page table walk

On x86-64 and arm64, a virtual address has 48 meaningful bits, which cover
2^48 bytes. With 4 KiB pages, that is 2^48 / 2^12 = 2^36 pages. A single
table with one entry for each of these pages would be far too large, and
most of its entries would be unused, because a typical process uses only a
small part of its address space. Both processors therefore organize the
page table as a tree with four levels. Figure 7-2 shows how an address
selects a path through that tree.

<figure>
<img src="figures/ch07_pagewalk.svg" alt="A virtual address split into four 9-bit indices and a 12-bit offset, walking four table levels"/>
</figure>

The lowest 12 bits of an address are the *offset* of a byte within its
page, since 2^12 = 4,096. The next 36 bits are divided into four indices
of 9 bits each. A register (CR3 on x86-64) holds the address of the
top-level table, L4. The first index selects one of the 512 entries of L4,
and that entry holds the address of an L3 table. The second index selects
an entry of L3, and so on. The entry selected in the L1 table holds the
frame number. Following this path is called a *page table walk*, and it
requires four memory reads.

Four additional reads for every memory access would be very slow. The MMU
therefore keeps a cache of recent translations, the **translation
lookaside buffer** (TLB), which holds from a few hundred to a few thousand
entries. If the translation of a page is in the TLB, the MMU uses it
directly. If it is not, the MMU performs the walk and stores the result in
the TLB. A program that uses more pages than the TLB has entries pays for
many walks. We measure this cost in Section 7.4.

Page tables are built and kept up to date by the kernel. When a page
fault occurs, it examines the faulting address and responds in one of four
ways.

- It allocates a frame filled with zeros and maps it. The kernel does this
  when a program accesses a new page of its heap or stack for the first
  time.
- It reads a page of a file from disk and maps it. This response is called
  *demand paging*.
- It copies a shared page and maps the copy. This response is the
  copy-on-write of Chapter 3.
- It decides that the access is invalid and sends a signal to the process.
  By default, the signal terminates the process.

A page fault is therefore not always an error. In three of these four
cases, it is how a process normally receives memory, at the moment it
first uses that memory.

<div class="callout keyidea">
<span class="label">Key idea</span>

An ordinary memory access is handled by hardware alone, using the TLB and
the page table. The kernel runs only when a page fault occurs. It then
maps a new page, loads a page from a file, copies a shared page, or sends
a signal.

</div>

## 7.3 Observing pages: the guard page

Listing 7-1 demonstrates page size, alignment of mapped memory, and a
fault caused by a protected page. Our program maps three pages with `mmap`
and writes one byte to each. It then calls `mprotect` to remove all
permissions from the middle page and writes to that page again. This
second write causes a page fault, and the kernel sends our process a
signal. A signal handler records the faulting address, and execution
continues after the faulting write by means of `siglongjmp`.

**Listing 7-1. Page size, page alignment, and a guard page (C++20).**

```cpp
{{#include ../code/ch07/pagesize.cpp}}
```

**Output 7-1. The fault occurs on the protected page.**

```text
{{#include ../code/out/ch07_pagesize.out}}
```

Our mapped region starts at `0x1051dc000`. The faulting address,
`0x1051dd000`, is 4,096 bytes higher and is therefore the first byte of
the middle page. Bytes `a` and `c`, which were written to pages one and
three, are unchanged.

Listing 7-1 installs its handler for two signals, `SIGSEGV` and `SIGBUS`.
For this kind of protection violation, Linux sends `SIGSEGV` and macOS
sends `SIGBUS`, so a portable program must handle both. The handler reads
the faulting address from the `siginfo_t` structure that the kernel passes
to it.

**Listing 7-2. Mapping and protecting pages in Rust, using the libc crate.**

```rust
{{#include ../code/ch07/pagesize.rs}}
```

**Output 7-2.**

```text
{{#include ../code/out/ch07_pagesize_rs.out}}
```

Our Rust program maps three pages and protects the middle one, but it
does not write to a protected page. Recovering from that fault would
require a jump out of a signal handler, across Rust stack frames, and Rust
does not define how such a jump behaves.

A page with no permissions that is placed next to a region of memory is
called a **guard page**. The kernel puts a guard page below the stack of
every thread. When a stack overflows, the program then receives a signal
at once, and it does not silently overwrite other memory. Debugging
allocators place guard pages after their blocks to detect writes past the
end of a block.

<div class="callout experiment">
<span class="label">Experiment</span>

Change `PROT_NONE` to `PROT_READ` in Listing 7-1 and run it again. The
write still faults, but a read of the same page now succeeds. Debuggers
use read-only pages to implement watchpoints, and the kernel uses them to
implement copy-on-write.

</div>

## 7.4 Mapped files and the cost of translation

A program can also use `mmap` to map a file into its address space. A load
from the mapped region then returns bytes of the file, and no call to
`read` is needed. Listing 7-3 counts the occurrences of the letter `a` in
a 4 MiB file in two ways. It first copies the file into a buffer with
`read`, and it then maps the file with `mmap`.

**Listing 7-3. Reading one file with read(2) and with mmap (C++20).**

```cpp
{{#include ../code/ch07/mmap_file.cpp}}
```

**Output 7-3. Both methods count 4,128,768 characters.**

```text
{{#include ../code/out/ch07_mmap_file.out}}
```

These two methods differ in how often data is copied. File data that the
kernel has read from disk stays in memory, in a structure called the
**page cache**. A call to `read` copies bytes from that cache into a
buffer of the program. With `mmap`, the kernel maps page cache frames
directly into a process's address space, so no second copy is made. For a
file that a program reads once from start to end, both methods perform
about equally. Mapping is the better choice when a program accesses parts
of a file repeatedly or when several processes share one file.

Our last experiment measures the cost of address translation. Listing 7-4
allocates a region of memory and reads one byte from each of its pages, in
a loop, 4,000,000 times in total. It repeats this measurement for regions
from 1 page to 65,536 pages and prints the average time of one access.

**Listing 7-4. One access per page, for a growing number of pages (C++20).**

```cpp
{{#include ../code/ch07/tlb.cpp}}
```

**Output 7-4. One run on the verification machine.**

```text
{{#include ../code/out/ch07_tlb.out}}
```

For up to 64 pages, one access takes about 1.7 ns. In that range, the TLB
holds a translation for every page, and all bytes that our program reads
fit in the L1 cache. Access time then rises with the page count, to 3.7 ns
at 1,024 pages, 6.8 ns at 4,096 pages, and 13.8 ns at 65,536 pages. With
thousands of pages, the TLB no longer holds every translation, so many
accesses need a page table walk. In addition, neither those bytes nor the
page table entries themselves fit in the faster caches any longer. Other
machines produce other numbers, but on each of them access time grows with
the page count in a similar way.

<div class="callout summary">
<span class="label">Summary</span>

- Virtual memory divides addresses into pages. A page table for each
  process maps pages to physical frames and stores the permissions of each
  page.
- On x86-64 and arm64, the page table is a four-level tree, and one walk
  takes four memory reads. The TLB caches recent translations.
- On a page fault, the kernel maps a zeroed page, loads a page from a
  file, copies a shared page, or sends a signal.
- `mprotect` changes the permissions of a page. A write to a protected
  page raises `SIGSEGV` on Linux and `SIGBUS` on macOS.
- `mmap` maps the page cache of a file into a process, which avoids the
  copy that `read` makes.
- The average access time grows as a program uses more pages, because
  fewer translations are found in the TLB.

In Chapter 8, we will divide pages into smaller blocks with a memory
allocator.

</div>
