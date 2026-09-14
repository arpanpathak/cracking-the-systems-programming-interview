# 2. Memory: Paging, Overcommit, and the OOM Killer {#memory-paging-oom}

A container's memory limit is enforced by the same page-table and page-fault
machinery that backs every process on the machine. A cgroup is not a second
memory system layered on top of the kernel's; it is an accounting boundary
drawn across the same pages. This chapter works through that machinery, ending
at the two questions it actually answers in production: why `RSS` can look
flat while a container is OOM-killed, and why `malloc` can succeed for memory
the machine does not have.

## Virtual memory

Every process has its own virtual address space described by `mm_struct` and
page tables. The CPU translates virtual addresses to physical addresses through
the page tables, with a TLB caching recent translations. This gives isolation,
so one process cannot read another process's memory; lazy allocation; shared
file pages; copy-on-write; and overcommit.

Typical 64-bit user address space, not to scale:

```text
0x0000_0000_0000_0000
├── text (executable code)
├── data / BSS
├── heap (grows up via brk)
├── mmap region (shared libs, mmap files, threads, arenas)
├── stack (grows down)
└── vsyscall / vvar / ... (kernel-exported pages)
```

On a 64-bit machine the hardware uses 48 bits of an address, with the upper
bits as sign extension, split into five fields: four 9-bit table indices and a
12-bit page offset. The 12-bit offset is why a page is 4 KiB.

```text
47      39 38      30 29      21 20      12 11        0
+-----------+-----------+-----------+-----------+-----------+
| PGD   9b  | PUD   9b  | PMD   9b  | PTE   9b  | offset 12b|
+-----------+-----------+-----------+-----------+-----------+
```

Translation walks the levels in order: the PGD entry names a PUD table, the
PUD entry a PMD table, the PMD entry a PTE table, and the PTE holds the
physical frame number. The offset is copied through untranslated. That is up
to four dependent memory reads per translation. The TLB exists to avoid paying
that cost on every access, and a TLB miss is the expensive event measured by
tools like `perf stat -e dTLB-load-misses`.

Two numbers make the structure concrete. Nine bits per level means one PTE
table describes 512 pages, and 512 × 4 KiB is 2 MiB of address space per
table. Each table is itself exactly one page, because 512 entries × 8 bytes is
4096 bytes. Empty branches are never allocated, so a process that touches a
few megabytes never materializes the tables for the rest, and that omission is
what makes a 128 TiB address space affordable at all. Isolation, lazy
allocation, shared libraries, and copy-on-write are all answers to one
question: which physical frame does this entry point at, and who else's entry
points at the same frame?

## Pages, page faults, and RSS

Memory is managed in pages, usually 4 KiB, with 2 MiB and 1 GiB huge pages
also available. When a program calls `malloc(1 GiB)`, the kernel usually does
not allocate physical memory immediately; it records virtual address space.
The first write to a page triggers a **page fault**, and the kernel allocates
a physical page and maps it.

A **minor fault** means the page is already in memory, for example a file page
in the page cache or a COW page, and only needs a new PTE. A **major fault**
means the kernel must read the page from disk or network. A **protection
fault** can come from COW, a read-only mapping, or a bug, and a **segmentation
fault** is access to a virtual address with no valid mapping at all.

Three measurements matter in practice: **VSZ**, the entire mapped virtual
address space including libraries and mappings that are not resident; **RSS**,
the physical pages currently mapped to the process; and **PSS**, RSS divided
among processes sharing a page, read from `/proc/<pid>/smaps_rollup`. Page
cache, file-backed pages the kernel has cached, is why `free` normally shows
most memory "used": that memory is reclaimed under pressure, so it is not
memory a workload is competing for.

```bash
cat /proc/self/status
cat /proc/self/smaps_rollup
grep -E 'VmSize|VmRSS|RssAnon|RssFile|ShmemPmdMapped' /proc/self/status
free -h
vmstat 1 5
```

The kernel keeps per-process counters, so the fault behavior above can be
measured rather than asserted. `getrusage(RUSAGE_SELF)` returns `ru_minflt`
and `ru_majflt`; `ps -o min_flt,maj_flt` and `/proc/<pid>/stat` fields 10 and
12 read the same numbers. The program below maps 64 MiB of anonymous memory
and writes to all of it twice.

