# 29. Command-Line Arguments {#command-line-arguments}

*Source file: [`src/bin/command_line_args.rs`](../../rust-interview-lab/src/bin/command_line_args.rs). Run it with
`cargo run --bin command_line_args -- --name ada --count 3 --verbose`.*

## Problem Statement

A command-line tool receives its input as a list of strings from the operating
system. The program has to know where that list starts and ends, which entry is the
name of the program rather than an argument to it, and how to turn the remaining
entries into the options the tool accepts. It also has to report a bad command line
in a way the shell can see, which means a non-zero exit status.

## Designing a Solution

`env::args()` returns an iterator over the arguments as `String`. The first item is
the name the program was invoked with, so the arguments proper begin at index one
and `args().skip(1)` is the boundary between the two.

The program parses three options. `--name` takes a value, `--count` takes a number,
and `--verbose` is a flag. The parser walks the arguments once with an iterator, so
a value option consumes the next item and a flag consumes only itself. It returns
`Result<Options, String>`: every failure is a message that names the argument at
fault, and `main` prints that message and a usage line to standard error before
returning `ExitCode::FAILURE`. A successful run returns `ExitCode::SUCCESS`, so the
exit status is a fact the shell can test.

`main` returns `ExitCode` rather than `()`. The return value is the program's report
to its caller, and the shell reads the status byte and branches on it. Returning
`ExitCode` keeps that decision in `main` instead of in a call to
`std::process::exit`, which would skip the destructors of everything still alive.

The iterator has one failure mode worth knowing. `args()` panics when an argument is
not valid UTF-8. `args_os` yields `OsString` instead and never panics, which is what
a tool that forwards an arbitrary path should use.

## Implementation

```rust
use std::env::args;
use std::process::ExitCode;

/// The options this program understands.
#[derive(Debug, PartialEq)]
struct Options {
    name: String,
    count: u32,
    verbose: bool,
}

impl Default for Options {
    fn default() -> Self {
        Self { name: String::from("world"), count: 1, verbose: false }
    }
}

/// Turn the arguments after the program name into `Options`.
fn parse(arguments: impl IntoIterator<Item = String>) -> Result<Options, String> {
    let mut options = Options::default();
    let mut arguments = arguments.into_iter();

    while let Some(argument) = arguments.next() {
        match argument.as_str() {
            "--name" => {
                options.name = arguments.next().ok_or("--name needs a value")?;
            }
            "--count" => {
                let value = arguments.next().ok_or("--count needs a value")?;
                options.count = value
                    .parse()
                    .map_err(|_| format!("--count needs a number, got {value:?}"))?;
            }
            "--verbose" => options.verbose = true,
            other => return Err(format!("unknown argument {other:?}")),
        }
    }

    Ok(options)
}

fn main() -> ExitCode {
    let options = match parse(args().skip(1)) {
        Ok(options) => options,
        Err(message) => {
            eprintln!("error: {message}");
            eprintln!("usage: command_line_args [--name NAME] [--count N] [--verbose]");
            return ExitCode::FAILURE;
        }
    };

    for index in 0..options.count {
        if options.verbose {
            println!("[{index}] hello, {}", options.name);
        } else {
            println!("hello, {}", options.name);
        }
    }

    ExitCode::SUCCESS
}

#[cfg(test)]
mod tests {
    use super::*;

    fn parse_args(arguments: &[&str]) -> Result<Options, String> {
        parse(arguments.iter().map(|value| value.to_string()))
    }

    #[test]
    fn defaults_apply_when_there_are_no_arguments() {
        assert_eq!(parse_args(&[]).unwrap(), Options::default());
    }

    #[test]
    fn a_value_option_consumes_the_next_argument() {
        let options = parse_args(&["--name", "ada", "--count", "3"]).unwrap();
        assert_eq!(options.name, "ada");
        assert_eq!(options.count, 3);
    }

    #[test]
    fn verbose_is_a_flag() {
        assert!(parse_args(&["--verbose"]).unwrap().verbose);
        assert!(!parse_args(&[]).unwrap().verbose);
    }

    #[test]
    fn a_value_option_without_a_value_is_an_error() {
        assert!(parse_args(&["--name"]).is_err());
        assert!(parse_args(&["--count"]).is_err());
    }

    #[test]
    fn a_non_numeric_count_is_an_error() {
        assert!(parse_args(&["--count", "many"]).is_err());
    }

    #[test]
    fn an_unknown_argument_is_an_error() {
        assert!(parse_args(&["--colour", "red"]).is_err());
        assert!(parse_args(&["extra"]).is_err());
    }
}
```

