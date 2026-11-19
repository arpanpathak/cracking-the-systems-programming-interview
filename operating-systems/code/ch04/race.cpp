// ch04/race.cpp: eight threads increment one counter without synchronization.
// Each iteration is a read, an add, and a write, forced to memory with volatile.
#include <cstdint>
#include <iostream>
#include <thread>
#include <vector>

int main() {
    constexpr int kThreads = 8;
    constexpr uint64_t kIters = 20'000'000;

    volatile uint64_t counter = 0;     // shared, no protection
    std::vector<std::thread> workers;

    for (int i = 0; i < kThreads; ++i) {
        workers.emplace_back([&counter] {
            for (uint64_t j = 0; j < kIters; ++j) {
                counter = counter + 1; // read-modify-write, not atomic
            }
        });
    }

    for (auto& t : workers) t.join();

    uint64_t observed = counter;
    std::cout << "expected " << (kThreads * kIters)
              << ", observed " << observed << "\n";
}
