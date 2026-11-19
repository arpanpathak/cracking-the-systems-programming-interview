// ch19/spsc_ring.cpp: a lock-free ring buffer for one producer and one consumer.
#include <array>
#include <atomic>
#include <cstdint>
#include <iostream>
#include <optional>
#include <thread>

/// A ring buffer that one thread writes and one other thread reads, without locks.
class SpscRing {
public:
    /// Stores a value. Returns false when the ring is full.
    bool try_push(uint64_t value) {
        size_t tail = tail_.load(std::memory_order_relaxed);
        size_t head = head_.load(std::memory_order_acquire);

        if (tail - head == kCapacity) return false;

        slots_[tail % kCapacity] = value;
        tail_.store(tail + 1, std::memory_order_release);
        return true;
    }

    /// Takes the oldest value. Returns nothing when the ring is empty.
    std::optional<uint64_t> try_pop() {
        size_t head = head_.load(std::memory_order_relaxed);
        size_t tail = tail_.load(std::memory_order_acquire);

        if (head == tail) return std::nullopt;

        uint64_t value = slots_[head % kCapacity];
        head_.store(head + 1, std::memory_order_release);
        return value;
    }

private:
    static constexpr size_t kCapacity = 1024;

    std::array<uint64_t, kCapacity> slots_{};
    alignas(64) std::atomic<size_t> head_{0};   // written only by the consumer
    alignas(64) std::atomic<size_t> tail_{0};   // written only by the producer
};

int main() {
    constexpr uint64_t kItems = 1'000'000;
    SpscRing ring;
    uint64_t consumed_sum = 0;

    std::thread producer([&ring] {
        for (uint64_t value = 1; value <= kItems; ++value) {
            while (!ring.try_push(value)) std::this_thread::yield();
        }
    });

    std::thread consumer([&ring, &consumed_sum] {
        uint64_t taken = 0;

        while (taken < kItems) {
            std::optional<uint64_t> value = ring.try_pop();

            if (!value) {
                std::this_thread::yield();
                continue;
            }

            consumed_sum += *value;
            ++taken;
        }
    });

    producer.join();
    consumer.join();

    uint64_t expected = kItems * (kItems + 1) / 2;

    std::cout << "expected sum " << expected << "\n"
              << "consumed sum " << consumed_sum << "\n"
              << "match        " << (expected == consumed_sum ? "yes" : "NO") << "\n";
}
