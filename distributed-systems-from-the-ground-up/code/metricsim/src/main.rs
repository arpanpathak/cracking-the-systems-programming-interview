//! Command metricsim stores 1 hour of a measurement taken every second. It
//! compares the size of the plain points with the size after encoding each
//! point as its difference from the one before, and then reduces the hour
//! to 1 point for every minute in 2 ways.
//!
//! Run it from code/ with:
//!
//!     cargo run -p metricsim

// ANCHOR: series
/// A point of a time series: when it was measured, in seconds, and the
/// value, here the response time of a service in milliseconds.
#[derive(Clone, Copy)]
struct Point {
    time: i64,
    value: i64,
}

/// 1 hour of response times around 40 ms, with a spike of 3 seconds at
/// minute 20, in which the response time is 900 ms.
fn hour() -> Vec<Point> {
    (0..3600)
        .map(|second| {
            let wobble = (second * 7 % 5) - 2;
            let spike = (1200..1203).contains(&second);

            Point {
                time: 1_760_000_000 + second,
                value: if spike { 900 } else { 40 + wobble },
            }
        })
        .collect()
}
// ANCHOR_END: series

// ANCHOR: encode
/// The bytes a whole number needs when small numbers are written in fewer
/// bytes: 7 bits of the number in each byte.
fn width(number: i64) -> usize {
    // Small negative and small positive numbers are both made small.
    let folded = ((number << 1) ^ (number >> 63)) as u64;
    let bits = (64 - folded.leading_zeros()).max(1) as usize;

    bits.div_ceil(7)
}

/// The bytes of the series when each time is stored as the change of its
/// step from the step before, and each value as its change from the value
/// before.
fn encoded_size(points: &[Point]) -> usize {
    let steps: Vec<i64> = points
        .windows(2)
        .map(|pair| pair[1].time - pair[0].time)
        .collect();
    let times: usize = steps
        .windows(2)
        .map(|pair| width(pair[1] - pair[0]))
        .sum();
    let values: usize = points
        .windows(2)
        .map(|pair| width(pair[1].value - pair[0].value))
        .sum();

    // The first point in full, the first step, then the changes.
    16 + 8 + times + values
}
// ANCHOR_END: encode

// ANCHOR: main
fn main() {
    let points = hour();
    let plain = points.len() * 16;
    let encoded = encoded_size(&points);

    println!("{} points, 1 for every second of an hour", points.len());
    println!("plain, 16 bytes for each point: {plain} bytes");
    println!(
        "each point as its change from the one before: {encoded} bytes, {:.1} bytes for each point",
        encoded as f64 / points.len() as f64
    );

    // The minute that contains the spike, reduced to 1 point in 2 ways.
    let minute = &points[1200..1260];
    let total: i64 = minute
        .iter()
        .map(|point| point.value)
        .sum();
    let average = total / minute.len() as i64;
    let largest = minute
        .iter()
        .map(|point| point.value)
        .max()
        .unwrap_or_default();

    println!("minute 20, kept as its average: {average} ms");
    println!("minute 20, kept as its largest value: {largest} ms");
}
// ANCHOR_END: main
