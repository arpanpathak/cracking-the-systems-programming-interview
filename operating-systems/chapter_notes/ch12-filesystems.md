# Chapter 12: File System Architecture and Durability

A file system provides a persistent, named abstraction for data stored on a physical device. It organizes storage into structured entities—files and directories—and manages the complex mapping between human-readable names and the underlying physical blocks of a storage medium.

## 12.1 The File Descriptor and the Open File Description

The interface between a process and a file is mediated by the file descriptor, a lightweight integer handle. However, the logical state of a file—most notably its current offset—is maintained within a distinct kernel object known as an **open file description**. This separation is critical for supporting process semantics: while multiple file descriptors within a single process may point to the same open file description (via `dup`), descriptors inherited from a parent during a `fork` also share the same underlying description. Consequently, these descriptors share a single, synchronized file offset. In contrast, independent calls to `open` on the same file create separate open file descriptions, each maintaining its own independent offset.

## 12.2 On-Disk Organization and Inode-Based Mapping

A file system decomposes a storage device into fixed-size blocks and manages them through several specialized structures:
- **Superblock:** Maintains global metadata regarding the file system's geometry and status.
- **Bitmaps:** Track the allocation status of inodes and data blocks.
- **Inode Table:** Contains the inode entries, which act as the authoritative descriptors for individual files.
- **Data Blocks:** The physical regions where the actual contents of files and directories are stored.

An **inode** is the central metadata structure for a file, containing its type, permissions, ownership, size, and link count. Crucially, the inode does not store the file's name; instead, names are managed within **directories**, which are specialized files containing mappings from filenames to inode numbers. This decoupling allows for the implementation of **hard links**, where multiple directory entries point to the same inode, increasing its link count. The inode maintains the file's data via a hierarchical pointer structure: twelve **direct pointers** for small files, supplemented by **indirect**, **double indirect**, and **triple indirect** pointers to facilitate the addressing of much larger files.

## 12.3 Sparse Files and the Mechanics of Durability

File systems can optimize storage through the use of **sparse files**. By allowing files to contain "holes"—regions of the virtual address space that are not backed by physical blocks—the system can represent large, mostly empty files without consuming excessive physical storage. When a program reads from a hole, the kernel transparently returns zero-filled data.

A significant challenge in file system design is ensuring **durability** in the face of system failures. While a `write` operation merely transfers data into the kernel's page cache, the actual persistence to the physical medium is deferred. To guarantee that data is safely committed to stable storage, a program must invoke `fsync`. However, for a newly created file to be truly durable, a two-stage synchronization is required: first, an `fsync` on the file itself to commit its data and inode, followed by an `fsync` on the containing directory to ensure the directory entry (the link between the name and the inode) is also persisted.

While modern file systems employ **journaling** to maintain the structural integrity of the file system after a crash, journaling does not substitute for `fsync` in guaranteeing the durability of individual application-level writes.
