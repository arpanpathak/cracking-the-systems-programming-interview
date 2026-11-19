// ch06/deadlock.cpp: two workers, two mutexes, opposite acquisition order.
// This program is expected to hang; the harness kills it and records the outcome.
#include <chrono>
#include <iostream>
#include <mutex>
#include <thread>

int main() {
    std::mutex a, b;

    std::thread t1([&] {
        std::lock_guard<std::mutex> la(a);
        std::cout << "worker 1 holds A\n" << std::flush;
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        std::lock_guard<std::mutex> lb(b);   // waits for B, held by worker 2
        std::cout << "worker 1 got A and B\n" << std::flush;
    });

    std::thread t2([&] {
        std::lock_guard<std::mutex> lb(b);
        std::cout << "worker 2 holds B\n" << std::flush;
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        std::lock_guard<std::mutex> la(a);   // waits for A, held by worker 1
        std::cout << "worker 2 got B and A\n" << std::flush;
    });

    t1.join();
    t2.join();

    std::cout << "finished without deadlock\n";
}
