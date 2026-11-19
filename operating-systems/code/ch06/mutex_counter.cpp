// ch06/mutex_counter.cpp: the counter from chapter 4, now guarded by a mutex.
#include <cstdint>
#include <iostream>
#include <mutex>
#include <thread>
#include <vector>

int main() {
    constexpr int kThreads = 8;
    constexpr uint64_t kIters = 5'000'000;

    uint64_t counter = 0;
    std::mutex m;
    std::vector<std::thread> workers;

    for (int i = 0; i < kThreads; ++i) {
        workers.emplace_back([&] {
            for (uint64_t j = 0; j < kIters; ++j) {
                std::lock_guard<std::mutex> lock(m);
                ++counter;
            }
        });
    }

    for (auto& t : workers) t.join();

    std::cout << "expected " << (kThreads * kIters)
              << ", observed " << counter << "\n";
}
