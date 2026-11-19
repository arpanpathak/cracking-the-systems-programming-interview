# 12. File Systems

A **file system** stores named files on a storage device and finds their
bytes again when a program asks for them by name. To do so, it keeps
several structures on the device: directories that hold names, inodes that
describe files, and blocks that hold their contents.

In this chapter, we first use the system calls that operate on files and
print the metadata that the kernel keeps for a file. We then describe the
structures on disk that those calls read. Finally, we create a sparse
file, whose size exceeds the storage it occupies, and we explain what
`fsync` guarantees after a crash.

<div class="callout glance">
<span class="label">This chapter covers</span>

- `open`, `read`, `write`, `lseek`, `close`, and `stat`
- file descriptors, open file descriptions, and the file offset
- superblock, bitmaps, inode table, and data blocks
- directories, inodes, and hard links
- direct and indirect block pointers
- sparse files
- `fsync` and durable file creation

</div>

## 12.1 Files through system calls

A program works with a file through six calls. `open` takes a path and
returns a **file descriptor**, a small integer that identifies the open
file within the process. `read` and `write` transfer bytes starting at the
current **file offset**, and they advance the offset by the number of
bytes transferred. `lseek` sets the offset to a chosen position. `close`
releases the descriptor. `stat` returns the metadata of a file, such as
its size, without reading its contents.

A descriptor does not store this offset itself. For each `open` call, the
kernel creates an object called an **open file description**, which holds
an offset, and the new descriptor refers to that object. When a process
calls `fork` or `dup`, the resulting descriptor refers to that same
description. A parent and a child that inherited a descriptor therefore
share one offset, and a `read` in the child advances the position that its
parent sees. Two separate calls to `open` on one file, in contrast, create
two descriptions with independent offsets.

**Listing 12-1. open, write, lseek, read, and stat (C++20).**

```cpp
{{#include ../code/ch12/files.cpp}}
```

**Output 12-1. A file of 36 bytes and its metadata.**

```text
{{#include ../code/out/ch12_files.out}}
```

**Listing 12-2. The same operations with the Rust standard library.**

```rust
{{#include ../code/ch12/files.rs}}
```

**Output 12-2.**

```text
{{#include ../code/out/ch12_files_rs.out}}
```

Our program writes `operating systems\n`, which is 18 bytes long, twice,
so its offset is 36 after the second write. It then moves that offset back
to 0 with `lseek` and reads all 36 bytes again.

The last line of the output shows three fields that `stat` returns.

- `st_ino`, here 10922009, is an **inode number**. It identifies a file
  within its file system, independently of any name.
- `st_size` is the file's length in bytes, 36.
- `st_blocks` is the amount of storage allocated to the file, counted in
  units of 512 bytes. A value of 8 means 8 × 512 = 4,096 bytes. Storage is
  allocated in blocks of 4 KiB, so even a file of 36 bytes occupies one
  whole block.

## 12.2 The structure on disk

Figure 12-1 shows a simplified layout, modeled on the classic Unix file
system. The file systems of Linux and macOS are more elaborate, but they
keep the same kinds of information.

<figure>
<img src="figures/ch12_fs_layout.svg" alt="A file system's blocks: superblock, bitmaps, inode table, data blocks, with a directory resolving a name to an inode"/>
</figure>

A file system divides its storage into **blocks** of a fixed size, 4 KiB
in our examples. The blocks serve five purposes.

- A **superblock** records how large the file system is and where its
  other areas begin.
- An **inode bitmap** has one bit per inode and marks inodes that are in
  use.
- A **data bitmap** has one bit per data block and marks blocks that are
  in use.
- An **inode table** holds all inodes. An **inode** describes one file. It
  contains a file type, permissions, an owner, a size, several timestamps,
  a link count, and pointers to that file's data blocks.
- **Data blocks** hold what files and directories contain.

<figure>
<img src="figures/ch12_inode.svg" alt="An inode with direct, indirect, double, and triple block pointers"/>
</figure>

A **directory** is a file whose contents are a list of entries. Each entry
holds a name and an inode number. To open `/a/b.txt`, the kernel searches
the root directory for the entry `a`, reads the inode of `a`, searches
that directory for `b.txt`, and reads the inode of `b.txt`.

An inode does not contain the name of its file. Names exist only in
directory entries. For this reason, renaming a file changes one directory
entry and leaves the inode and the data blocks unchanged. It is also why a
file can have several names. A **hard link** is an additional directory
entry with the same inode number, and the link count in the inode records
how many entries refer to it. The kernel frees the inode and its blocks
when the link count reaches zero and no process has the file open.

