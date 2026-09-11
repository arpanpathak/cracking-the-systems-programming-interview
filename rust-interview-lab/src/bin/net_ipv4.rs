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
