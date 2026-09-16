# 35. Types That Reject Invalid Values {#adt-idioms}

*Source file: [`src/problems/adt_idioms.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/adt_idioms.rs). Test it with `cargo test adt_idioms`.*

## Problem Statement

A command-line client for a GPU service accepts four commands, one per line:

```text
list
get <id>
create <name> <gpu-count>
delete <id>
```

A GPU count must be an integer from 1 to 64. The parser must turn a line into a value
the rest of the program can use without checking it again, and it must report each
kind of malformed input in a way a caller can distinguish: an empty line, an unknown
verb, a missing argument, and a count that is not a number or is out of range.

## Designing a Solution

The obvious representation is a `String` for the verb, an `Option<String>` for each
argument, and a `u32` for the count. Every function that receives those values would
have to re-check them, because nothing in the types says that a `create` has a name or
that the count is in range. Three types remove the re-checking.

**A newtype for the count.** `struct GpuCount(u32)` is a distinct type whose only
constructor validates the range. Code that receives a `GpuCount` knows the value is
between 1 and 64 without looking at it, and a raw `u32` cannot be passed where a
`GpuCount` is expected.

**An enumeration for the command.** Each variant carries exactly the fields its
command needs. `Command::List` has none, `Command::Get` has an `id`, and
`Command::Create` has a `name` and a `GpuCount`. A `match` on a `Command` must
handle all four variants, and a variant cannot be built without its fields.

**An enumeration for the failure.** `CommandError` names each way a line can be
rejected, and carries the text that caused the rejection. A caller can match on the
variant to decide what to do, and print it through `Display` to tell a user what
happened.

The diagram below shows the flow from text to typed value.

```text
"create triton 4"
       |
       v
 Command::parse ----> Err(CommandError::UnknownVerb | MissingArgument | InvalidGpuCount)
       |
       v
 Ok(Command::Create { name: "triton", gpus: GpuCount(4) })
       |
       v
 the rest of the program: no further checks on name or gpus
```

## Implementation

The module has four parts: the newtype, its error, the command and its error, and a
short iterator example. The first listing shows the newtype.

<p class="listing"><span class="listing-label">Listing 35.1</span> <code>GpuCount</code>, <code>new</code>, and <code>get</code>. <code>src/problems/adt_idioms.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/adt_idioms.rs">read the file on GitHub</a></p>

The tuple field of `GpuCount` is private, so code outside the module cannot write
`GpuCount(0)`. The only ways to obtain a value are `GpuCount::new` and
`GpuCount::try_from`, and both run the range check.

`(Self::MIN..=Self::MAX).contains(&value)` states the valid range once, using the
associated constants that the error message also prints. Changing the limit is a
one-line edit that updates the check and the message together.

`GpuCountError` is itself a newtype. It carries the rejected value, which lets the
`Display` implementation produce a message such as `gpu count 99 is outside 1..=64`.
The empty `impl std::error::Error for GpuCountError {}` is enough to make the type
usable with `?` in a function that returns `Box<dyn Error>`; the trait's methods all
have default implementations.

`TryFrom<u32>` connects the newtype to the standard conversion traits. A caller can
write `GpuCount::try_from(raw)?` or `let gpus: GpuCount = raw.try_into()?`, and
generic code that accepts `T: TryFrom<u32>` works with it. The implementation
delegates to `new`, so there is one validation path. `From<GpuCount> for u32` goes
the other way, and it cannot fail, which is why it is `From` rather than `TryFrom`.

The next listing shows the command type and its parser.

<p class="listing"><span class="listing-label">Listing 35.2</span> <code>Command</code>, <code>parse</code>, and <code>verb</code>. <code>src/problems/adt_idioms.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/adt_idioms.rs">read the file on GitHub</a></p>

`Command::parse` splits the line on whitespace and takes the verb with
`parts.next().ok_or(CommandError::Empty)?`. `ok_or` converts `Option` to `Result`, and
`?` returns the error immediately, so the rest of the function runs only when a verb
exists.

The helper `argument` has the same shape and adds the name of the missing argument to
the error. Its signature is worth reading closely. `parts: &mut impl Iterator<Item =
&'a str>` borrows the iterator mutably, so each call consumes one item from the same
sequence. The lifetime `'a` ties the returned `&str` to the original line, not to the
iterator, which lets `parse` convert it with `to_string` after the call.

The `create` arm distinguishes two failures that produce the same variant. A count
that does not parse as `u32` and a count that parses but is out of range both return
`InvalidGpuCount`, carrying the raw text. The design choice is that the caller cares
about which argument was wrong, not about which check rejected it.

`verb` returns `&'static str` for each variant. The `..` in patterns such as
`Self::Get { .. }` ignores the fields, and the `match` has no wildcard arm, so adding a
fifth command makes this function fail to compile until the new variant is handled.

The next listing shows the last function in the module, which is unrelated to parsing and
illustrates a different idiom.

```rust
/// Count and sum in one pass, without managing an index.
pub fn summarize(values: &[i32]) -> (usize, i64) {
    values.iter().fold((0usize, 0i64), |(count, sum), value| {
        (count + 1, sum + i64::from(*value))
    })
}
```

`fold` carries a tuple of accumulators through the iteration. The count is `usize`
and the sum is `i64`, and each element is widened with `i64::from(*value)`. Widening
before adding means that summing a slice of `i32` values cannot overflow until the
total exceeds the range of `i64`. `From` is used instead of `as` because it compiles
only for conversions that cannot lose information.

The last listing shows the tests. They exercise every variant of `Command`, every variant
of `CommandError`, the boundaries of the newtype, and the rendered messages.

<p class="listing"><span class="listing-label">Listing 35.3</span> The tests for the module. <code>src/problems/adt_idioms.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/adt_idioms.rs">read the file on GitHub</a></p>

## Intuition

The table below follows six inputs through `Command::parse`.

**`Command::parse` on valid and invalid lines**

| input | verb | arguments consumed | result |
|---|---|---|---|
| `"list"` | `list` | none | `Ok(Command::List)` |
| `"get wl-7"` | `get` | `wl-7` | `Ok(Command::Get { id: "wl-7" })` |
| `"create triton 4"` | `create` | `triton`, `4` | `Ok(Command::Create { name: "triton", gpus: GpuCount(4) })` |
| `"create triton 0"` | `create` | `triton`, `0` | `"0"` parses as `0u32`, `GpuCount::new(0)` fails, `Err(InvalidGpuCount("0"))` |
| `"get"` | `get` | none available | `Err(MissingArgument("id"))` |
| `""` | none | none | `Err(Empty)` |

`Command::parse("create triton 0").unwrap_err().to_string()` produces
`invalid gpu count: "0"`. The `{raw:?}` format prints the text with quotes, which makes
trailing whitespace or an empty string visible in the message.

## Time and Space Complexity

| Operation | Time | Space |
|---|---|---|
| `GpuCount::new` | `O(1)` | none; `GpuCount` is the size of a `u32` |
| `Command::parse` | `O(len)` for the line | one `String` per stored argument |
| `verb` | `O(1)` | none |
| `summarize` | `O(n)` | none |

A newtype has no run-time cost. `GpuCount` has the same size and alignment as `u32`,
and its methods compile to the same instructions as the unwrapped code. The type
exists only for the compiler.

## Limitations

**The parser allocates for every argument.** `Command::Get { id: String }` owns its
identifier, so each successful parse copies the argument out of the line. A version
that returns `Command<'a>` with `&'a str` fields would allocate nothing, at the cost
of tying the command's lifetime to the input line.

**Extra arguments are ignored.** `"get wl-7 extra"` parses as `Get { id: "wl-7" }`.
The parser never checks that `parts` is exhausted. Adding
`if parts.next().is_some() { return Err(...) }` after each arm would reject the input,
and it would require a new error variant.

**The two count failures are merged.** `InvalidGpuCount` does not say whether the text
was not a number or the number was out of range. A caller that wants to print "must
be between 1 and 64" for the second case has to parse the text again. Keeping the
`GpuCountError` inside the variant, for example `OutOfRange(GpuCountError)`, would
preserve the information.

**`CommandError::MissingArgument(&'static str)` limits the argument names to string
literals.** This is fine for a fixed grammar and prevents building the name at run
time. It also keeps the error type `Clone` and cheap.

**`summarize` is unrelated to the rest of the module.** It sits here as an example of
an iterator fold. In a real codebase it would live with the code that uses it.

## Summary

- A newtype with a private field and a validating constructor makes an invalid value
  unrepresentable, at no run-time cost.
- `TryFrom` and `From` connect a newtype to the standard conversion traits, so `?` and
  `try_into` work with it.
- An enumeration whose variants carry only the fields they need replaces a bag of
  optional fields, and `match` without a wildcard makes a new variant a compile error
  at every use.
- A typed error enumeration lets a caller branch on the failure, and implementing
  `Display` and `std::error::Error` lets it travel through `?` and `Box<dyn Error>`.
- Widening with `i64::from` before adding avoids overflow, and `From` rejects lossy
  conversions at compile time.

## References

- The Rust Book, [Using the newtype pattern](https://doc.rust-lang.org/book/ch20-02-advanced-traits.html#using-the-newtype-pattern-to-implement-external-traits-on-external-types).
- Rust API Guidelines, [Newtypes provide static distinctions](https://rust-lang.github.io/api-guidelines/type-safety.html#newtypes-provide-static-distinctions-c-newtype).
- Standard library, [`TryFrom`](https://doc.rust-lang.org/std/convert/trait.TryFrom.html).
- Standard library, [`std::error::Error`](https://doc.rust-lang.org/std/error/trait.Error.html).
- Standard library, [`Iterator::fold`](https://doc.rust-lang.org/std/iter/trait.Iterator.html#method.fold).