```c
/* faults.c: the kernel counts the page faults a process takes. */
#define _GNU_SOURCE
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/resource.h>

static void delta(const char *label, struct rusage *before, struct rusage *after)
{
    printf("%-13s minor +%ld major +%ld\n", label,
           after->ru_minflt - before->ru_minflt,
           after->ru_majflt - before->ru_majflt);
}

int main(void)
{
    const size_t len = 64u * 1024 * 1024;   /* 64 MiB */
    struct rusage before, after;
    char *p;

    p = mmap(NULL, len, PROT_READ | PROT_WRITE,
             MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (p == MAP_FAILED) {
        perror("mmap");
        return 1;
    }

    getrusage(RUSAGE_SELF, &before);
    memset(p, 1, len);                      /* first touch of every page */
    getrusage(RUSAGE_SELF, &after);
    delta("first touch", &before, &after);

    getrusage(RUSAGE_SELF, &before);
    memset(p, 2, len);                      /* already resident */
    getrusage(RUSAGE_SELF, &after);
    delta("second write", &before, &after);

    printf("mapped %zu bytes = %zu pages of %d\n", len, len / 4096, 4096);
    munmap(p, len);
    return 0;
}
```

```text
$ gcc -O2 -o faults faults.c && ./faults
first touch   minor +16384 major +0
second write  minor +0 major +0
mapped 67108864 bytes = 16384 pages of 4096
```

The arithmetic checks out exactly: 64 MiB ÷ 4 KiB is 16384 pages, and the
first touch took exactly one minor fault per page. The second pass over the
same range took none, because the pages were already resident. `major` faults
are zero for anonymous memory, since nothing had to be read from a backing
store. The same reasoning applies to an `mmap` of a *file*: the first touch is
a minor fault if the page is already in the page cache and a major fault if
it is not, which is what makes `majflt` a useful production signal —
sustained major faults mean the working set no longer fits in RAM.

```rust
//! faults.rs
use libc::{getrusage, mmap, rusage, MAP_ANONYMOUS, MAP_FAILED, MAP_PRIVATE, PROT_READ, PROT_WRITE, RUSAGE_SELF};

const LEN: usize = 64 * 1024 * 1024; // 64 MiB

fn usage() -> rusage {
    let mut u: rusage = unsafe { std::mem::zeroed() };
    // SAFETY: RUSAGE_SELF writes a rusage into a valid stack slot.
    unsafe { getrusage(RUSAGE_SELF, &mut u) };
    u
}

fn main() {
    // SAFETY: an anonymous private mapping; the result is checked below.
    let base = unsafe {
        mmap(
            std::ptr::null_mut(),
            LEN,
            PROT_READ | PROT_WRITE,
            MAP_PRIVATE | MAP_ANONYMOUS,
            -1,
            0,
        )
    };
    if base == MAP_FAILED {
        eprintln!("mmap failed");
        std::process::exit(1);
    }

    let before = usage();
    // SAFETY: the mapping is LEN bytes and writable.
    unsafe { std::ptr::write_bytes(base as *mut u8, 1, LEN) };
    let after = usage();
    println!(
        "first touch : minor +{} major +{}",
        after.ru_minflt - before.ru_minflt,
        after.ru_majflt - before.ru_majflt
    );

    let before = usage();
    // SAFETY: same mapping, already resident.
    unsafe { std::ptr::write_bytes(base as *mut u8, 2, LEN) };
    let after = usage();
    println!(
        "second write: minor +{} major +{}",
        after.ru_minflt - before.ru_minflt,
        after.ru_majflt - before.ru_majflt
    );
    println!("bytes: {} = {} pages", LEN, LEN / 4096);
}
```

```text
$ cargo run --release --bin faults
first touch : minor +16384 major +0
second write: minor +0 major +0
bytes: 67108864 = 16384 pages
```

That program never asks the allocator for memory; `mmap` is the syscall
underneath `malloc`, and going straight to it removes the allocator from the
measurement.

## `malloc`, `brk`, and `mmap`

Glibc `malloc` manages heap **arenas**. Small allocations come from arenas
that grow with `brk`/`mmap`; large allocations use `mmap` directly and are
unmapped on `free`. Its threshold, `M_MMAP_THRESHOLD`, is 128 KiB by default: a
larger request is served by `mmap` and released on `free`, a smaller one comes
from the heap that `brk` extends.

