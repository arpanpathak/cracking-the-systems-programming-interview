# 39. A Bump Allocator {#bump-allocator}

*Source file: [`src/problems/bump_allocator.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/bump_allocator.rs). Test it with `cargo test bump_allocator`.*

## Problem Statement

Given a buffer of `capacity` bytes, implement `alloc(size, align)` that returns a
mutable slice of `size` bytes whose start is a multiple of `align`, or `None` when the
request does not fit. Individual allocations are never freed; `reset` makes the whole
buffer available again. A failed allocation must leave the arena unchanged.

## Designing a Solution

The arena keeps one integer, `offset`, the index of the first unused byte. An
allocation rounds `offset` up to the next multiple of `align`, checks that `size`
bytes fit after that point, and moves `offset` past them. The diagram below shows two
allocations.

```text
alloc(1, 8)     offset 0 is already a multiple of 8; bytes [0, 1) are returned
                offset = 1

alloc(4, 16)    align_up(1, 16) = 16; bytes [16, 20) are returned
                offset = 20; bytes [1, 16) are padding and are never handed out

 0   1               16   20                                      64
 [a][ padding ....... ][bbbb][ free ................................ ]
```

Rounding up to a power of two does not need division. For `align = 2^k`, the mask
`align - 1` has the low `k` bits set. Adding the mask and then clearing those bits
gives the smallest multiple of `align` that is not less than the original offset:

```text
align_up(offset, align) = (offset + (align - 1)) & !(align - 1)

align_up(1, 16)  = (1 + 15)  & !15 = 16 & ...11110000 = 16
align_up(16, 16) = (16 + 15) & !15 = 31 & ...11110000 = 16
align_up(17, 16) = (17 + 15) & !15 = 32 & ...11110000 = 32
```

The only arithmetic that can overflow is `offset + mask` and `start + size`. Both use
`checked_add`, and an overflow is reported as `None` like any other request that does
not fit.

## Implementation

<p class="listing"><span class="listing-label">Listing 39.1</span> <code>BumpArena</code>, <code>with_capacity</code>, and <code>alloc</code>. <code>src/problems/bump_allocator.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/bump_allocator.rs">read the file on GitHub</a></p>

`alloc` returns `Option<&mut [u8]>`. The slice borrows the arena mutably, so the caller
must finish using one allocation before requesting another. That restriction is what
makes the function safe without `unsafe`: two live allocations would be two mutable
borrows of the same `Vec`, which the borrow checker rejects. A production arena lifts
the restriction by handing out raw pointers or by using interior mutability, and it
then needs `unsafe` code to justify that the regions do not overlap.

The order of the statements in `alloc` implements the "failed allocation changes
nothing" requirement. `start` and `end` are computed and checked first, and
`self.offset = end` is the only write, performed after every check has passed.

`align_up` returns `Option<usize>` so that an offset near `usize::MAX` cannot wrap to a
small value and appear to fit. `map(|value| value & !mask)` applies the mask only when
the addition succeeded.

`reset` sets the cursor to zero and does not clear the bytes, so an allocation made
after a reset can see data written before it. Only a fresh arena is guaranteed to be
zeroed, by `vec![0; capacity]`, and the test `writes_are_isolated_between_allocations`
depends on that.

The next listing shows the tests.

<p class="listing"><span class="listing-label">Listing 39.2</span> The tests for the module. <code>src/problems/bump_allocator.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/bump_allocator.rs">read the file on GitHub</a></p>

`writes_are_isolated_between_allocations` reads `arena.buffer` directly. The test module
is a child of the module that defines `BumpArena`, so it can see the private field. The
test ends the borrow of `second` before it borrows `arena.buffer`, which is why
`second` is not used after `copy_from_slice`.

## Intuition

**`allocations_are_aligned` on a 64-byte arena**

| call | `offset` before | `start = align_up(offset, align)` | `end` | `offset` after | `remaining` |
|---|---|---|---|---|---|
| `alloc(1, 8)` | 0 | 0 | 1 | 1 | 63 |
| `alloc(4, 16)` | 1 | 16 | 20 | 20 | 44 |

**`exhaustion_returns_none_and_keeps_state` on a 16-byte arena**

| call | `start` | `end` | `end > 16`? | result | `offset` after |
|---|---|---|---|---|---|
| `alloc(16, 1)` | 0 | 16 | no | `Some(16 bytes)` | 16 |
| `alloc(1, 1)` | 16 | 17 | yes | `None` | 16, unchanged |

A zero-sized allocation at offset 0 with alignment 8 returns an empty slice and leaves
`offset` at 0. A zero-sized allocation at offset 1 with alignment 8 would move the
cursor to 8 and consume seven bytes of padding for an allocation of no bytes.

## Time and Space Complexity

| Operation | Time | Space |
|---|---|---|
| `with_capacity` | `O(capacity)`, to zero the buffer | `capacity` bytes |
| `alloc` | `O(1)` | none beyond the buffer; padding is lost until `reset` |
| `reset` | `O(1)` | none |

Internal fragmentation is bounded by `align - 1` bytes per allocation. There is no
external fragmentation, because nothing is freed individually.

## Limitations

**The allocator aligns offsets, not addresses.** `alloc(size, 8)` returns a slice that
starts at an offset divisible by 8 from the start of the buffer. The returned pointer
is divisible by 8 only if the buffer's own address is. `Vec<u8>` has an alignment of
1, and nothing in the type guarantees that its heap block is aligned to 8 or 16. The
test `allocations_are_aligned` passes because the system allocator on common
platforms returns blocks aligned to at least 16 bytes. An arena intended to store
typed values needs to allocate its buffer with `std::alloc::alloc` and a `Layout` of
the maximum alignment it will serve, or align relative to the address rather than the
offset.

**One allocation at a time.** The `&mut [u8]` return value prevents holding two
allocations simultaneously, which is the normal use of an arena. The type is a correct
model of the arithmetic and not yet a usable allocator.

**Bytes, not values.** `alloc` returns bytes. Placing a `T` in them requires `unsafe`
code, and dropping that `T` requires the arena to remember to run its destructor,
which a bump allocator does not do. Crates such as `bumpalo` address both problems.

**`reset` does not zero.** Memory handed out after a reset contains whatever the
previous cycle wrote. For byte buffers that are always written before they are read
this is acceptable; for anything else it is a source of stale data.

**`align` is checked with `assert!`.** A non-power-of-two alignment panics rather than
returning `None`. The caller controls the alignment, so a panic reports a programming
error rather than a runtime condition, which is a reasonable choice, and it should be
documented as such.

## Summary

- A bump allocator is a buffer and a cursor. Allocation rounds the cursor up to the
  requested alignment and advances it; `reset` frees everything at once.
- For a power-of-two alignment, `(offset + align - 1) & !(align - 1)` rounds up
  without division.
- `checked_add` on both additions turns arithmetic overflow into an ordinary failed
  allocation, and writing `offset` only after every check keeps a failure side-effect
  free.
- Returning `&mut [u8]` keeps the code safe and limits the caller to one live
  allocation.
- Aligning an offset inside a `Vec<u8>` does not align the address; a real arena
  allocates its buffer with the alignment it intends to serve.

## References

- Standard library, [`std::alloc::Layout`](https://doc.rust-lang.org/std/alloc/struct.Layout.html).
- Standard library, [`usize::is_power_of_two`](https://doc.rust-lang.org/std/primitive.usize.html#method.is_power_of_two) and [`usize::checked_add`](https://doc.rust-lang.org/std/primitive.usize.html#method.checked_add).
- The `bumpalo` crate, [documentation](https://docs.rs/bumpalo/latest/bumpalo/).
- The Rust Reference, [Type layout](https://doc.rust-lang.org/reference/type-layout.html), on size and alignment.