Figure 12-2 shows the block pointers of an inode. The first 12 pointers
are *direct*, which means that each one holds the number of a data block.
With blocks of 4 KiB, direct pointers cover files of up to 12 × 4 KiB =
48 KiB. For larger files, the inode has an *indirect* pointer. It holds
the number of a block that contains further block pointers, 512 or 1,024
of them, depending on the size of a pointer. A *double indirect* pointer
adds another level, and a *triple indirect* pointer adds a third. Most
files are small, and with this design the kernel reaches their blocks
directly from the inode. Only large files need the additional reads.

## 12.3 Sparse files

A program can set the offset beyond the end of a file with `lseek` and
then write there. The file system allocates no blocks for the region that
was skipped. Such a region is called a **hole**, and a file with
holes is a **sparse file**. Reading from a hole returns zeros.

Listing 12-3 creates a sparse file. It writes 4,096 bytes at offset 0, moves its offset to 4 MiB, and writes
another 4,096 bytes there. It then extends the file to 8 MiB with
`ftruncate`, which adds a second hole at the end. Finally, it reads 16
bytes from the first hole, at offset 2 MiB.

**Listing 12-3. A file with a logical size of 8 MiB and 8 KiB of storage (C++20).**

```cpp
{{#include ../code/ch12/sparse.cpp}}
```

**Output 12-3. The logical size is about 1,000 times the allocated storage.**

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

`stat` reports a size of 8,388,608 bytes, which is 8 MiB. Yet the file occupies only 16 units of 512 bytes, which is 8,192 bytes,
or two blocks of 4 KiB. One block holds what was written at offset 0, and
the other holds what was written at offset 4 MiB. All 16 bytes read from
the hole are zero, although nothing is stored for them.

Sparse files are common in practice. Disk images of virtual machines and
database files are often created with a large logical size and receive
storage only for the parts that have been written.

<div class="callout caution">
<span class="label">Watch out</span>

A program that copies a sparse file by reading every byte and writing it
to a new file fills the holes with real blocks of zeros. An 8 MiB sparse
file then occupies 8 MiB, and a sparse virtual machine image of 100 GB may
no longer fit on the target device. Copy tools have options that preserve
holes, such as `cp --sparse=always` on Linux.

</div>

## 12.4 Durability and fsync

When `write` returns, its data has been copied into the kernel's page
cache, which we met in Chapter 7. That data has not necessarily been
written to a storage device. The kernel writes cached pages to the device
later, in the background, and whatever has not been written when power
fails is lost.

A program that needs its data to survive a power failure calls `fsync` on
its descriptor. `fsync` writes a file's data blocks and inode to the
device and returns only after the device has reported that these writes
are complete.

For a newly created file, one `fsync` is not sufficient. A file's name is
stored in a directory, and that directory is a separate file. If a system
crashes after the new file's data has reached the device but before its
directory entry has, the file has no name and cannot be found. A program
therefore creates a file durably in three steps. It writes its data, calls
`fsync` on the file, and then calls `fsync` on the containing directory.

Modern file systems keep a **journal**, a log in which they record each
change to their structures before they apply it. After a crash, the file
system reads the journal and completes or discards unfinished changes, so
its structures remain consistent. A journal does not remove the need for
`fsync`. It protects the structures of the file system, but it does not
ensure that the most recent data of an application has been written.

Storage devices have write caches of their own, and a device may report
that a write is complete while the data is still in its cache. During
`fsync`, the kernel sends the device a command to flush that cache. A
device that ignores this command, or a system configured not to send it,
can lose data after a power failure even though `fsync` returned
successfully.

<div class="callout keyidea">
<span class="label">Key idea</span>

`write` copies data into the page cache, and `fsync` writes it to the
device. To create a file durably, a program calls `fsync` on the file and
then on its directory.

</div>

<div class="callout summary">
<span class="label">Summary</span>

- A descriptor refers to an open file description, which holds the file
  offset. Descriptors that were duplicated by `fork` or `dup` share one
  offset.
- A directory maps names to inode numbers. An inode holds the metadata and
  the block pointers of a file, but not its name.
- An inode has 12 direct pointers and three levels of indirect pointers.
- A sparse file has holes that occupy no storage and read as zeros.
  `st_blocks` reports the storage that is actually allocated.
- `fsync` writes the data and the inode of a file to the device. A new
  file also needs an `fsync` on its directory.

In Chapter 13, we use descriptors to wait for input from many sources at
once.

</div>
