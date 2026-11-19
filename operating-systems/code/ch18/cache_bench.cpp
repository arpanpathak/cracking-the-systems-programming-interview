// ch18/cache_bench.cpp: walk a buffer with stride 64; each size step
// crosses one more level of the memory hierarchy.
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <vector>

static double ns_per_access(size_t bytes) {
    constexpr uint64_t kAccesses = 16'000'000;
    std::vector<uint8_t> v(bytes);

    // Touch every 64th byte once so page faults do not dominate the timing.
    for (size_t i = 0; i < bytes; i += 64) v[i] = 1;

    uint64_t sum = 0;
    size_t i = 0;
    auto t0 = std::chrono::steady_clock::now();
    for (uint64_t k = 0; k < kAccesses; ++k) {
        sum += v[i];
        i += 64;
        if (i >= bytes) i = 0;
    }
    auto t1 = std::chrono::steady_clock::now();

    double ns = std::chrono::duration<double, std::nano>(t1 - t0).count() / kAccesses;
    printf("  %9zu bytes  %7.1f ns per access  (checksum %llu)\n", bytes, ns,
           static_cast<unsigned long long>(sum));
    return ns;
}

int main() {
    printf("stride 64 bytes, 16,000,000 accesses per size\n\n");

    for (size_t s = 16 * 1024; s <= 256u * 1024 * 1024; s *= 4) {
        ns_per_access(s);
    }
}
