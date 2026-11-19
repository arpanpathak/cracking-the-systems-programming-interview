// ch07/tlb.cpp: one access per page, sweeping the working set upward.
// Each size step crosses another level of the memory hierarchy; the
// latency steps mark the TLB and cache boundaries.
#include <sys/mman.h>
#include <unistd.h>
#include <chrono>
#include <cstdint>
#include <cstdio>

static double ns_per_access(size_t bytes, uint64_t touches) {
    const long ps = sysconf(_SC_PAGESIZE);

    char* region = static_cast<char*>(
        mmap(nullptr, bytes, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANON, -1, 0));
    if (region == MAP_FAILED) return -1.0;

    const size_t pages = bytes / static_cast<size_t>(ps);

    // Touch every page once so the measurement is not dominated by page faults.
    for (size_t p = 0; p < pages; ++p) region[p * ps] = 1;

    uint64_t sum = 0;
    size_t p = 0;

    auto start = std::chrono::steady_clock::now();
    for (uint64_t i = 0; i < touches; ++i) {
        sum += static_cast<uint8_t>(region[p * ps]);
        if (++p == pages) p = 0;
    }
    auto end = std::chrono::steady_clock::now();

    double ns = std::chrono::duration<double, std::nano>(end - start).count() / touches;

    printf("  %8zu bytes  %8zu pages  %8.1f ns per access  (checksum %llu)\n",
           bytes, pages, ns, static_cast<unsigned long long>(sum));

    munmap(region, bytes);
    return ns;
}

int main() {
    constexpr uint64_t kTouches = 4'000'000;
    printf("one access per page, %llu accesses per size\n\n",
           static_cast<unsigned long long>(kTouches));

    ns_per_access(4 * 1024, kTouches);
    ns_per_access(64 * 1024, kTouches);
    ns_per_access(256 * 1024, kTouches);
    ns_per_access(1u << 20, kTouches);
    ns_per_access(4u << 20, kTouches);
    ns_per_access(16u << 20, kTouches);
    ns_per_access(64u << 20, kTouches);
    ns_per_access(256u << 20, kTouches);
}
