# 51. IPv4 Addresses and TCP Windows {#ipv4-and-tcp-windows}

*Source files: [`src/bin/net_ipv4.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/net_ipv4.rs) and [`src/bin/net_window.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/net_window.rs). Run them with `cargo run --bin net_ipv4` and `cargo run --bin net_window`.*

## Problem Statement

1. Parse text such as `192.168.1.10` into four octets, rejecting anything that is not
   exactly four values in `0..=255`. Report whether the address is in one of the private
   ranges, and convert it to and from the 32-bit integer carried in an IP header.
2. Given a receiver window and a congestion window, compute how much unacknowledged data
   a TCP sender may have in flight. Given a link's bandwidth and round-trip time, compute
   how many bytes must be in flight to keep the link busy.

## Designing a Solution

**Parsing.** Split the text on `.`, parse each part as `u8`, and require exactly four
parts. Parsing as `u8` rejects values above 255 without a separate range check.

**Private ranges.** RFC 1918 reserves three blocks for private networks:

```text
10.0.0.0/8        first octet 10
172.16.0.0/12     first octet 172, second octet 16 through 31
192.168.0.0/16    first octets 192, 168
```

Each block is a condition on a prefix of the octets, which a slice pattern expresses
directly.

**Byte order.** Protocol headers carry multi-byte integers most significant byte first,
known as big-endian or network byte order. The address `127.0.0.1` is the integer
`0x7f000001`, stored in a header as the bytes `7f 00 00 01` whatever the host's own byte
order.

**Windows.** A TCP sender limits unacknowledged data to the smaller of two windows: the
receiver's advertised window, which protects the receiver's buffer, and the congestion
window, which the sender maintains to avoid overloading the network.

**Bandwidth-delay product.** A sender can release new data only as acknowledgements
return, and they return one round-trip time after the data left. To keep a link of
bandwidth `B` bytes per second busy, the sender must have `B × RTT` bytes in flight at
all times. If the effective window is smaller than that product, the link sits partly
idle regardless of its bandwidth.

## Implementation

```rust
//! IPv4 addresses: parse a dotted quad, check the private ranges, and show the
//! network byte order used on the wire.
//!
//! Run with: cargo run --bin net_ipv4

/// Parse `a.b.c.d`, rejecting anything that is not exactly four octets.
fn parse(input: &str) -> Option<[u8; 4]> {
    let mut parts = input.split('.').map(|part| part.parse::<u8>().ok());
    let address = [
        parts.next()??,
        parts.next()??,
        parts.next()??,
        parts.next()??,
    ];
    parts.next().is_none().then_some(address)
}

/// `10.0.0.0/8`, `172.16.0.0/12`, and `192.168.0.0/16` are not routable on the
/// public internet.
fn is_private(address: [u8; 4]) -> bool {
    matches!(address, [10, ..] | [172, 16..=31, ..] | [192, 168, ..])
}

/// Addresses travel big-endian, so the first octet is the most significant byte.
fn to_network_order(address: [u8; 4]) -> u32 {
    u32::from_be_bytes(address)
}

fn from_network_order(value: u32) -> [u8; 4] {
    value.to_be_bytes()
}

fn main() {
    println!(
        "{:<16} {:<18} {:>8} {:>12}",
        "input", "parsed", "private", "as u32"
    );

    for text in [
        "10.0.0.1",
        "172.16.5.4",
        "192.168.1.10",
        "8.8.8.8",
        "256.1.1.1",
        "1.2.3",
    ] {
        match parse(text) {
            Some(address) => println!(
                "{text:<16} {:<18} {:>8} {:>12}",
                format!("{address:?}"),
                is_private(address),
                to_network_order(address)
            ),
            None => println!("{text:<16} invalid"),
        }
    }

    assert_eq!(parse("10.0.0.1"), Some([10, 0, 0, 1]));
    assert_eq!(parse("1.2.3"), None);
    assert_eq!(parse("1.2.3.4.5"), None);
    assert_eq!(parse("256.0.0.1"), None);

    assert!(is_private([10, 1, 2, 3]));
    assert!(is_private([172, 31, 0, 1]));
    assert!(!is_private([172, 32, 0, 1]));
    assert!(!is_private([8, 8, 8, 8]));

    assert_eq!(to_network_order([127, 0, 0, 1]), 0x7f00_0001);
    assert_eq!(from_network_order(0x7f00_0001), [127, 0, 0, 1]);

    println!("\nall checks passed");
}
```

