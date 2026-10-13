//! Command streamsim plays a video the way a streaming player does: 4
//! seconds at a time, choosing the quality of each piece from the speed of
//! the last download. It prints the choice and how much video is buffered.
//!
//! Run it from code/ with:
//!
//!     cargo run -p streamsim

// ANCHOR: choose
/// The qualities the video was encoded in, in kilobits per second.
const QUALITIES: [u32; 4] = [400, 1200, 2500, 5000];

/// The length of one piece of video, in seconds.
const PIECE: f64 = 4.0;

/// The best quality that uses at most 80% of the measured speed. The 20%
/// kept back absorbs a speed that drops during the next download.
fn choose(speed: u32) -> u32 {
    QUALITIES
        .iter()
        .copied()
        .rfind(|&quality| f64::from(quality) <= 0.8 * f64::from(speed))
        .unwrap_or(QUALITIES[0])
}
// ANCHOR_END: choose

// ANCHOR: play
fn main() {
    // The speed of the connection during each download, in kilobits per second.
    let speeds = [6000, 6000, 6000, 1500, 1500, 700, 700, 3200, 6000, 6000];
    let mut measured = 1000;
    let mut buffered: f64 = 0.0;
    let mut stalled: f64 = 0.0;

    println!("piece  speed  chosen  download  buffered");

    for (piece, &speed) in speeds.iter().enumerate() {
        let quality = choose(measured);
        let download = PIECE * f64::from(quality) / f64::from(speed);

        // While the piece downloads, the player keeps showing buffered video.
        let played = download.min(buffered);

        stalled += download - played;
        buffered = buffered - played + PIECE;
        measured = speed;

        println!(
            "{:5}  {speed:5}  {quality:6}  {download:6.1} s  {buffered:6.1} s",
            piece + 1
        );
    }

    println!(
        "time without video after the start: {:.1} s",
        stalled - PIECE * 400.0 / 6000.0
    );
}
// ANCHOR_END: play
