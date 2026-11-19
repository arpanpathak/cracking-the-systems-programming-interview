# 12. File Systems

A file system is the machinery that turns names into bytes on durable
storage: directories, inodes, blocks, and the journal that keeps the
whole structure consistent across crashes. This chapter opens the
machinery from the system call side — open, read, write, seek, stat —
then looks at the on-disk structure those calls consult, and ends with
the two properties every storage engineer must be able to explain:
sparse files and the meaning of `fsync`.

<div class="callout glance">
<span class="label">At a glance</span>

- A file descriptor is a per-process handle onto an open file
  description, which carries the file offset.
- The directory holds names; the inode holds everything else, including
  the block pointers.
- Sparse files store holes as nothing, and read them back as zeros.
- `fsync` orders data and metadata to the device; without it, a power
  loss can leave a file's directory entry without its data.

</div>

## 12.1 Files through system calls

The file interface is five calls. `open` resolves a path to a
**descriptor** — a small integer naming the open file in this process's
descriptor table. `read` and `write` transfer bytes at the descriptor's
current **file offset**, and advance it. `lseek` moves the offset.
`close` releases the descriptor. `stat` reads the metadata without
touching the data.

The offset deserves precision, because it explains behavior that
surprises people. The offset lives in the **open file description**,
the kernel object shared by descriptors duplicated through `fork` or
`dup`. A parent and child that share a description share one offset —
the child's reads advance the parent's position. Two separate `open`
calls produce separate descriptions, each with its own offset. The
listing demonstrates the basic case.

**Listing 12-1. open, write, seek, read, stat (C++20).**

```cpp
{{#include ../code/ch12/files.cpp}}
```

**Output 12-1. Thirty-six bytes, one inode, a handful of blocks.**

```text
{{#include ../code/out/ch12_files.out}}
```

**Listing 12-2. The same operations through the Rust standard library.**

```rust
{{#include ../code/ch12/files.rs}}
```

**Output 12-2.**

```text
{{#include ../code/out/ch12_files_rs.out}}
```

The metadata line names the structure underneath. `st_ino` is the
**inode number** — the file's identity on this file system, distinct
from its name. `st_size` is 36, the bytes written. `st_blocks` counts
the storage actually allocated, in 512-byte units — eight blocks for a
36-byte file, because the file system allocates in larger units, 4 KiB
here. The three numbers together are the interface between a file's
logical size and its physical footprint, and the next sections open
each side.

## 12.2 The structure on disk

Figure 12-1 is the canonical layout, simplified from the Unix file
systems that Linux and macOS descend from.

<figure>
<img src="diagrams/ch12_fs_layout.svg" alt="A file system's blocks: superblock, bitmaps, inode table, data blocks, with a directory resolving a name to an inode"/>
</figure>

The file system is a sequence of fixed-size **blocks**. The
**superblock** records the geometry. Two **bitmaps** track which inodes
and which blocks are free. The **inode table** holds one inode per
file — mode, owner, size, timestamps, link count, and the block
pointers of Figure 12-2. The **data blocks** hold file contents and
directories.

<figure>
<img src="diagrams/ch12_inode.svg" alt="An inode with direct, indirect, double, and triple block pointers"/>
</figure>

A directory is a file whose data blocks contain entries — a name and an
inode number each. Opening `/a/b.txt` walks three directories, each
walk a lookup in a table, until the final inode appears. The name never
enters the inode; the inode number is the identity. That separation is
why renaming is cheap (one directory entry changes) and why a file can
have several names (each hard link is another entry pointing at the
same inode, and the link count in the inode tracks them).

Small files live in the inode's direct pointers — twelve blocks, 48 KiB
at 4 KiB per block. Larger files add one indirect block per level of
indirection, each holding hundreds of pointers. The split exists for
the same reason as Chapter 7's page tables: most files are small, and
the small case must not pay for the large case's generality.

## 12.3 Sparse files

A file whose logical size exceeds its allocated blocks is **sparse**.
Seeking past the end and writing creates a hole: the skipped region is
not allocated, and reads from it return zeros. The next listing builds
one on purpose and reads its hole back.

**Listing 12-3. Eight mebibytes of file, eight kilobytes of storage (C++20).**

```cpp
{{#include ../code/ch12/sparse.cpp}}
```

**Output 12-3. Logical size and allocated blocks differ by a factor of a thousand.**

```text
{{#include ../code/out/ch12_sparse.out}}
```

**Listing 12-4. The same sparse file in Rust.**

```rust
{{#include ../code/ch12/sparse.rs}}
```

**Output 12-4.**

```text
{{#include ../code/out/ch12_sparse_rs.out}}
```

The numbers are the lesson. The file reports 8,388,608 bytes. It
occupies 16 blocks of 512 bytes — 8 KiB — because two 4 KiB islands
were written and nothing in between. The read from the hole returns
zeros the file system never stored. Sparse files are how virtual
machine images, database files, and container layers stay small on
disk while appearing large to programs.

<div class="callout caution">
<span class="label">Watch out</span>

Copying a sparse file with a tool that reads and rewrites every byte
materializes the holes — an 8 MiB sparse file becomes an 8 MiB dense
file, and a 100 GB VM image may not fit where it came from. Tools that
preserve sparseness, and copy-on-write file systems that share
extents, exist precisely because the naive copy is wrong.

</div>

## 12.4 Durability: what fsync promises

The last property is the one most often misunderstood. `write` returns
when the data is in the kernel's page cache, not on the device. The
cache is fast and correct for reads, but a power loss discards it.
`fsync` is the call that says: write this file's data and metadata to
the device, and do not return until the device has them.

The subtlety is that two structures must reach the device, not one. The
data blocks and the inode — plus, for a newly created file, the
directory entry that names it. A crash between the data and the
directory leaves a directory entry pointing at an inode whose blocks
were never written — the classic "file exists but is empty" failure.
Durable creation is therefore an ordered sequence: write, `fsync` the
file, `fsync` the containing directory. Journaling file systems
simplify the internals — they record each operation's intent in a
journal first, then apply it — but the ordering requirement at the
system call level remains.

The other half of durability is the device's own write cache, which
may acknowledge a write it has not stored. The kernel issues cache
flush commands where the hardware supports them; storage configured
without them lies about `fsync`. That is a hardware configuration
question, but it belongs in this chapter, because every guarantee
above it depends on the answer.

<div class="callout keyidea">
<span class="label">Key idea</span>

The page cache makes writes fast and durability explicit. `write`
reaches the cache; `fsync` reaches the device; and a new file needs
two `fsync`s — the file, then its directory — before the name and the
bytes are durable together.

</div>

<div class="callout summary">
<span class="label">Summary</span>

- Descriptors are per-process; the file offset lives in the shared
  open file description.
- Directories map names to inode numbers; inodes hold metadata and
  block pointers; the two are deliberately separate.
- Sparse files store holes as nothing and read them as zeros — a
  logical-to-physical ratio visible in `st_blocks`.
- `fsync` orders data and metadata to the device; durable file
  creation fsyncs the file and its directory.
- Chapter 13 takes the descriptor into the I/O stack's busiest
  pattern: waiting for many of them at once.

</div>