`parse` maps each part to `part.parse::<u8>().ok()`, so the iterator yields
`Option<Option<u8>>`: the outer `Option` says whether a part exists, and the inner one
whether it parsed. `parts.next()??` applies `?` twice, returning `None` from the function
if either layer is `None`. Four such expressions build the array, and
`parts.next().is_none().then_some(address)` rejects a fifth part.

`is_private` uses slice patterns on the array. `[10, ..]` matches any address whose
first octet is 10. `[172, 16..=31, ..]` matches a first octet of 172 and a second in the
inclusive range, which is exactly the `/12` block. The `|` combines the three patterns
in one `matches!`.

`u32::from_be_bytes(address)` interprets the array as a big-endian integer, and
`value.to_be_bytes()` performs the inverse. Both are `const fn` and compile to a byte
swap on little-endian processors and to nothing on big-endian ones.

```rust
//! TCP window math: the effective window is the smaller of the receiver and
//! congestion windows, and the bandwidth-delay product is how many bytes must be
//! in flight to fill a link.
//!
//! Run with: cargo run --bin net_window

/// The sender may have this much unacknowledged data in flight.
fn effective_window(receive: u32, congestion: u32) -> u32 {
    receive.min(congestion)
}

/// Bytes in flight needed to keep a link busy: bandwidth times round-trip time.
fn bandwidth_delay_product(bytes_per_second: u64, rtt_millis: u64) -> u64 {
    bytes_per_second * rtt_millis / 1_000
}

fn main() {
    println!("effective window = min(receiver window, congestion window)");
    for (receive, congestion) in [(64_000, 16_000), (16_000, 64_000), (32_000, 32_000)] {
        println!(
            "  receiver {receive:>7} B, congestion {congestion:>7} B -> {:>7} B",
            effective_window(receive, congestion)
        );
    }

    println!("\nbandwidth-delay product (bytes needed in flight)");
    for (rate, rtt) in [(1_000_000, 1), (10_000_000, 50), (1_000_000_000, 100)] {
        println!(
            "  {:>12} B/s x {rtt:>3} ms -> {:>12} B",
            rate,
            bandwidth_delay_product(rate, rtt)
        );
    }

    // A window smaller than the product leaves the link idle, no matter how much
    // bandwidth is available. This is why latency, not only bandwidth, matters.
    let product = bandwidth_delay_product(1_000_000_000, 100);
    let window = u64::from(effective_window(64_000, 1_000_000));
    println!(
        "\nwindow {window} B vs product {product} B: link is {} the window too small",
        if window < product {
            "starved,"
        } else {
            "usable,"
        }
    );

    assert_eq!(effective_window(64_000, 16_000), 16_000);
    assert_eq!(effective_window(16_000, 64_000), 16_000);
    assert_eq!(bandwidth_delay_product(10_000_000, 50), 500_000);
    assert!(window < product);

    println!("\nall checks passed");
}
```

`effective_window` is `receive.min(congestion)`. `bandwidth_delay_product` multiplies
before dividing, `bytes_per_second * rtt_millis / 1_000`, so that integer division does
not discard the fractional part of the round-trip time in seconds.

`u64::from(effective_window(...))` widens the `u32` window before comparing it with the
`u64` product. `From` is used rather than `as` because it cannot truncate.

## Intuition

The IPv4 program prints:

```text
input            parsed              private       as u32
10.0.0.1         [10, 0, 0, 1]          true    167772161
172.16.5.4       [172, 16, 5, 4]        true   2886731012
192.168.1.10     [192, 168, 1, 10]      true   3232235786
8.8.8.8          [8, 8, 8, 8]          false    134744072
256.1.1.1        invalid
1.2.3            invalid

all checks passed
```

