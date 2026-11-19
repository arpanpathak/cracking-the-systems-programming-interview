# 12. File System Architecture and Durability

A file system provides a persistent, named abstraction for data stored on a block device. It organizes storage into structured entities, files and directories, and manages the mapping between human-readable hierarchical paths and physical disk blocks while surviving power loss and abrupt system crashes.

## 12.1 The File Descriptor and the Open File Description

The kernel mediates every file operation through three distinct layers of indirection:
1. **Per-Process File Descriptor Table:** Maps a small non-negative integer (`fd`, such as `3`) inside the process's PCB to a pointer in the system-wide open file table, along with per-descriptor flags such as `FD_CLOEXEC`.
2. **System-Wide Open File Description:** A kernel object created by each call to `open()` that stores the current byte offset, access mode (`O_RDONLY`, `O_WRONLY`, `O_RDWR`), status flags (`O_APPEND`, `O_NONBLOCK`), a reference count, and a pointer to the target inode.
3. **In-Memory Inode (`vnode` / `struct inode`):** Represents the underlying file itself (size, permissions, timestamps, link count, and physical block map), shared across all processes opening that file.

This three-level design explains why descriptors duplicated via `dup()` / `dup2()` or inherited across `fork()` point to the **same** open file description and therefore share a single synchronized byte offset, whereas two independent calls to `open()` on the same pathname allocate **separate** open file descriptions with independent offsets referencing the same underlying inode.

### 12.1.1 The POSIX File System Call Interface (`open`, `lseek`, `fstat`, `struct stat`, `ftruncate`, `fsync`, `unlink`)

Listings 12-1 through 12-4 exercise the core POSIX file-manipulation interface directly:

```text
int     open(const char *pathname, int flags, mode_t mode);
off_t   lseek(int fd, off_t offset, int whence);
int     fstat(int fd, struct stat *statbuf);
int     ftruncate(int fd, off_t length);
int     fsync(int fd);
int     unlink(const char *pathname);
```

- **`open(pathname, flags, mode)`:** Opens or creates a file and returns the lowest unused file descriptor (`>= 0`), or `-1` on error (`ENOENT`, `EACCES`, `EEXIST`, `EMFILE`).
  - **`flags`:** Combines an access mode (`O_RDWR` for both reading and writing) with creation and state flags: **`O_CREAT`** creates the file if it does not already exist; **`O_TRUNC`** resets an existing regular file's length to `0` bytes upon opening.
  - **`mode`:** Octal permission mask applied only when `O_CREAT` creates a new file. Passing **`0644`** requests owner read/write (`6 = rw-`), group read (`4 = r--`), and other read (`4 = r--`), which the kernel masks against the process's `umask` (`mode & ~umask`).
- **`lseek(fd, offset, whence)`:** Repositions the open file description's byte offset without transferring any data, returning the resulting absolute byte offset from the start of the file (`off_t >= 0`), or `(off_t)-1` on error (`ESPIPE` if `fd` refers to a non-seekable pipe or socket).
  - **`whence`:** Reference origin for `offset`: **`SEEK_SET`** sets the offset to `offset` bytes from byte `0`; **`SEEK_CUR`** adds `offset` to the current cursor (so `lseek(fd, 0, SEEK_CUR)` queries the current offset without moving it); **`SEEK_END`** sets the offset relative to the current end of the file.
  - Seeking beyond the current end of file is legal in POSIX and does not immediately allocate storage; a subsequent `write()` at the new offset creates a **sparse hole** spanning the unwritten gap.
- **`fstat(fd, statbuf)` and `struct stat`:** Populates the caller's `struct stat` with authoritative metadata read from the file's inode (returning `0` on success or `-1` on `EBADF` / `EFAULT`). Key fields inspected in systems code include:
  - **`st_ino` (`ino_t`):** Unique inode number identifying the file within its mounted filesystem.
  - **`st_size` (`off_t`):** Logical length of the file in bytes (the highest written or truncated byte offset, including any unallocated sparse holes).
  - **`st_blocks` (`blkcnt_t`):** Actual physical disk space allocated to the file, always reported by POSIX in **512-byte units** regardless of the filesystem's native 4 KiB page or cluster size (`st_blocks * 512` equals allocated bytes on disk).
  - **`st_blksize` (`blksize_t`):** Preferred I/O transfer block size for efficient buffered reads and writes.
  - **`st_mode` (`mode_t`) and `st_nlink` (`nlink_t`):** File type and permission bits, and the hard-link reference count pointing to this inode.
