# 50. Paging and Round-Robin Scheduling {#paging-and-scheduling}

*Source files: [`src/bin/os_paging.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/os_paging.rs) and [`src/bin/os_scheduler.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/os_scheduler.rs). Run them with `cargo run --bin os_paging` and `cargo run --bin os_scheduler`.*

## Problem Statement

1. With 4,096-byte pages, compute the page number and offset of an address, the number
   of pages needed to hold a given number of bytes, and the kind of page fault an access
   causes given whether the address is mapped, whether the page is in memory, and
   whether it is writable.
2. Given a list of runnable tasks and a 5 ms quantum, list the task that runs in each
   time slice under round-robin scheduling, and state the longest a task can wait for
   its next slice.

## Designing a Solution

**Addresses.** A page size of 4,096 is `2^12`, so the low 12 bits of an address are the
offset within its page and the remaining bits are the page number. Dividing by the page
size gives the page number and the remainder gives the offset; with a power of two the
compiler emits a shift and a mask.

```text
address 0x1234  =  0001 0010 0011 0100 in binary
                   |  page  | offset  |
page   = 0x1234 >> 12      = 0x1
offset = 0x1234 & 0xfff    = 0x234
```

**Page counts.** A buffer of `b` bytes needs `ceil(b / 4096)` pages. `u64::div_ceil`
computes that without the `(b + 4095) / 4096` idiom, which overflows for `b` near
`u64::MAX`.

**Fault classes.** When the processor cannot complete an access through the page
tables, it raises a fault and the kernel decides what happened. The program's model has
four outcomes:

- **invalid**: the address is not part of any mapping; the process receives `SIGSEGV`;
- **major**: the mapping is valid but the page must be read from disk or swap;
- **protection**: the page is present, but the access is not permitted, such as a write
  to a read-only page;
- **minor**: the page is present and the access is permitted, and the kernel only has to
  update the page tables.

**Round robin.** Tasks form a circular queue. Each runs for at most one quantum and then
moves to the back. With `n` tasks and quantum `q`, a task that has just run waits at
most `(n - 1) × q` before it runs again, and slice `t` belongs to task `t mod n`.

## Implementation

```rust
//! Virtual memory arithmetic: address to page and offset, page counts, and how a
//! page fault is classified.
//!
//! Run with: cargo run --bin os_paging

const PAGE_SIZE: u64 = 4096;

fn split_page(address: u64) -> (u64, u64) {
    (address / PAGE_SIZE, address % PAGE_SIZE)
}

fn pages_needed(bytes: u64) -> u64 {
    bytes.div_ceil(PAGE_SIZE)
}

#[derive(Debug, PartialEq, Eq)]
enum Fault {
    /// The page is resident; a copy-on-write write or permission upgrade.
    Minor,
    /// The mapping is valid but the page must be read from backing store.
    Major,
    /// The mapping is valid and resident, but the access permission is wrong.
    Protection,
    /// No valid mapping at this address.
    Invalid,
}

fn classify_fault(mapped: bool, present: bool, writable: bool) -> Fault {
    match (mapped, present, writable) {
        (false, _, _) => Fault::Invalid,
        (true, false, _) => Fault::Major,
        (true, true, false) => Fault::Protection,
        (true, true, true) => Fault::Minor,
    }
}

fn main() {
    println!("page size: {PAGE_SIZE} bytes");

    println!("\naddress -> page, offset");
    for address in [0u64, 0x1234, 0x1fff, 0x2000] {
        let (page, offset) = split_page(address);
        println!("  0x{address:04x} -> page {page:>2}, offset 0x{offset:03x}");
    }

    println!("\npages needed");
    for bytes in [0u64, 1, PAGE_SIZE, PAGE_SIZE + 1] {
        println!("  {bytes:>5} bytes -> {}", pages_needed(bytes));
    }

    println!("\nfault classification");
    println!(
        "  unmapped           -> {:?}",
        classify_fault(false, false, false)
    );
    println!(
        "  mapped, not in ram -> {:?}",
        classify_fault(true, false, true)
    );
    println!(
        "  resident, read-only-> {:?}",
        classify_fault(true, true, false)
    );
    println!(
        "  resident, writable -> {:?}",
        classify_fault(true, true, true)
    );

    assert_eq!(split_page(0x1234), (1, 0x234));
    assert_eq!(pages_needed(0), 0);
    assert_eq!(pages_needed(PAGE_SIZE + 1), 2);
    assert_eq!(classify_fault(true, false, true), Fault::Major);
    assert_eq!(classify_fault(true, true, false), Fault::Protection);
    assert_eq!(classify_fault(false, true, true), Fault::Invalid);

    println!("\nall checks passed");
}
```

`classify_fault` matches on a tuple `(mapped, present, writable)`. The patterns are
ordered from the most general failure to the most specific: `(false, _, _)` covers every
unmapped access in one arm, and `(true, false, _)` every non-resident page. The four arms
are exhaustive over the eight combinations of three booleans, and the compiler verifies
that no combination is missing.

`Fault` derives `PartialEq` and `Eq` so that `assert_eq!` can compare variants, and
`Debug` so that `{:?}` can print them.

