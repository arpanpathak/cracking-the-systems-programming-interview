// ch19/byte_routines.rs: memmove, strlen, and atoi written by hand.

/// Copies `count` bytes inside `buffer` from `source` to `destination`.
/// The two ranges may overlap. Returns false if either range leaves the buffer.
fn move_bytes(
    buffer: &mut [u8],
    destination: usize,
    source: usize,
    count: usize,
) -> bool {
    let length = buffer.len();

    // The subtraction form cannot overflow, unlike `source + count <= length`.
    let source_fits = source <= length && count <= length - source;
    let destination_fits = destination <= length && count <= length - destination;

    if !source_fits || !destination_fits {
        return false;
    }

    if destination < source {
        for index in 0..count {
            buffer[destination + index] = buffer[source + index];
        }

        return true;
    }

    for index in (0..count).rev() {
        buffer[destination + index] = buffer[source + index];
    }

    true
}

/// Counts the bytes before the first NUL, as C's strlen does.
fn string_length(bytes: &[u8]) -> usize {
    bytes
        .iter()
        .take_while(|&&byte| byte != 0)
        .count()
}

/// Parses an optional sign and decimal digits. Returns None on overflow or no digits.
fn parse_int(text: &str) -> Option<i32> {
    let (negative, digits) = match text.as_bytes().first() {
        Some(b'-') => (true, &text[1..]),
        Some(b'+') => (false, &text[1..]),
        _ => (false, text),
    };

    if digits.is_empty() {
        return None;
    }

    let mut value: i64 = 0;

    for byte in digits.bytes() {
        let digit = (byte as char).to_digit(10)?;

        value = value
            .checked_mul(10)?
            .checked_add(i64::from(digit))?;
    }

    let signed = if negative { -value } else { value };

    i32::try_from(signed).ok()
}

fn main() {
    let mut forward = *b"abcdefgh";
    move_bytes(&mut forward, 0, 2, 6); // destination below source
    println!("shift left : {}", String::from_utf8_lossy(&forward));

    let mut backward = *b"abcdefgh";
    move_bytes(&mut backward, 2, 0, 6); // destination above source
    println!("shift right: {}", String::from_utf8_lossy(&backward));

    println!("length     : {}", string_length(b"operating\0"));
    println!("parse min  : {:?}", parse_int("-2147483648"));
    println!("parse over : {:?}", parse_int("2147483648"));
}
