# What an Abstraction Costs {#what-an-abstraction-costs}

## A field that costs nothing

The repository's singly linked list stores its successor as
`Option<Box<ListNode>>`. On a target with 64-bit addresses that field is eight
bytes wide, which is the width of a bare `Box<ListNode>` in the same position. The
`Option` wrapper adds no tag byte, no padding and no second word: a boxed value is
never null, so the all-zero address is available to encode the empty case.

Change one word of that type and the result changes. `Option<u32>` occupies eight
bytes, against four for a `u32` on its own. Every `u32` bit pattern is a legal
`u32`, so no encoding is free for the empty case, and the compiler adds a four-byte
tag which alignment then rounds up to eight.

```text
type                 size    alignment   why
Box<ListNode>          8         8       one pointer
Option<Box<ListNode>>  8         8       the null pointer is the empty case
u32                    4         4       one word
Option<u32>            8         4       no spare encoding, so a tag is added
&[i32]                16         8       a pointer and a length
Vec<u32>              24         8       a pointer, a length, and a capacity
```

These figures are for a 64-bit target and were produced by a program run on the
machine that built this book. They are not properties of the language. On a 32-bit
target each pointer is four bytes and every number above changes. What survives
the change of target is the reason in the last column: the layout follows from
whether the type has an unused bit pattern, and that is a property of the type.

A design question as ordinary as whether a field should be `Option<u32>` or
`Option<NonZeroU32>` therefore has a measurable answer, and the answer is four
bytes per value. The linked list receives the free version because it stores a
pointer. The `MinStack` pays the tagged version twice, in two `Vec<i32>` fields,
and pays nothing for the option, because `Vec` expresses emptiness through its
length.

## Four budgets

An abstraction spends from one of four budgets, and a claim about overhead is
meaningless until it names which one.

| Budget | Measured in | Typical mechanism that spends it |
|---|---|---|
| Instructions | cycles per operation | one indirect call per element through a trait object |
| Memory | bytes per value, bytes per live object | a tag byte added to an enumeration, an entry per access in a log |
| Stack | bytes per frame, frames per call | recursion whose depth follows the input |
| Compilation | seconds per build, bytes per artefact | one copy of a generic function per set of type arguments |

The four budgets are not interchangeable. An abstraction can be free in
instructions and expensive in memory, which is what the linked list is, and it can
be free in memory and expensive in instructions, which is what a boxed iterator
is.

## What the compiler removes

The mechanism behind most zero-cost claims is monomorphisation. The *Rust Book*
defines it as "the process of turning generic code into specific code by filling
in the concrete types that are used when compiled", and the consequence is
mechanical: a generic function with one call site compiles to one function, which
the optimiser can then inline into its caller.

The repository relies on this throughout. `map_order<T, R, F>` in Chapter 21 takes
a closure as a type parameter, so the pool's worker loop contains a direct call to
the caller's closure rather than an indirect call through a function pointer, and
the body of the closure can be optimised in place. The iterator chains in the
search chapter compile to loops because `Map`, `Copied` and `Filter` are types,
each named at its call site.

The same mechanism accounts for the fourth budget. Monomorphisation is paid for
with code: a generic function with forty call sites containing forty different
types produces forty copies of the compiled function. In a large program that
appears as build time and binary size, and the trade is real enough that the
standard library itself avoids generic instantiation in a few places for this
reason.

## What it cannot remove

Four things survive every optimisation level.

A bounds check on an index that the optimiser cannot prove is in range remains in
the generated code. So does a `match` on a discriminant, a pointer chase through a
box, and the unwinding tables that a reachable `panic!` requires.

Type erasure removes the ability to inline. Replacing a concrete type with `dyn`
turns each call into a load of an address from a vtable followed by an indirect
call, and the optimiser loses the body it would have inlined. The cost is per call
rather than per program, so it depends on how often the call occurs.

Work that leaves the process cannot be optimised at all. The system call
measurement in Chapter 24 is the clearest example in the book: ten million calls
to `getpid` take 2.076 seconds on the machine that ran them, or 207.6 nanoseconds
per call, and no amount of inlining affects that figure, because the time is spent
in the kernel.

## Conditional bounds

Where a bound holds only under an assumption, the assumption is stated beside it.
The expected constant-time lookup of a hash map is the standard case: it holds
while the hash function distributes keys evenly, and the standard library's
default hasher is randomly seeded so that an attacker cannot choose the keys that
break the assumption. A program that installs its own hasher gives that up, and the
bound becomes a hope.

Two kinds of number appear in the chapters that follow. Facts about the language or
the standard library are stated as facts and cited, with the release attached where
a function was stabilised in a particular version. Measurements state the machine
that produced them, because a measurement without its environment cannot be
checked. The two kinds are not interchangeable.

## References

- The Rust Book, [Performance of code using generics](https://doc.rust-lang.org/book/ch10-01-syntax.html#performance-of-code-using-generics), on monomorphisation.
- The Rust Book, [Using trait objects that allow for values of different types](https://doc.rust-lang.org/book/ch17-02-trait-objects.html), on dynamic dispatch.
- The Rust Reference, [Type layout](https://doc.rust-lang.org/reference/type-layout.html), on size, alignment, and the niche optimisation.
- Standard library, [`std::mem::size_of`](https://doc.rust-lang.org/std/mem/fn.size_of.html) and [`std::mem::align_of`](https://doc.rust-lang.org/std/mem/fn.align_of.html).
- Standard library, [`HashMap`](https://doc.rust-lang.org/std/collections/struct.HashMap.html), on the randomly seeded default hasher.
