# 27. Paths and Directory Traversal {#paths-and-directories}

*Source files: [`src/bin/path_buff.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/path_buff.rs), [`src/bin/list_directory.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/list_directory.rs), and
[`src/bin/recusrive_directory_walk.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/recusrive_directory_walk.rs). Run them with
`cargo run --bin path_buff`, `cargo run --bin list_directory`, and
`cargo run --bin recusrive_directory_walk`.*

## Problem Statement

Three programs answer the questions a tool needs about the filesystem before it
opens anything: how a path is assembled and taken apart, what a directory
contains, and how to visit every file below a starting directory.

## Designing a Solution

A path is a sequence of components, not a string. `Path` is the borrowed form and
`PathBuf` is the owned form, with the same relationship as `str` and `String`.
`join` builds a new `PathBuf` and leaves the receiver alone; `push` extends the
receiver in place. Because a directory separator differs between platforms, the
two methods insert the platform's separator, which string concatenation does not.

The inspection methods return `Option` rather than a sentinel, because a path
need not have the component asked for. `/tmp/data.txt` has a parent, a file name
and an extension; `/` has none of the three. Returning `None` for those cases
keeps the caller from inventing a value.

`fs::read_dir` yields one `io::Result<DirEntry>` per directory entry. The `Result`
matters when an entry cannot be read, which `for entry in fs::read_dir(dir)?`
would otherwise hide. `DirEntry::path` produces an owned `PathBuf`, and
`DirEntry::file_type` returns the entry's type from the directory listing, which
avoids the metadata lookup that `Path::is_dir` performs per entry.

A recursive walk is the same loop with a call to itself for each subdirectory,
and `?` on that call stops the walk at the first unreadable directory.

## Implementation

`path_buff.rs` builds one path with `join` and another with `push`, then reads
parts of the second:

```rust
use std::path::{Path, PathBuf};

fn main() {
    let dir = Path::new("/tmp");
    let file = dir.join("data.txt");

    let mut buf = PathBuf::from(dir);
    buf.push("nested");
    buf.push("file.txt");

    println!("file: {}", file.display());
    println!("buf:  {}", buf.display());
    println!("parent: {:?}", buf.parent());
    println!("file_name: {:?}", buf.file_name());
    println!("ext: {:?}", buf.extension());
}
```

`list_directory.rs` prints one line per entry of the working directory:

```rust
use std::fs;
use std::io;

fn main() -> io::Result<()> {
    for entry in fs::read_dir(".")? {
        let entry = entry?;
        let path = entry.path();

        if path.is_dir() {
            println!("[DIR]  {}", path.display());
        } else {
            println!("[FILE] {}", path.display());
        }
    }
    Ok(())
}
```

`recusrive_directory_walk.rs` repeats that loop for every subdirectory:

```rust
use std::fs;
use std::io;
use std::path::Path;

fn walk(dir: &Path) -> io::Result<()> {
    for entry in fs::read_dir(dir)? {
        let entry = entry?;
        let path = entry.path();
        let file_type = entry.file_type()?;

        if file_type.is_dir() {
            println!("[DIR]  {}", path.display());
            walk(&path)?;
        } else {
            println!("[FILE] {}", path.display());
        }
    }
    Ok(())
}

fn main() -> io::Result<()> {
    walk(Path::new("."))?;
    Ok(())
}
```

`Path::display` is the conversion for printing. `Path` is not guaranteed to be
valid UTF-8, so it does not implement `Display`; `display` returns a wrapper that
replaces unrepresentable bytes, which is what a terminal needs.

`DirEntry::file_type` is used in the walk while the single-directory program uses
`Path::is_dir`. The two differ for a symbolic link: `file_type` reports the link
itself, and `is_dir` follows the link. The walk therefore prints a link to a
directory as `[FILE]` and does not descend into it, which is also what keeps a
link cycle from producing an unbounded walk.

## Intuition

`path_buff.rs` on a Unix host:

```text
dir                      "/tmp"
dir.join("data.txt")     "/tmp/data.txt"
PathBuf::from(dir)       "/tmp"
push("nested")           "/tmp/nested"
push("file.txt")         "/tmp/nested/file.txt"

file: /tmp/data.txt
buf:  /tmp/nested/file.txt
parent: Some("/tmp/nested")
file_name: Some("file.txt")
ext: Some("txt")
```

`list_directory.rs` in a directory holding `Cargo.toml` and `src`:

```text
[FILE] ./Cargo.toml
[DIR]  ./src
```

`recusrive_directory_walk.rs` from the same directory:

```text
[FILE] ./Cargo.toml
[DIR]  ./src
[FILE] ./src/lib.rs
[FILE] ./src/main.rs
```

Neither listing sorts its output, so the order above is one possible order rather
than the order the filesystem guarantees.

## Time and Space Complexity

| Operation | Cost | Condition |
|---|---|---|
| `Path::join`, `PathBuf::push` | `O(length)` time, one allocation for `join` | the path is copied into the result |
| `read_dir` iteration | one directory read plus one `DirEntry` per entry | the order is unspecified |
| `DirEntry::file_type` | no extra metadata call on most platforms | the type comes with the entry |
| `Path::is_dir` | one metadata call per call | it resolves the path again |
| recursive walk | `O(entries)` time, `O(depth)` stack | one frame per open directory |

## Limitations

**The walk has no cycle protection beyond not following links.**
`entry.file_type` does not follow a symbolic link, so a link to a directory is
not entered. A bind mount or a hard-linked directory can still present a cycle,
and the walk would not terminate.

**Depth is bounded by the stack.** `walk` calls itself once per directory level,
so a tree several thousand levels deep exhausts the stack. An explicit stack of
`PathBuf` values removes that limit.

**One unreadable directory stops the walk.** `walk(&path)?` propagates the error
to `main`, so a permission failure at one level abandons the remaining
directories. A tool that should continue past such an entry has to collect the
error and resume.

**The order is unspecified and unsorted.** `read_dir` returns entries in the
order the filesystem supplies. A reproducible listing has to collect the entries
and sort them, which the programs do not do.

**Relative names depend on the working directory.** Both directory programs walk
`"."`, so their output changes with the directory they are started in, and
`list_directory` does not recurse.

## Summary

- `Path` and `PathBuf` are the borrowed and owned forms of a path, and `join` is
  the non-mutating builder against `push`.
- The inspection methods return `Option`, because the component asked for may not
  exist.
- `DirEntry::file_type` avoids a per-entry metadata call, and its refusal to
  follow symbolic links is what keeps the walk finite.
- The recursive walk trades an explicit stack for call frames, so its depth is
  limited by the stack.

## References

- Standard library, [`std::path`](https://doc.rust-lang.org/std/path/).
- Standard library, [`PathBuf::push`](https://doc.rust-lang.org/std/path/struct.PathBuf.html#method.push).
- Standard library, [`std::fs::read_dir`](https://doc.rust-lang.org/std/fs/fn.read_dir.html).
- Standard library, [`DirEntry::file_type`](https://doc.rust-lang.org/std/fs/struct.DirEntry.html#method.file_type).
