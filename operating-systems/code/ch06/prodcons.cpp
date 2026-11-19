// ch06/prodcons.cpp: a bounded buffer shared by two producers and two consumers.
#include <condition_variable>
#include <cstdint>
#include <iostream>
#include <mutex>
#include <thread>
#include <vector>

int main() {
    constexpr int kCapacity = 8;
    constexpr int kProducers = 2;
    constexpr int kConsumers = 2;
    constexpr uint64_t kItemsPerProducer = 100'000;

    int buf[kCapacity];
    int head = 0, tail = 0, count = 0;
    std::mutex m;
    std::condition_variable not_full, not_empty;

    std::vector<std::thread> producers, consumers;
    std::vector<uint64_t> produced_sum(kProducers, 0);
    std::vector<uint64_t> consumed_sum(kConsumers, 0);

    for (int p = 0; p < kProducers; ++p) {
        producers.emplace_back([&, p] {
            uint64_t first = p * kItemsPerProducer + 1;

            for (uint64_t v = first; v < first + kItemsPerProducer; ++v) {
                std::unique_lock<std::mutex> lock(m);
                not_full.wait(lock, [&] { return count < kCapacity; });

                buf[tail] = static_cast<int>(v); // fits: v <= 200000
                tail = (tail + 1) % kCapacity;
                ++count;
                produced_sum[p] += v;

                not_empty.notify_one();
            }
        });
    }

    for (int c = 0; c < kConsumers; ++c) {
        consumers.emplace_back([&, c] {
            uint64_t local = 0;
            constexpr uint64_t kItemsPerConsumer = kProducers * kItemsPerProducer / kConsumers;

            for (uint64_t done = 0; done < kItemsPerConsumer; ++done) {
                std::unique_lock<std::mutex> lock(m);
                not_empty.wait(lock, [&] { return count > 0; });

                int v = buf[head];
                head = (head + 1) % kCapacity;
                --count;
                local += v;

                not_full.notify_one();
            }

            consumed_sum[c] = local;
        });
    }

    for (auto& t : producers) t.join();
    for (auto& t : consumers) t.join();

    uint64_t expected =
        (kProducers * kItemsPerProducer) * (kProducers * kItemsPerProducer + 1) / 2;

    uint64_t produced = 0, consumed = 0;
    for (uint64_t s : produced_sum) produced += s;
    for (uint64_t s : consumed_sum) consumed += s;

    std::cout << "produced sum " << produced << "\n"
              << "consumed sum " << consumed << "\n"
              << "expected     " << expected << "\n"
              << "match        " << (produced == consumed && consumed == expected
                                          ? "yes"
                                          : "NO")
              << "\n";
}
