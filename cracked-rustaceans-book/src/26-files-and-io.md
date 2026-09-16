# 26. Reading and Writing Files {#files-and-io}

*Source files: [`src/bin/read_write_file.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/read_write_file.rs),
[`src/bin/append_to_file_open_options.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/append_to_file_open_options.rs), and
[`src/bin/readfile_line_by_line.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/readfile_line_by_line.rs). Run them with
`cargo run --bin read_write_file`,
`cargo run --bin append_to_file_open_options`, and
`cargo run --bin readfile_line_by_line`.*

## Problem Statement

Three programs cover the file operations a command-line tool needs: write a file
from a string, add lines to an existing file, and read a file back, either whole
or one line at a time. Each reports a failure through `io::Result` rather than
terminating on the first error.

## Designing a Solution

`std::fs` provides the whole-value operations. `fs::write` creates a file or
replaces its contents in one call, and `fs::read_to_string` reads an entire file
into a `String`. Both return `io::Result`, so `?` propagates a failure to the
caller, and returning that result from `main` prints the error and sets a nonzero
exit status.

Appending needs `OpenOptions`, because `fs::write` truncates. `OpenOptions::new()`
assembles the flags for a single `open` call: `create(true)` makes the file when
it is missing, and `append(true)` places every write at the end. Two `writeln!`
calls then add two lines without reading the existing contents.

Reading line by line uses a `BufReader`. The reader owns a buffer and fills it in
blocks, so `lines()` does not issue one system call per line. `BufRead` must be
in scope for the method to resolve, even though the value is a `BufReader`; that
is the only trait import the program needs. Each item is an `io::Result<String>`
without its terminator, so an unreadable line is reported rather than skipped.

## Implementation

`read_write_file.rs` writes a string and reads it back through two paths built in
different ways:

<p class="listing"><span class="listing-label">Listing 26.1</span> The complete program. <code>src/bin/read_write_file.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/read_write_file.rs">read the file on GitHub</a></p>

`append_to_file_open_options.rs` adds two lines to a file that survives the run:

<p class="listing"><span class="listing-label">Listing 26.2</span> The complete program. <code>src/bin/append_to_file_open_options.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/append_to_file_open_options.rs">read the file on GitHub</a></p>

`readfile_line_by_line.rs` numbers the lines as it prints them:

<p class="listing"><span class="listing-label">Listing 26.3</span> The complete program. <code>src/bin/readfile_line_by_line.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/readfile_line_by_line.rs">read the file on GitHub</a></p>

`read_content_of_file` takes `&Path` rather than `&PathBuf`. A `&PathBuf`
coerces to `&Path` at the call site, but a `&Path` does not coerce to `&PathBuf`,
so the `&Path` signature accepts strictly more callers: both `&joined_path` and
`&mut_base_dir` below borrow as `&PathBuf`, and the coercion is what lets a
`&Path`-typed parameter accept both. `fs::read_to_string` already returns
`io::Result<String>`, the function's own return type, so the body returns that
value directly rather than unwrapping it with `?` and rewrapping it in `Ok`.

`OpenOptions` is consumed by `open`, which is why the builder chain ends in a
single statement. The two flags are independent: `create` decides what happens
when the file is absent, and `append` decides where each write lands. Without
`create`, opening a missing `log.txt` returns `ErrorKind::NotFound`.

## Intuition

`read_write_file.rs`, from an empty working directory:

```text
statement                         effect
fs::write(...)                    hello.txt is created with "Hello, NVIDIA!\n"
PathBuf::from(".").join(...)      joined_path   = "./hello.txt"
push("hello.txt")                 pushed_path   = "./hello.txt"
read_content_of_file(joined)      returns "Hello, NVIDIA!\n"
read_content_of_file(pushed)      returns the same string
```

`append_to_file_open_options.rs`, run twice with `log.txt` absent at the start:

```text
run 1   log.txt  ->  "New log line\nAnother line\n"
run 2   log.txt  ->  "New log line\nAnother line\nNew log line\nAnother line\n"

the file is opened for append, so the second run adds to the end rather than
replacing the contents
```

`readfile_line_by_line.rs` over that file:

```text
1: New log line
2: Another line
```

The index is one-based because `enumerate` starts at zero and the program prints
`index + 1`.

## Time and Space Complexity

| Operation | Cost | Condition |
|---|---|---|
| `fs::read_to_string` | `O(n)` time, `O(n)` space | `n` bytes in the file; the whole file is held in memory |
| `fs::write` | `O(n)` time | one truncation followed by the writes |
| `writeln!` on an append handle | one write per call | the handle is not line-buffered; each call reaches the kernel |
| `BufReader::lines` | `O(n)` time, `O(1)` space in the buffer | one `String` allocation per line |

`read_to_string` fails when the bytes are not valid UTF-8, and it allocates the
whole file before returning. A program that reads a large file should keep the
`File` and read through the `BufReader` rather than calling `read_to_string`.

## Limitations

**Neither writer is atomic.** A process that stops between the truncation and the
writes leaves a partial file. Replacing a file without that window is done by
writing a temporary file in the same directory and renaming it over the target.

**No call requests a flush.** `fs::write` and `writeln!` return once the data has
reached the operating system, not the storage device, so a power loss can lose
recent writes. `File::sync_all` is the call that waits for the device.

**Relative paths depend on the working directory.** All three programs use names
such as `hello.txt` and `log.txt`, which resolve against the directory the
program was started in. Running `readfile_line_by_line` before
`append_to_file_open_options` reports `NotFound`.

**`lines()` splits on one separator.** It divides on `\n` and removes a trailing
`\r`, so a file separated by `;` or by a bare `\r` is read as one line. The final
line is yielded even when it has no terminator.

**The two writers ignore the returned length.** `writeln!` can write fewer bytes
than requested; the callers rely on `io::Write` to report that as an error, and
neither program checks how many bytes reached the file.

## Summary

- `fs::write` replaces contents, `OpenOptions` with `append(true)` adds to them,
  and the difference is the flag rather than a separate function.
- `?` converts an `io::Error` into the caller's error type, which is what lets
  these programs read as a sequence of statements.
- `BufReader` turns many small reads into block reads, and `BufRead` has to be
  imported for `lines` to resolve.
- Relative file names resolve against the working directory, so these programs
  are not independent of where they are started.

## References

- Standard library, [`std::fs`](https://doc.rust-lang.org/std/fs/).
- Standard library, [`OpenOptions`](https://doc.rust-lang.org/std/fs/struct.OpenOptions.html).
- Standard library, [`BufReader`](https://doc.rust-lang.org/std/io/struct.BufReader.html).
- Standard library, [`BufRead::lines`](https://doc.rust-lang.org/std/io/trait.BufRead.html#method.lines).
- Standard library, [`PathBuf`](https://doc.rust-lang.org/std/path/struct.PathBuf.html).
