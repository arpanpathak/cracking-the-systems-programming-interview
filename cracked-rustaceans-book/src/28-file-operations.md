# 28. File Operations and Errors {#file-operations}

*Source files: [`src/bin/copy_rename_delete_file.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/copy_rename_delete_file.rs) and
[`src/bin/file_error_handling.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/file_error_handling.rs). Run them with
`cargo run --bin copy_rename_delete_file` and
`cargo run --bin file_error_handling`.*

## Problem Statement

Two programs cover the mutating file operations and the other half of the
interface: copy, rename and delete a file, and decide what to report when a read
fails.

## Designing a Solution

`fs::copy` reads one file and writes another, returning the number of bytes
copied. `fs::rename` changes a name, and on one filesystem it is an atomic
replacement: the target either has the old contents or the new ones, never a
mixture. `fs::remove_file` removes a name for a file, not a directory.

Errors are values. `io::Error` carries an `ErrorKind`, which is the part a caller
can branch on without examining the message text. `ErrorKind::NotFound` is the
common case for a path that does not exist, and `Err(e) if e.kind() ==
io::ErrorKind::NotFound` matches it before the general error arm. The guard is
the mechanism: the arm is only selected when its condition holds, so the ordering
of the arms is explicit rather than incidental.

## Implementation

`copy_rename_delete_file.rs` performs the three operations in sequence:

<p class="listing"><span class="listing-label">Listing 28.1</span> The complete program. <code>src/bin/copy_rename_delete_file.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/copy_rename_delete_file.rs">read the file on GitHub</a></p>

`file_error_handling.rs` turns a failed read into a message that depends on the
kind of failure:

<p class="listing"><span class="listing-label">Listing 28.2</span> The complete program. <code>src/bin/file_error_handling.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/file_error_handling.rs">read the file on GitHub</a></p>

Each call in the first program is a fallible operation, and `?` returns early on
the first failure. That is the correct default for a sequence in which each step
depends on the previous one: copying before the file exists has no meaning.

In the second program the error is matched rather than propagated, because `main`
returns `()`. A `main` that returns `Result` instead would let `?` do the work,
at the cost of printing the error through the runtime's `Debug` implementation
rather than the message chosen here. The `eprintln!` writes to standard error,
which keeps diagnostics out of a pipeline that reads standard output.

## Intuition

`copy_rename_delete_file.rs` from an empty directory:

```text
statement                   files afterwards
fs::write("a.txt", ...)     a.txt
fs::copy("a.txt","b.txt")   a.txt  b.txt
fs::rename("b.txt","c.txt") a.txt  c.txt
fs::remove_file("a.txt")    c.txt
println!("Done")            prints Done
```

`file_error_handling.rs` with no `missing.txt`:

```text
read_file("missing.txt")    Err(kind = NotFound)
first arm                   does not match Ok
guarded arm                 matches, prints "File not found" to stderr
main                        returns ()
```

## Time and Space Complexity

| Operation | Cost | Condition |
|---|---|---|
| `fs::copy` | `O(n)` time and one extra file's worth of writes | `n` bytes copied; the kernel may choose the buffer size |
| `fs::rename` | `O(1)` time | source and target are on one filesystem |
| `fs::remove_file` | `O(1)` time | the name is unlinked; the data is freed when the last handle closes |
| `ErrorKind` match | `O(1)` time | the kind is a field of the error |

## Limitations

**`rename` is not portable across filesystems.** When the source and target are
on different mounts, the operation fails rather than copying, and the error kind
is platform specific. Moving between filesystems needs a copy followed by a
remove, which is not atomic.

**`copy` does not preserve everything.** It writes the file contents and copies
the permission bits, but it does not preserve ownership, timestamps, or extended
attributes. A tool that needs those has to set them explicitly.

**`remove_file` refuses a directory.** A directory needs `remove_dir`, which
itself requires the directory to be empty. A recursive delete has to walk the
tree and remove children before parents.

**A failure in the middle leaves the earlier steps applied.** The first program
returns as soon as a call fails, so a failure at `rename` leaves `a.txt` and
`b.txt` in place. Nothing here rolls back, and a tool that must leave the
directory unchanged needs a temporary directory and a final rename.

**The error message in the last arm is the library's.** `eprintln!("Error: {}", e)`
prints `Display` for `io::Error`, which includes the operating system message but
not the path. Adding the path is the caller's job, because the error does not
carry it.

## Summary

- `copy`, `rename` and `remove_file` are the mutating operations, and `rename` is
  the atomic replacement primitive within one filesystem.
- Errors are values; `ErrorKind` is the part a program can branch on, and a
  match guard is how the branch is written.
- `?` is the right default for a sequence of dependent steps, and an explicit
  match is the right form when the program chooses the message.
- Diagnostics go to standard error, which keeps standard output usable as data.

## References

- Standard library, [`fs::copy`](https://doc.rust-lang.org/std/fs/fn.copy.html).
- Standard library, [`fs::rename`](https://doc.rust-lang.org/std/fs/fn.rename.html).
- Standard library, [`fs::remove_file`](https://doc.rust-lang.org/std/fs/fn.remove_file.html).
- Standard library, [`io::ErrorKind`](https://doc.rust-lang.org/std/io/enum.ErrorKind.html).