- **`ftruncate(fd, length)`:** Adjusts the file's logical size (`st_size`) to exactly `length` bytes, returning `0` on success or `-1` on error (`EINVAL`, `EACCES`). Shrinking discards trailing blocks; extending past the previous end creates a zero-reading sparse extension without allocating disk blocks.
- **`fsync(fd)`:** Flushes all modified data pages and inode metadata associated with `fd` from the kernel's volatile page cache down to stable non-volatile storage, blocking until the storage controller acknowledges completion (returning `0` on success or `-1` with `EIO` / `ENOSPC`).
- **`unlink(pathname)`:** Removes the directory entry naming `pathname` and decrements the target inode's hard-link count (`st_nlink`). Importantly, the kernel reclaims the inode and its data blocks only when **both** `st_nlink == 0` **and** zero open file descriptions reference the inode; an already-open file remains readable and writable even after being unlinked. Returns `0` on success or `-1` (`ENOENT`, `EACCES`).

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

## 12.2 On-Disk Organization and Inode-Based Mapping

A classic Unix file system partitions a block device into fixed-size blocks (commonly 4 KiB) organized into four structural regions:
- **Superblock:** Stores global file system geometry, block size, total inode and block counts, mount state, and pointers to root structures.
- **Allocation Bitmaps:** Compact bit arrays tracking which inodes (inode bitmap) and physical data blocks (data bitmap) are free or allocated.
- **Inode Table:** A fixed or dynamically allocated array of on-disk inode records indexed directly by inode number (`st_ino`).
- **Data Blocks:** The bulk of the partition storing file payloads and directory entry tables.

An **inode** is the authoritative descriptor for a file, recording its type, permissions, owner UID/GID, logical size, timestamps, hard-link count, and block-pointer table. Crucially, an inode does **not** store the file's name. Names reside exclusively inside **directories**, which are specialized files mapping `(filename -> inode_number)` pairs. Decoupling names from inodes makes **hard links** straightforward: multiple directory entries reference the same `st_ino`, incrementing `st_nlink`. To balance O(1) lookup for small files with multi-terabyte capacity for large files, classic inodes maintain twelve **direct block pointers**, followed by **single indirect**, **double indirect**, and **triple indirect** pointer trees (modern filesystems such as ext4, XFS, and APFS generalize this into **extent trees** recording contiguous `(logical_offset, physical_start, length)` ranges).

<figure>
<img src="figures/ch12_fs_layout.svg" alt="A file system's blocks: superblock, bitmaps, inode table, data blocks, with a directory resolving a name to an inode"/>
</figure>

<figure>
<img src="figures/ch12_inode.svg" alt="An inode with direct, indirect, double, and triple block pointers"/>
</figure>

## 12.3 Sparse Files and the Mechanics of Durability

File systems avoid wasting physical storage on large zero-filled regions through **sparse files**. When a process seeks forward across an unwritten interval (for example, writing 4 KiB at byte `0`, calling `lseek(fd, 4 * 1024 * 1024, SEEK_SET)`, writing 4 KiB at 4 MiB, and calling `ftruncate(fd, 8 * 1024 * 1024)`), the file system leaves the intermediate block pointers or extent entries unmapped. As Output 12-3 confirms, `st_size` reports the full 8 MiB logical span while `st_blocks * 512` consumes only 8 KiB of physical storage. Whenever a process reads from an unmapped hole, the kernel synthesizes zero bytes directly in memory without touching the disk. Virtual-machine disk images, core dumps, and database files rely heavily on sparse allocation.

Achieving crash **durability** requires explicit coordination with both the kernel page cache and the disk controller:
1. **Deferred writeback on `write()`:** Returning from `write()` confirms only that user bytes were copied into the kernel's volatile RAM page cache. On sudden power loss, dirty page-cache pages vanish.
2. **File and directory `fsync()`:** Invoking `fsync(fd)` forces the file's dirty data blocks and inode metadata onto stable media. However, for a **newly created** or **renamed** file, calling `fsync(fd)` alone is insufficient: the parent directory entry linking the filename to the new inode may still reside solely in the page cache. Crash-safe atomic file replacement therefore follows a strict four-step protocol: write to a temporary sibling file, `fsync()` the temporary file, atomically `rename()` it over the target path, and `fsync()` the parent directory descriptor.
3. **Journaling versus application durability:** Metadata journaling (ext4, XFS, NTFS) logs structural filesystem transitions in a write-ahead journal so the filesystem mounts consistently after a crash without running a full `fsck` scan, yet journaling does **not** guarantee that un-`fsync`ed application writes survive a power cut.

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
