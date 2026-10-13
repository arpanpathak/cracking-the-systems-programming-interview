//! Command shortener compares 2 ways of making a short code for a URL: the
//! next number of a counter written in base 62, and the first characters of
//! a hash. It counts how often each gives 2 URLs the same code.
//!
//! Run it from code/ with:
//!
//!     cargo run --release -p shortener

// ANCHOR: imports
use std::collections::HashSet;
use std::iter;

use xxhash_rust::xxh3::xxh3_64;
// ANCHOR_END: imports

// ANCHOR: base62
const DIGITS: &[u8] = b"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";

/// Writes a number in base 62.
fn encode(number: u64) -> String {
    // The number after each division by 62, until nothing is left. The
    // remainder of each is 1 digit, starting with the last digit of the code.
    let mut code: Vec<u8> =
        iter::successors(Some(number), |&rest| (rest >= 62).then_some(rest / 62))
            .map(|rest| DIGITS[(rest % 62) as usize])
            .collect();

    code.reverse();

    String::from_utf8_lossy(&code).into_owned()
}

/// Reads a code back into its number, or `None` for a character that is
/// not a digit of base 62.
fn decode(code: &str) -> Option<u64> {
    code.bytes()
        .try_fold(0u64, |number, byte| {
            let digit = DIGITS
                .iter()
                .position(|&digit| digit == byte)?;

            Some(number * 62 + digit as u64)
        })
}
// ANCHOR_END: base62

// ANCHOR: main
fn main() {
    for number in [0, 61, 62, 1_000_000, 3_521_614_606_207] {
        let code = encode(number);

        println!("{number:>14} -> {code:<8} -> {:?}", decode(&code));
    }

    let urls = 2_000_000u64;
    let url = |number: u64| format!("https://example.com/page/{number}");

    // Codes from a counter: every URL receives the next number.
    let counted: HashSet<String> = (0..urls).map(encode).collect();

    // Codes from a hash: the first 6 characters of the hash in base 62.
    let hashed: HashSet<String> = (0..urls)
        .map(|number| encode(xxh3_64(url(number).as_bytes())))
        .map(|code| code[..6].to_owned())
        .collect();

    println!(
        "{urls} URLs, codes from a counter: {} collisions",
        urls as usize - counted.len()
    );
    println!(
        "{urls} URLs, 6 characters of a hash: {} collisions",
        urls as usize - hashed.len()
    );
    println!("codes of 7 characters: {} possible", 62u64.pow(7));
}
// ANCHOR_END: main
