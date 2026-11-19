// ch07/tlb.cpp: Measures per-access latency while sweeping the working set upward,
// stepping by one full hardware page per access so latency cliffs reveal TLB capacity.
#include <sys/mman.h>
#include <unistd.h>
#include <chrono>
#include <cstdint>
#include <cstdio>

static double measure_ns_per_access(size_t working_set_bytes, uint64_t total_accesses) {
    const size_t page_size = static_cast<size_t>(sysconf(_SC_PAGESIZE));

    char* region = static_cast<char*>(
        mmap(nullptr, working_set_bytes, PROT_READ | PROT_WRITE,
             MAP_PRIVATE | MAP_ANON, -1, 0));
    if (region == MAP_FAILED) return -1.0;

    const size_t page_count = working_set_bytes / page_size;

    // Pre-fault every page once so page-allocation traps do not distort TLB timings.
    for (size_t page_index = 0; page_index < page_count; ++page_index) {
        region[page_index * page_size] = 1;
    }

    uint64_t checksum = 0;
    size_t page_index = 0;

    auto start_time = std::chrono::steady_clock::now();
    for (uint64_t step = 0; step < total_accesses; ++step) {
        checksum += static_cast<uint8_t>(region[page_index * page_size]);
        if (++page_index == page_count) page_index = 0;
    }
    auto end_time = std::chrono::steady_clock::now();

    double ns_per_access =
        std::chrono::duration<double, std::nano>(end_time - start_time).count() / total_accesses;

    printf("  %9zu bytes  %7zu pages  %6.1f ns per access  (checksum %llu)\n",
           working_set_bytes, page_count, ns_per_access,
           static_cast<unsigned long long>(checksum));

    munmap(region, working_set_bytes);
    return ns_per_access;
}

int main() {
    constexpr uint64_t kTotalAccesses = 4'000'000;
    printf("one access per page, %llu accesses per working-set size\n\n",
           static_cast<unsigned long long>(kTotalAccesses));

    for (size_t bytes : {
             size_t{4} * 1024, size_t{64} * 1024, size_t{256} * 1024,
             size_t{1} << 20,  size_t{4} << 20,   size_t{16} << 20,
             size_t{64} << 20, size_t{256} << 20,
         }) {
        measure_ns_per_access(bytes, kTotalAccesses);
    }
}
