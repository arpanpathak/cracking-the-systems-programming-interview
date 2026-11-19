// ch19/bit_tricks.rs: four bit manipulations that systems code uses daily.

/// Counts the 1 bits. Each iteration clears the lowest set bit.
fn count_set_bits(mut value: u64) -> u32 {
    let mut count = 0;

    while value != 0 {
        value &= value - 1;
        count += 1;
    }

    count
}

/// True when exactly one bit is set.
fn is_power_of_two(value: u64) -> bool {
    value != 0 && (value & (value - 1)) == 0
}

/// Rounds `value` up to the next multiple of `alignment`, which must be a power of two.
fn align_up(value: u64, alignment: u64) -> u64 {
    (value + alignment - 1) & !(alignment - 1)
}

/// Smallest power of two that is greater than or equal to `value` (for value >= 1).
/// Uses O(1) bit-smearing without loops or branching.
fn next_power_of_two(value: u64) -> u64 {
    if value <= 1 {
        return 1;
    }

    let mut v = value - 1;

    v |= v >> 1;
    v |= v >> 2;
    v |= v >> 4;
    v |= v >> 8;
    v |= v >> 16;
    v |= v >> 32;

    v + 1
}

fn main() {
    println!("count_set_bits(0b1011)  = {}", count_set_bits(0b1011));
    println!("is_power_of_two(64)     = {}", is_power_of_two(64));
    println!("is_power_of_two(96)     = {}", is_power_of_two(96));
    println!("align_up(11, 16)        = {}", align_up(11, 16));
    println!("align_up(4097, 4096)    = {}", align_up(4097, 4096));
    println!("next_power_of_two(1000) = {}", next_power_of_two(1000));
}
