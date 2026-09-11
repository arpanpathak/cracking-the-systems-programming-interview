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
