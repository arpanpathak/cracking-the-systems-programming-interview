// ch04/race_atomic.cpp: the same counter with an atomic increment.
#include <atomic>
#include <cstdint>
#include <iostream>
#include <thread>
#include <vector>

int main() {
    constexpr int kThreads = 8;
    constexpr uint64_t kIters = 5'000'000;

    std::atomic<uint64_t> counter{0};
    std::vector<std::thread> workers;

    for (int i = 0; i < kThreads; ++i) {
        workers.emplace_back([&counter] {
            for (uint64_t j = 0; j < kIters; ++j) {
                counter.fetch_add(1, std::memory_order_relaxed);
            }
        });
    }

    for (auto& t : workers) t.join();

    std::cout << "expected " << (kThreads * kIters)
              << ", observed " << counter.load() << "\n";
}
