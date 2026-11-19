// ch19/bounded_queue.cpp: a blocking queue of fixed capacity.
#include <condition_variable>
#include <cstdint>
#include <deque>
#include <iostream>
#include <mutex>
#include <thread>
#include <vector>

/// A queue that blocks producers while it is full and consumers while it is empty.
template <typename T>
class BoundedQueue {
public:
    /// A capacity of 0 would block every push forever, so the minimum is 1.
    explicit BoundedQueue(size_t capacity) : capacity_(capacity == 0 ? 1 : capacity) {}

    /// Appends one item. Waits while the queue is full.
    void push(T item) {
        std::unique_lock<std::mutex> lock(mutex_);

        while (is_full()) {
            is_full_.wait(lock);
        }

        items_.push_back(std::move(item));
        is_empty_.notify_one();
    }

    /// Removes the oldest item. Waits while the queue is empty.
    T pop() {
        std::unique_lock<std::mutex> lock(mutex_);

        while (is_empty()) {
            is_empty_.wait(lock);
        }

        T item = std::move(items_.front());
        items_.pop_front();
        is_full_.notify_one();

        return item;
    }

private:
    bool is_full() const { return items_.size() == capacity_; }

    bool is_empty() const { return items_.empty(); }

    const size_t capacity_;
    std::deque<T> items_;
    std::mutex mutex_;
    std::condition_variable is_full_;    // producers sleep here while the queue is full
    std::condition_variable is_empty_;   // consumers sleep here while the queue is empty
};

int main() {
    constexpr uint64_t kItemsPerThread = 50'000;
    constexpr uint64_t kThreadPairs = 2;

    BoundedQueue<uint64_t> queue(8);
    uint64_t consumed_sum[kThreadPairs] = {0, 0};
    std::vector<std::thread> threads;

    for (uint64_t producer = 0; producer < kThreadPairs; ++producer) {
        threads.emplace_back([&queue, producer] {
            uint64_t first = producer * kItemsPerThread + 1;

            for (uint64_t value = first; value < first + kItemsPerThread; ++value) {
                queue.push(value);
            }
        });
    }

    for (uint64_t consumer = 0; consumer < kThreadPairs; ++consumer) {
        threads.emplace_back([&queue, &consumed_sum, consumer] {
            for (uint64_t taken = 0; taken < kItemsPerThread; ++taken) {
                consumed_sum[consumer] += queue.pop();
            }
        });
    }

    for (std::thread& thread : threads) {
        thread.join();
    }

    uint64_t item_count = kThreadPairs * kItemsPerThread;
    uint64_t expected = item_count * (item_count + 1) / 2;
    uint64_t consumed = consumed_sum[0] + consumed_sum[1];

    std::cout << "expected sum " << expected << "\n"
              << "consumed sum " << consumed << "\n"
              << "match        " << (expected == consumed ? "yes" : "NO") << "\n";
}
