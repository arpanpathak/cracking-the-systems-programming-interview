// ch19/byte_routines.cpp: memmove, strlen, and atoi written by hand.
#include <climits>
#include <cstddef>
#include <cstdio>
#include <cstring>
#include <optional>

/// Copies `count` bytes from `source` to `destination`. The two ranges may overlap.
void* move_bytes(void* destination, const void* source, size_t count) {
    auto* to = static_cast<unsigned char*>(destination);
    const auto* from = static_cast<const unsigned char*>(source);

    if (to < from) {
        for (size_t index = 0; index < count; ++index) to[index] = from[index];
        return destination;
    }

    for (size_t index = count; index > 0; --index) to[index - 1] = from[index - 1];
    return destination;
}

/// Counts the characters before the terminating NUL.
size_t string_length(const char* text) {
    const char* cursor = text;

    while (*cursor != '\0') ++cursor;

    return static_cast<size_t>(cursor - text);
}

/// Parses an optional sign and decimal digits. Returns std::nullopt on overflow or invalid format.
std::optional<int> parse_int(const char* text) {
    if (text == nullptr || *text == '\0') {
        return std::nullopt;
    }

    const char* cursor = text;
    bool negative = (*cursor == '-');

    if (*cursor == '-' || *cursor == '+') {
        ++cursor;
    }

    if (*cursor < '0' || *cursor > '9') {
        return std::nullopt;
    }

    long long value = 0;

    for (; *cursor >= '0' && *cursor <= '9'; ++cursor) {
        value = value * 10 + (*cursor - '0');

        if (value > static_cast<long long>(INT_MAX) + 1) {
            return std::nullopt;
        }
    }

    if (*cursor != '\0') {
        return std::nullopt;   // non-digit characters trailing the number
    }

    if (negative) {
        value = -value;
    }

    if (value > INT_MAX || value < INT_MIN) {
        return std::nullopt;
    }

    return static_cast<int>(value);
}

int main() {
    char forward[] = "abcdefgh";
    move_bytes(forward, forward + 2, 6);          // destination below source
    printf("shift left : %s\n", forward);

    char backward[] = "abcdefgh";
    move_bytes(backward + 2, backward, 6);        // destination above source
    printf("shift right: %s\n", backward);

    printf("length     : %zu\n", string_length("operating"));

    std::optional<int> parsed_min = parse_int("-2147483648");
    if (parsed_min) {
        printf("parse min  : ok %d\n", *parsed_min);
    } else {
        printf("parse min  : error\n");
    }

    std::optional<int> parsed_over = parse_int("2147483648");
    if (parsed_over) {
        printf("parse over : ok %d\n", *parsed_over);
    } else {
        printf("parse over : error\n");
    }
}
