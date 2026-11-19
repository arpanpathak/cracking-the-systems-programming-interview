// ch17/false_sharing.cpp: two hot counters, one cache line versus two.
// The counters use atomic increments: the standard pattern for shared counters.
#include <atomic>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <thread>

struct Unpadded {
    alignas(64) std::atomic<uint64_t> a{0};
    std::atomic<uint64_t> b{0};          // shares a's cache line
};

struct Padded {
    alignas(64) std::atomic<uint64_t> a{0};
    alignas(64) std::atomic<uint64_t> b{0};   // each field owns a line
};

template <typename C>
double run(C& c) {
    constexpr uint64_t kIters = 40'000'000;

    auto t0 = std::chrono::steady_clock::now();
    std::thread t1([&] {
        for (uint64_t i = 0; i < kIters; ++i) {
            c.a.fetch_add(1, std::memory_order_relaxed);
        }
    });

    std::thread t2([&] {
        for (uint64_t i = 0; i < kIters; ++i) {
            c.b.fetch_add(1, std::memory_order_relaxed);
        }
    });

    t1.join();
    t2.join();

    auto t1e = std::chrono::steady_clock::now();
    return std::chrono::duration<double, std::milli>(t1e - t0).count();
}

int main() {
    Unpadded u;
    Padded p;

    run(u);                       // warmup
    run(p);

    double tu = run(u);
    double tp = run(p);

    printf("unpadded (shared line): %7.1f ms\n", tu);
    printf("padded   (separate)   : %7.1f ms\n", tp);
    printf("ratio                 : %5.2fx\n", tu / tp);
    printf("(unpadded %llu, padded %llu)\n",
           static_cast<unsigned long long>(u.a.load()),
           static_cast<unsigned long long>(p.a.load()));
}
