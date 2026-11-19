// ch19/bit_tricks.cpp: four bit manipulations that systems code uses daily.
#include <cinttypes>
#include <cstdint>
#include <cstdio>

/// Counts the 1 bits. Each iteration clears the lowest set bit.
int count_set_bits(uint64_t value) {
    int count = 0;

    for (; value != 0; value &= value - 1) ++count;

    return count;
}

/// True when exactly one bit is set.
bool is_power_of_two(uint64_t value) {
    return value != 0 && (value & (value - 1)) == 0;
}

/// Rounds `value` up to the next multiple of `alignment`, which must be a power of two.
uint64_t align_up(uint64_t value, uint64_t alignment) {
    return (value + alignment - 1) & ~(alignment - 1);
}

/// Smallest power of two that is greater than or equal to `value` (for value >= 1).
/// Uses O(1) bit-smearing without loops or branching.
uint64_t next_power_of_two(uint64_t value) {
    if (value <= 1) {
        return 1;
    }

    uint64_t v = value - 1;

    v |= v >> 1;
    v |= v >> 2;
    v |= v >> 4;
    v |= v >> 8;
    v |= v >> 16;
    v |= v >> 32;

    return v + 1;
}

int main() {
    printf("count_set_bits(0b1011)  = %d\n", count_set_bits(0b1011));
    printf("is_power_of_two(64)     = %d\n", is_power_of_two(64));
    printf("is_power_of_two(96)     = %d\n", is_power_of_two(96));
    printf("align_up(11, 16)        = %" PRIu64 "\n", align_up(11, 16));
    printf("align_up(4097, 4096)    = %" PRIu64 "\n", align_up(4097, 4096));
    printf("next_power_of_two(1000) = %" PRIu64 "\n", next_power_of_two(1000));
}