```c
/* heap.c: glibc grows the brk area for small blocks and calls mmap for large ones. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

static int mappings(void)
{
    FILE *f = fopen("/proc/self/maps", "r");
    int lines = 0;
    char buf[512];

    if (f == NULL)
        return -1;
    while (fgets(buf, sizeof buf, f) != NULL)
        lines++;
    fclose(f);
    return lines;
}

int main(void)
{
    void *small;
    void *large;

    printf("start    brk=%p mappings=%d\n", sbrk(0), mappings());

    small = malloc(64 * 1024);
    printf("64 KiB   %p brk=%p mappings=%d\n", small, sbrk(0), mappings());

    large = malloc(8 * 1024 * 1024);
    printf("8 MiB    %p brk=%p mappings=%d\n", large, sbrk(0), mappings());

    free(large);
    free(small);
    printf("freed    brk=%p mappings=%d\n", sbrk(0), mappings());
    return 0;
}
```

```text
$ gcc -O2 -o heap heap.c && ./heap
start    brk=0xaaaaef254000 mappings=16
64 KiB   0xaaaaef2558a0 brk=0xaaaaef275000 mappings=16
8 MiB    0xffff8143f010 brk=0xaaaaef275000 mappings=17
freed    brk=0xaaaaef275000 mappings=16
```

Three things are visible in that output. The 64 KiB block came from the heap:
`brk` moved, and the mapping count did not change. The 8 MiB block did the
opposite: `brk` is identical before and after, the mapping count went from 16
to 17, and the address sits in the high part of the address space, where
`mmap` places mappings. After `free`, the large mapping is gone but `brk` has
not moved, because glibc keeps the heap it has already grown, in order to
reuse it.

That last point has a real production consequence. A process that repeatedly
allocates and frees large buffers holds a stable mapping count rather than
returning memory between calls, and a process that allocates many small
objects keeps both the pages and the `brk` address for its lifetime. Neither
is a leak in the "lost pointer" sense, and neither shows up as growing `RSS`
unless the memory was actually touched. So "`RSS` is flat but the container
was OOM-killed" is normally a cgroup limit set below the peak *touched* set,
not a leak.

## Overcommit and the OOM killer

Linux can let `malloc` succeed even when there is not enough physical RAM,
under an overcommit mode of `0` (heuristic), `1` (always overcommit), or `2`
(never overcommit). When memory runs out, the kernel invokes the OOM killer,
which scores processes and kills one to free memory.

In containers, memory limits are enforced by **cgroup v2**. When a cgroup
exceeds `memory.max`, the kernel reclaims pages inside that cgroup, then
invokes the cgroup OOM killer for that cgroup; a container does not
necessarily take down the whole node. `dmesg` shows messages like
`Memory cgroup out of memory: Killed process ...`.

Overcommit is where the kernel's model and the textbook model diverge. A
textbook allocator refuses when the resource is exhausted; Linux hands out
address space it may not be able to back, for two reasons: a `fork`-heavy
workload would fail constantly if every child had to be fully fundable, and
most programs reserve far more than they touch. The mode is selected by
`vm.overcommit_memory`, and the default is the heuristic.

The consequence is that a non-`NULL` return from `malloc` is not a promise.
The failure arrives later, as an OOM kill, and the process chosen to die is
selected by `oom_score` rather than by whoever requested the memory.
Production systems set a `memory.max` on the cgroup for exactly this reason:
it confines the kill to the container that overspent instead of letting the
heuristic choose among every process on the node.

Linus Torvalds, on why the deployed behavior wins even when the theory is
cleaner (*The Linux Edge*, in *Open Sources*, O'Reilly, 1999):

> Theory and practice sometimes clash. Theory loses. Every single time.

## Huge pages and NUMA

Huge pages reduce TLB misses and page-table overhead for large memory
regions, useful for some HPC and database workloads; Kubernetes supports
`hugepages-2Mi`/`hugepages-1Gi` as schedulable resources. NUMA means
memory attached to one CPU socket is faster for CPUs on that socket; GPU
servers are strongly NUMA, since PCIe/NVLink topology and GPU memory locality
affect data transfer, and `numactl --hardware` shows nodes and distances.

Three GPU-specific points follow from the same model. CUDA pinned, page-locked
host memory allows DMA without bounce buffers and is deliberately
non-swappable. GPUs have their own HBM memory, so `nvidia-smi` shows used and
free GPU memory that is not host RSS. And GPUDirect Storage can DMA from
storage to GPU memory, bypassing host memory entirely.

## References

- Drepper, "What Every Programmer Should Know About Memory" (2007).
- Bryant & O'Hallaron, *Computer Systems: A Programmer's Perspective*, Chapters
  8 and 9.
- Arpaci-Dusseau, *Operating Systems: Three Easy Pieces*, the virtual memory
  chapters.
- The `cgroups(7)` man page, and the kernel documentation for the cgroup v2
  memory controller.
