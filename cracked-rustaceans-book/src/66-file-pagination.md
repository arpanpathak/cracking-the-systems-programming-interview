# 66. Paginating a File with a Byte Cursor {#file-pagination}

*Source file: [`src/bin/file_pagination.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/file_pagination.rs). Run it from the
`rust-interview-lab` directory with `cargo run --bin file_pagination`, so that the relative
path in `main` resolves.*

## Problem Statement

A file holds more records, one per line, than a caller can receive at once. Serve it a page
at a time: each request asks for at most `page_size` lines and gets back those lines
together with a cursor, and passing that cursor to the next request resumes exactly where
the previous page stopped. The last page must say that it is the last, and no request may
read the whole file.

## Designing a Solution

The obvious cursor is a line number, and it is the wrong one. Resuming at line `N` means
reading and discarding `N` lines, so serving the last page of a million-line file costs a
million lines of work, and serving the whole file page by page costs `O(n²)`. A byte offset
costs one `lseek` regardless of how far into the file it points, which makes every page
cost the same.

That choice is what keeps the reader stateless. Nothing is remembered between calls: the
file is opened, the offset is seeked to, the page is read, and the handle is dropped. The
cursor is the entire session, which is what an HTTP API needs when consecutive requests may
land on different processes.

Two details decide whether the cursor is correct. `BufRead::read_line` returns the number
of bytes it consumed, and that count includes the line terminator, so adding it to the
offset gives the position of the next line rather than the position of its newline.
`trim_end` then removes the terminator from the string that is handed back, and does not
touch the count. Conflating the two, by advancing the offset with the trimmed length, moves
the cursor one byte short of each line and repeats a newline on every page boundary.

Reporting the last page needs a look at what comes next without consuming it.
`BufRead::fill_buf` returns the reader's buffer, filling it from the file if it is empty,
and an empty slice means the file is exhausted. Checking it after the loop distinguishes a
final page from a page that merely happens to be full, so the caller stops at the right
moment instead of making one more request that returns nothing.

## Implementation

```rust
use std::fs::File;
use std::io::{self, BufRead, BufReader, Seek, SeekFrom};

struct Page {
    jobs: Vec<String>,
    next_cursor: Option<u64> // Byte offset where the next page starts
}

fn read_page(path: &str, cursor: u64, page_size: usize) -> io::Result<Page> {
    let mut file = File::open(path)?;
    file.seek(SeekFrom::Start(cursor))?;
    let mut reader = BufReader::new(file);

    // Optimization which preserves as large as the max mage size
    let mut jobs: Vec<String> = Vec::with_capacity(page_size);
    let mut offset = cursor;
    let mut line = String::new();
    
    while jobs.len() < page_size {
        // Clear the previously read line
        line.clear();

        match reader.read_line(&mut line)? {
            0 => break, 
            bytes_read => { 
                offset += bytes_read as u64; 
                jobs.push(line.trim_end().to_string()); 
            }, 
        }
    }

    let at_end  = reader.fill_buf()?.is_empty();
    let next_cursor = if at_end  { None } else {Some(offset)};

    Ok(Page { jobs, next_cursor})
}

fn main() -> io::Result<()> {
    let mut cursor = 0;

    loop {
        let page = read_page("src/bin/large_file.txt", cursor, 3)?;

        println!("--- page ---");
        for job in &page.jobs {
            println!("{job}");
        }

        match page.next_cursor {
            Some(next) => cursor = next,
            None => break,
        }
    }

    Ok(())
}
```

`Page` is the return type rather than a tuple, so neither field can be read as the other.
`next_cursor` is an `Option<u64>`, and `None` is the end of the file. An `Option` rather
than a sentinel offset means the caller cannot accidentally continue past the end, because
there is no value to pass.

`read_page` seeks before it wraps the file. The order matters: `File` implements `Seek`,
and `BufReader` starts with an empty buffer, so seeking first and buffering second means
the reader's first fill begins at the cursor. Seeking through the `BufReader` afterwards
would also work, and it discards the buffer to do so.

`Vec::with_capacity(page_size)` sizes the page once, since the exact upper bound is known
before the loop starts. `line.clear()` at the top of each iteration is required rather than
tidy: `read_line` appends to the string it is given, so a string reused without clearing
accumulates the whole page into its first entry.

The `match` on the byte count separates the two outcomes. Zero means end of file, which
ends the loop early and leaves the page short. Any other count is both the evidence that a
line arrived and the amount by which the offset moves, so the same value does both jobs.

`reader.fill_buf()?.is_empty()` is the end-of-file test, and it is a peek rather than a
read: the bytes stay in the reader's buffer, which is then dropped along with the reader.
The cost is at most one extra read of the underlying file per page.

## Intuition

The sample file holds thirteen lines in fifty-eight bytes, and `main` asks for three lines
at a time. The cursor after each page is the offset of the line that has not been read yet:

```text
page   lines                                    bytes consumed   next_cursor
1      "First Line", "Second Line", "Thrid Line"   12 + 12 + 11        35
2      "4", "5", "6"                                2 + 2 + 2          41
3      "7", "8", "9"                                2 + 2 + 2          47
4      "10", "11", "12"                             3 + 3 + 3          56
5      "13"                                             2             None
```

The first line is eleven characters and twelve bytes, because the trailing newline is
counted in the offset and trimmed from the string. The fifth page stops after one line:
`read_line` returns zero, the loop breaks early, and `fill_buf` then confirms the file is
exhausted, so the cursor is `None` and the caller's loop ends. Running the program prints
the five pages:

```text
--- page ---
First Line
Second Line
Thrid Line
--- page ---
4
5
6
--- page ---
7
8
9
--- page ---
10
11
12
--- page ---
13
```

## Time and Space Complexity

| Resource | Cost | Condition |
|---|---|---|
| One page | `O(b)` | `b` bytes in the page; the seek is `O(1)` regardless of the offset |
| The whole file, page by page | `O(n)` | each byte is read once, which a line-number cursor would not achieve |
| Space per call | 8 KiB buffer, plus the page | `BufReader`'s default capacity, allocated and dropped per call |
| Syscalls per page | one `open`, one `lseek`, and `ceil(b / 8192) + 1` reads | the final read is the `fill_buf` peek |

## Limitations

**Every page opens the file and allocates a new buffer.** `File::open` and an 8 KiB
`BufReader` are paid on each call, and the buffer is discarded after serving a few hundred
bytes. A server handling many small pages would keep a pool of open handles, or accept a
`&mut BufReader` from its caller.

**The file may change between pages.** Nothing pins the file's contents, so an offset
recorded for one version of the file can land in the middle of a line of another, and the
first record of the following page is then a fragment. Cursors in a real API carry
something that detects this, such as a generation number or the file's modification time,
and reject a cursor that no longer applies.

**A line has no length limit.** `read_line` grows the string until it meets a newline, so a
file with no newlines allocates its whole length into one `String`, whatever `page_size`
says. `BufRead::take` with a cap, or `read_until` on a bounded buffer, puts a ceiling on it.

**`trim_end` removes more than the terminator.** It strips every trailing whitespace
character, so records ending in a space or a tab come back altered. `trim_end_matches('\n')`
followed by the same for `'\r'` trims exactly the terminator and nothing else.

**Invalid UTF-8 ends the page with an error.** `read_line` requires valid UTF-8 and returns
`InvalidData` otherwise, which `?` propagates, discarding the lines already collected. A
reader over arbitrary bytes uses `read_until(b'\n', &mut Vec<u8>)` and leaves the decoding
to the caller.

**The path is hard-coded and relative.** `main` names `src/bin/large_file.txt`, so the
program only works when run from the `rust-interview-lab` directory. Chapter 29 shows the
argument handling that would replace it.

## Summary

- A byte offset is the right cursor for a file, because seeking to it costs the same
  wherever it points, while a line number makes the last page the most expensive one.
- The offset advances by the count `read_line` returns, which includes the terminator that
  `trim_end` removes from the string.
- `fill_buf` peeks at what follows the page, which is what lets the last page be reported
  as the last one instead of being discovered by an empty request.
- The reader keeps no state between calls, so the cursor alone is enough to resume, and
  nothing prevents the file from changing underneath it.

## References

- Standard library, [`BufRead::read_line`](https://doc.rust-lang.org/std/io/trait.BufRead.html#method.read_line).
- Standard library, [`BufRead::fill_buf`](https://doc.rust-lang.org/std/io/trait.BufRead.html#tymethod.fill_buf).
- Standard library, [`Seek::seek`](https://doc.rust-lang.org/std/io/trait.Seek.html#tymethod.seek)
  and [`SeekFrom`](https://doc.rust-lang.org/std/io/enum.SeekFrom.html).
- Chapter 26, on reading and writing files, and chapter 24, on what a system call costs.
