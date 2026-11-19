// ch04/threads.cpp: four threads, one process.
#include <iostream>
#include <mutex>
#include <thread>
#include <vector>

int main() {
    std::mutex m;                      // serializes access to std::cout
    std::vector<std::thread> workers;

    for (int i = 0; i < 4; ++i) {
        workers.emplace_back([i, &m] {
            std::lock_guard<std::mutex> lock(m);
            std::cout << "thread " << i << " running\n";
        });
    }

    for (auto& t : workers) t.join();

    std::cout << "all threads joined\n";
}