The listing is the whole file. Taken in order:

- `parse` accepts any iterator of `String`, so the tests can pass a slice and `main`
  can pass `args().skip(1)`. The argument is not collected into a `Vec` first, so a
  value is consumed exactly when the parser reaches it.
- `--name` and `--count` both call `arguments.next()`. When the iterator is
  exhausted they receive `None`, and `ok_or` turns that into the message
  `--name needs a value`. A flag that silently accepted a missing value would hide a
  typo.
- `--count` parses with `value.parse()`. `map_err` replaces the parser's error with
  one that quotes the offending text, because the caller needs to know which word
  was not a number.
- The final arm catches every other argument, including a stray positional one, and
  returns an error. An unknown option is a failure rather than something ignored, so
  a misspelled flag does not silently do nothing.
- `main` returns `ExitCode`. On success the loop prints `count` greetings, and
  `--verbose` prefixes each line with its index.

The `Default` implementation gives the program the values it uses when an option is
absent. Defaults live in one place, so the parser only writes a field when the
command line supplies one.

## Intuition

With no arguments, the defaults apply:

```text
$ cargo run --bin command_line_args
hello, world
```

With the options:

```text
$ cargo run --bin command_line_args -- --name ada --count 3 --verbose
[0] hello, ada
[1] hello, ada
[2] hello, ada
```

A bad command line goes to standard error and sets the exit status:

```text
$ cargo run --bin command_line_args -- --count many
error: --count needs a number, got "many"
usage: command_line_args [--name NAME] [--count N] [--verbose]
$ echo $?
1
```

`cargo run` passes everything after a bare `--` to the program, which is why the
examples use it. Without the separator, `cargo` would treat `--name` as one of its
own flags.

The process receives its arguments after the shell has removed quoting and
performed expansion. `--name "two words"` arrives as one element, and `*` arrives
already expanded by the shell, so the program never sees the command line as a
single string.

## Time and Space Complexity

| Operation | Cost | Condition |
|---|---|---|
| `env::args()` | no allocation until an item is taken | each item is a `String` when produced |
| `parse` | `O(n)` time | one pass, one `next()` per option and value |
| `skip(1)` | `O(1)` | it drops the first item of the iterator |
| memory | `O(1)` beyond the strings already produced | the parser keeps no list of its own |

Collecting into a `Vec<String>` would cost one allocation per argument plus the
vector, and it would hold the whole command line at once. The parser avoids both,
because it only ever needs the current argument and, for a value option, the one
after it.

## Limitations

**Only the separated form is accepted.** `--name ada` is an option and its value;
`--name=ada` is an unknown argument, because the match is on the whole word.
Accepting the second form means splitting each argument at its first `=` before the
match.

**There is no `--` separator of its own.** The program does not treat a bare `--` as
the end of the options, so a value that begins with `--` cannot be passed as a name
except by changing the parser.

**There is no help flag.** `--help` is reported as an unknown argument. A tool that
ships to other people usually answers `--help` with the usage line and the exit
status for success, rather than with the failure path.

**`args()` panics on a non-UTF-8 argument.** On Unix an argument is a byte string,
and a file name that is not valid UTF-8 reaches the program as bytes. A program
that must accept such a name has to use `args_os` and handle `OsString`.

**The program name is not the same as the executable.** The first argument is
whatever the caller passed as `argv[0]`, which is the path used to invoke the
program and can be changed by the caller. It is not a reliable source of the
program's location.

**Precedence between sources is not implemented.** A flag over an environment
variable over a file over a default is the usual order, and a tool that reads more
than one source has to state that order somewhere. This parser has one source.

## Summary

- `env::args()` yields `String` values whose first item is the invocation name;
  `skip(1)` is the boundary between the program and its arguments.
- The parser walks the arguments once with an iterator, so a value option consumes
  the next item and a flag consumes only itself.
- Every failure returns a message that names the argument at fault, and `main` turns
  it into standard error plus `ExitCode::FAILURE`.
- `args()` panics on non-UTF-8 input, and `args_os` is the version that does not.

## References

- Standard library, [`std::env::args`](https://doc.rust-lang.org/std/env/fn.args.html).
- Standard library, [`std::env::args_os`](https://doc.rust-lang.org/std/env/fn.args_os.html).
- Standard library, [`std::process::ExitCode`](https://doc.rust-lang.org/std/process/struct.ExitCode.html).
- The Rust Book, [Accepting command line arguments](https://doc.rust-lang.org/book/ch12-01-accepting-command-line-arguments.html).
