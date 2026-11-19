// ch06/trylock.cpp: the same two workers, but worker 2 backs off instead of blocking.
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
        std::lock_guard<std::mutex> lb(b);
        std::cout << "worker 1 got A and B\n" << std::flush;
    });

    std::thread t2([&] {
        for (;;) {
            {
                std::lock_guard<std::mutex> lb(b);
                std::cout << "worker 2 holds B, tries A\n" << std::flush;
                if (a.try_lock()) {
                    std::cout << "worker 2 got B and A\n" << std::flush;
                    a.unlock();
                    break;
                }
            }

            std::this_thread::sleep_for(std::chrono::milliseconds(5));
        }
    });

    t1.join();
    t2.join();

    std::cout << "finished without deadlock\n";
}
