// ch06/cas_ordering.cpp: compare_exchange_weak CAS loop, Acquire-Release
// message passing, and a lock-free Seqlock snapshot reader/writer.
#include <atomic>
#include <cstdint>
#include <iostream>
#include <thread>
#include <vector>

// 1. Atomic Compare-And-Swap (CAS) maximum accumulator using compare_exchange_weak.
static void update_max(std::atomic<uint64_t>& max_val, uint64_t candidate) {
    uint64_t prev = max_val.load(std::memory_order_relaxed);
    while (candidate > prev &&
           !max_val.compare_exchange_weak(prev, candidate,
                                          std::memory_order_release,
                                          std::memory_order_relaxed)) {
        // On failure (or spurious LL/SC clear on ARM64), prev is reloaded
        // with the current value of max_val automatically.
    }
}

// 2. Lock-free Seqlock for read-mostly telemetry coordinates.
struct TelemetrySnapshot {
    uint64_t ticks;
    uint64_t scaled_ns;
};

class Seqlock {
public:
    void write(TelemetrySnapshot next) {
        uint64_t s = seq_.load(std::memory_order_relaxed);
        seq_.store(s + 1, std::memory_order_release); // odd: write in progress
        std::atomic_signal_fence(std::memory_order_acq_rel);
        slot_ticks_.store(next.ticks, std::memory_order_relaxed);
        slot_ns_.store(next.scaled_ns, std::memory_order_relaxed);
        seq_.store(s + 2, std::memory_order_release); // even: coherent snapshot
    }

    TelemetrySnapshot read() const {
        for (;;) {
            uint64_t s1 = seq_.load(std::memory_order_acquire);
            if ((s1 & 1u) != 0) continue; // writer active; retry

            uint64_t t = slot_ticks_.load(std::memory_order_relaxed);
            uint64_t ns = slot_ns_.load(std::memory_order_relaxed);
            std::atomic_thread_fence(std::memory_order_acquire);

            uint64_t s2 = seq_.load(std::memory_order_relaxed);
            if (s1 == s2) return {t, ns};
        }
    }

private:
    std::atomic<uint64_t> seq_{0};
    std::atomic<uint64_t> slot_ticks_{0};
    std::atomic<uint64_t> slot_ns_{0};
};

int main() {
    // Part A: CAS loop across 4 threads.
    std::atomic<uint64_t> peak{0};
    std::vector<std::thread> workers;
    for (uint64_t id = 1; id <= 4; ++id) {
        workers.emplace_back([&peak, id] {
            for (uint64_t step = 1; step <= 25'000; ++step) {
                update_max(peak, id * step);
            }
        });
    }
    for (auto& w : workers) w.join();

    // Part B: Acquire-Release message passing.
    uint64_t payload = 0;
    std::atomic<bool> ready{false};
    uint64_t observed_payload = 0;

    std::thread producer([&] {
        payload = 0xCAFE'BABE'2026ULL;
        ready.store(true, std::memory_order_release);
    });
    std::thread consumer([&] {
        while (!ready.load(std::memory_order_acquire)) {}
        observed_payload = payload;
    });
    producer.join();
    consumer.join();

    // Part C: Seqlock invariant verification (scaled_ns == ticks * 10).
    Seqlock clock_lock;
    std::atomic<bool> done{false};
    uint64_t torn_reads = 0;

    std::thread writer([&] {
        for (uint64_t i = 1; i <= 50'000; ++i) {
            clock_lock.write({i, i * 10});
        }
        done.store(true, std::memory_order_release);
    });
    std::thread reader([&] {
        while (!done.load(std::memory_order_acquire)) {
            TelemetrySnapshot snap = clock_lock.read();
            if (snap.scaled_ns != snap.ticks * 10) ++torn_reads;
        }
    });
    writer.join();
    reader.join();

    std::cout << "cas peak value   : " << peak.load() << "\n"
              << "acq-rel payload  : 0x" << std::hex << observed_payload << std::dec << "\n"
              << "seqlock torn     : " << torn_reads << "\n";
}