```rust
//! Round-robin scheduling: each runnable task gets one fixed time slice in turn,
//! so no task starves. This is the simplest fair policy a scheduler can use.
//!
//! Run with: cargo run --bin os_scheduler

const QUANTUM_MS: u64 = 5;

/// The task chosen on each of `ticks` time slices.
fn schedule<'a>(tasks: &[&'a str], ticks: usize) -> Vec<&'a str> {
    if tasks.is_empty() {
        return Vec::new();
    }
    (0..ticks).map(|tick| tasks[tick % tasks.len()]).collect()
}

fn main() {
    let tasks = ["encoder", "decoder", "gc"];

    println!("{} runnable tasks, {QUANTUM_MS} ms quantum", tasks.len());
    for (tick, task) in schedule(&tasks, 7).iter().enumerate() {
        let start = tick as u64 * QUANTUM_MS;
        println!(
            "  slice {tick}: {start:>2}-{:>2} ms  {task}",
            start + QUANTUM_MS
        );
    }

    let order = schedule(&tasks, 7);
    assert_eq!(
        order,
        [
            "encoder", "decoder", "gc", "encoder", "decoder", "gc", "encoder"
        ]
    );
    assert!(schedule(&[], 3).is_empty());

    // A long task is preempted, not run to completion, which is what bounds its
    // worst-case latency to one quantum times the number of tasks.
    println!(
        "\nworst-case wait for one slice: {} ms",
        QUANTUM_MS * tasks.len() as u64
    );
    println!("all checks passed");
}
```

`schedule` maps each tick to `tasks[tick % tasks.len()]` and collects the results. The
early return for an empty task list prevents a division by zero in `%`.

The signature `fn schedule<'a>(tasks: &[&'a str], ticks: usize) -> Vec<&'a str>` ties the
returned string slices to the strings themselves, not to the slice that holds them. A
caller can therefore drop or rebuild the task list while keeping the schedule, as long
as the strings outlive it. Here they are string literals, which live for the whole
program.

## Intuition

The paging program prints:

```text
page size: 4096 bytes

address -> page, offset
  0x0000 -> page  0, offset 0x000
  0x1234 -> page  1, offset 0x234
  0x1fff -> page  1, offset 0xfff
  0x2000 -> page  2, offset 0x000

pages needed
      0 bytes -> 0
      1 bytes -> 1
   4096 bytes -> 1
   4097 bytes -> 2

fault classification
  unmapped           -> Invalid
  mapped, not in ram -> Major
  resident, read-only-> Protection
  resident, writable -> Minor

all checks passed
```

`0x1fff` and `0x2000` differ by one byte and lie on different pages, which is why a
buffer that crosses a page boundary can fault halfway through a single read.

The scheduler prints:

```text
3 runnable tasks, 5 ms quantum
  slice 0:  0- 5 ms  encoder
  slice 1:  5-10 ms  decoder
  slice 2: 10-15 ms  gc
  slice 3: 15-20 ms  encoder
  slice 4: 20-25 ms  decoder
  slice 5: 25-30 ms  gc
  slice 6: 30-35 ms  encoder

worst-case wait for one slice: 15 ms
all checks passed
```

## Time and Space Complexity

| Operation | Time | Space |
|---|---|---|
| `split_page`, `pages_needed`, `classify_fault` | `O(1)` | none |
| `schedule(tasks, ticks)` | `O(ticks)` | one `&str` per tick |

## Limitations

**The fault model is a teaching simplification.** In Linux, a minor fault is one the
kernel resolves without I/O, typically because the page is already in the page cache or
is a fresh zero page, and it can occur on a read as well as a write. A write to a
read-only page is a protection fault only when the mapping itself is read-only; when the
mapping is writable and the page is shared copy-on-write, the same hardware fault is
resolved as a minor fault by copying the page. Three booleans cannot represent that
distinction.

**The worst-case figure is off by one quantum.** The program prints `QUANTUM_MS ×
tasks.len()`, 15 ms, as the wait for one slice. A task that has just finished its slice
waits for the other two tasks, 10 ms, before it runs again. The 15 ms figure is the
length of one full round, which is the bound on the time from any moment until a given
task finishes its next slice, provided every task uses its whole quantum.

**Real schedulers are not round robin.** Linux's CFS and EEVDF schedulers weight tasks
by priority, track the time each has received, and let tasks that block early give up
the rest of their quantum. Round robin is the base case those designs refine.

**The page size is a constant.** 4,096 bytes is the default on x86-64 and on most ARM
Linux systems, but AArch64 kernels can be configured for 16 KiB or 64 KiB pages, and
huge pages of 2 MiB and 1 GiB coexist with small ones. Portable code asks the system,
for example with `sysconf(_SC_PAGESIZE)`.

**`schedule` allocates the whole schedule.** A scheduler would compute the next task on
demand. An iterator such as `tasks.iter().cycle().take(ticks)` expresses the same
sequence lazily.

## Summary

- With a page size of `2^12`, the page number is the address shifted right by 12 and the
  offset is the low 12 bits.
- `div_ceil` computes the number of whole pages for a byte count without the overflow of
  the add-then-divide idiom.
- Matching on a tuple of booleans states a decision table whose completeness the
  compiler checks.
- Round robin gives each of `n` tasks one quantum `q` in turn, so a task waits at most
  `(n - 1) × q` between slices.
- Both programs model the ideas and omit what real kernels add: copy-on-write, page
  cache, multiple page sizes, and weighted scheduling.

## References

- Remzi H. Arpaci-Dusseau and Andrea C. Arpaci-Dusseau, *Operating Systems: Three Easy
  Pieces*, Arpaci-Dusseau Books, 2018, chapters 2 ("Scheduling: Introduction"), 18
  ("Paging: Introduction"), and 21 ("Swapping: Mechanisms").
- The Linux kernel documentation, [Memory management concepts](https://docs.kernel.org/admin-guide/mm/concepts.html).
- Standard library, [`u64::div_ceil`](https://doc.rust-lang.org/std/primitive.u64.html#method.div_ceil).
