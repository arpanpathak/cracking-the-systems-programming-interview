# 29. Command-Line Arguments {#command-line-arguments}

*Source file: [`src/bin/command_line_args.rs`](../../rust-interview-lab/src/bin/command_line_args.rs). Run it with
`cargo run --bin command_line_args`.*

## Problem Statement

A command-line tool receives its input as a list of strings from the operating
system. The program has to know where that list starts and ends, and which entry
is the name of the program rather than an argument to it.

## Designing a Solution

`env::args()` returns an iterator over the arguments as `String`. The first item
is the name the program was invoked with, so the arguments proper begin at index
one. `env::args().skip(1)` is the shortest way to drop it, and `collect` turns
the rest into a `Vec<String>` when a program needs random access or a length.

The iterator has one failure mode worth knowing: `args()` panics when an argument
is not valid UTF-8. `args_os` yields `OsString` instead and never panics, which is
what a tool that forwards an arbitrary path should use.

The file in this chapter stops after collecting the arguments. The binding is
never read, so the compiler reports an unused variable. That warning is the
subject of the Limits section: the file is the start of an argument parser rather
than a finished one.

## Implementation

```rust
use std::env::args;

fn main() {
    let args: Vec<String> = args().collect();

    

}
```

`args()` is called rather than imported as a value, and the `Vec<String>`
annotation is what fixes the type of the collection. The first element is the
program name; every argument follows it. Because the binding is not read, the
compiler emits `unused variable: 'args'`, which is reported at the binding rather
than at run time.

## Intuition

Invoked as `cargo run --bin command_line_args alpha beta`, the process receives:

```text
index   value
0       "target/debug/command_line_args"
1       "alpha"
2       "beta"

collect() builds ["target/debug/command_line_args", "alpha", "beta"]
skip(1) would build ["alpha", "beta"]
```

The shell removes the quoting and performs its own expansion before the process
starts, so the program never sees the command line as one string. An argument
written as `"two words"` arrives as a single element, and `*` arrives already
expanded by the shell.

## Time and Space Complexity

| Operation | Cost | Condition |
|---|---|---|
| `env::args()` | no allocation until an item is taken | each item is a `String` when produced |
| `collect` into `Vec<String>` | one allocation per argument plus the vector | the whole argument list is held at once |
| `skip(1)` | `O(1)` time | it drops the first item of the iterator |

## Limitations

**The file collects the arguments and does not use them.** The unused-variable
warning is the compiler reporting that the program is incomplete. Nothing here
validates the number of arguments, reads a flag, or chooses an exit status.

**There is no exit status.** `main` returns `()`, so the process always exits
with the status for success. A tool that fails should return the failure, either
by returning a `Result` from `main` or by calling `std::process::exit`.

**`args()` panics on a non-UTF-8 argument.** On Unix an argument is a byte
string, and a file name that is not valid UTF-8 reaches the program as bytes. A
program that must accept such a name has to use `args_os` and handle `OsString`.

**The program name is not the same as the executable.** The first argument is
whatever the caller passed as `argv[0]`, which is the path used to invoke the
program and can be changed by the caller. It is not a reliable source of the
program's location.

**There is no parsing of flags, values, or defaults.** Splitting `--name value`
into a key and a value, distinguishing `-o json`, and applying the precedence of
a flag over an environment variable over a file over a default are all absent.

## Summary

- `env::args()` yields `String` values whose first item is the invocation name;
  `skip(1)` is the boundary between the program and its arguments.
- `args()` panics on non-UTF-8 input, and `args_os` is the version that does not.
- Collecting the arguments costs one allocation per argument, which is the point
  at which a program has to decide whether it needs them all at once.
- The file is a starting point, not a parser: it neither validates its input nor
  reports a status.

## References

- Standard library, [`std::env::args`](https://doc.rust-lang.org/std/env/fn.args.html).
- Standard library, [`std::env::args_os`](https://doc.rust-lang.org/std/env/fn.args_os.html).
- Standard library, [`std::process::exit`](https://doc.rust-lang.org/std/process/fn.exit.html).
- The Rust Book, [Accepting command line arguments](https://doc.rust-lang.org/book/ch12-01-accepting-command-line-arguments.html).