**`parse("1.2.3")`**

| expression | value |
|---|---|
| `parts.next()` for the first three octets | `Some(Some(1))`, `Some(Some(2))`, `Some(Some(3))` |
| fourth `parts.next()` | `None` |
| first `?` on `None` | the function returns `None` |

The window program prints:

```text
effective window = min(receiver window, congestion window)
  receiver   64000 B, congestion   16000 B ->   16000 B
  receiver   16000 B, congestion   64000 B ->   16000 B
  receiver   32000 B, congestion   32000 B ->   32000 B

bandwidth-delay product (bytes needed in flight)
       1000000 B/s x   1 ms ->         1000 B
      10000000 B/s x  50 ms ->       500000 B
    1000000000 B/s x 100 ms ->    100000000 B

window 64000 B vs product 100000000 B: link is starved, the window too small

all checks passed
```

A link of one gigabyte per second with a 100 ms round trip needs 100 MB in flight. A
64 KB window fills 0.064 percent of it. The classic 16-bit TCP window field cannot
express more than 65,535 bytes; RFC 7323 added a window scale option to go beyond it.

## Time and Space Complexity

| Function | Time | Space |
|---|---|---|
| `parse` | `O(len)` | none |
| `is_private`, `to_network_order`, `from_network_order` | `O(1)` | none |
| `effective_window`, `bandwidth_delay_product` | `O(1)` | none |

## Limitations

**The parser accepts forms that address parsers reject.** `str::parse::<u8>` accepts a
leading `+` and leading zeros, so `+1.2.3.4` and `010.0.0.1` parse. The second is
especially misleading, because the C function `inet_aton` reads `010` as octal 8.
The standard library's `"10.0.0.1".parse::<std::net::Ipv4Addr>()` rejects both forms.

**The standard library already provides these functions.** `Ipv4Addr` implements
`FromStr`, `Ipv4Addr::is_private` checks the same three blocks, and
`u32::from(Ipv4Addr)` and `Ipv4Addr::from(u32)` perform the byte-order conversion.
Writing the functions by hand is useful in an interview; production code should use the
type.

**`bandwidth_delay_product` can overflow.** `bytes_per_second * rtt_millis` is a `u64`
product. Values large enough to overflow are physically unrealistic, but the function
would panic in a debug build and wrap in a release build. `checked_mul` or `u128`
arithmetic would make the limit explicit.

**The window model is static.** Real congestion windows change on every acknowledgement
and every loss, and the receiver window changes as the application reads. The program
compares two numbers at one instant.

**The final message's wording.** The format string produces
`link is starved, the window too small`, which reads as a sentence fragment; it would
be clearer as two clauses, such as `the window is too small, so the link is starved`.

## Summary

- `part.parse::<u8>().ok()` inside an iterator yields `Option<Option<u8>>`, and `??`
  unwraps both layers or returns `None`.
- Slice patterns with ranges, such as `[172, 16..=31, ..]`, express address blocks
  directly and are checked by the compiler.
- `u32::from_be_bytes` and `to_be_bytes` convert between octets and network byte order.
- A TCP sender's effective window is the minimum of the receiver and congestion windows.
- A link is fully used only when the window is at least the bandwidth-delay product,
  which for fast, long links is far larger than 64 KB.
- `std::net::Ipv4Addr` provides stricter parsing and the same classification out of the
  box.

## References

- RFC 1918, *Address Allocation for Private Internets*, 1996.
- RFC 7323, *TCP Extensions for High Performance*, 2014, on window scaling.
- W. Richard Stevens, Bill Fenner, and Andrew M. Rudoff, *UNIX Network Programming,
  Volume 1*, 3rd edition, Addison-Wesley, 2003, Chapter 35, on byte-ordering functions.
- Standard library, [`std::net::Ipv4Addr`](https://doc.rust-lang.org/std/net/struct.Ipv4Addr.html) and [`u32::from_be_bytes`](https://doc.rust-lang.org/std/primitive.u32.html#method.from_be_bytes).
