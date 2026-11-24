// ch19/mpsc_queue.cpp: wait-free multi-producer, single-consumer queue (Vyukov).
#include <atomic>
#include <cstdint>
#include <iostream>
#include <optional>
#include <thread>
#include <utility>
#include <vector>

/// Unbounded lock-free MPSC queue using a stub-node linked list.
/// Multiple threads may call push() concurrently; only one thread may call pop().
template <typename T>
class MpscQueue {
public:
    MpscQueue() {
        Node* stub = new Node(std::nullopt);
        head_.store(stub, std::memory_order_relaxed);
        tail_ = stub;
    }

    MpscQueue(const MpscQueue&) = delete;
    MpscQueue& operator=(const MpscQueue&) = delete;

    ~MpscQueue() {
        Node* curr = tail_;
        while (curr) {
            Node* next = curr->next.load(std::memory_order_relaxed);
            delete curr;
            curr = next;
        }
    }

    /// Wait-free enqueue: atomically swap head, then link the previous node.
    void push(T value) {
        Node* node = new Node(std::move(value));
        Node* prev = head_.exchange(node, std::memory_order_acq_rel);
        prev->next.store(node, std::memory_order_release);
    }

    /// Single-consumer dequeue: advance stub to next, reclaim old stub, return payload.
    std::optional<T> pop() {
        Node* next = tail_->next.load(std::memory_order_acquire);
        if (!next) return std::nullopt;

        T value = std::move(*next->data);
        next->data.reset();

        delete tail_;
        tail_ = next;
        return value;
    }

private:
    struct Node {
        explicit Node(std::optional<T> value) : data(std::move(value)) {}

        std::optional<T> data;
        std::atomic<Node*> next{nullptr};
    };

    alignas(64) std::atomic<Node*> head_{nullptr}; // shared by all producers
    alignas(64) Node* tail_{nullptr};              // owned by the single consumer
};

int main() {
    constexpr uint64_t kProducers = 4;
    constexpr uint64_t kPerProducer = 25'000;
    constexpr uint64_t kTotal = kProducers * kPerProducer;

    MpscQueue<uint64_t> queue;
    std::vector<std::thread> producers;
    producers.reserve(kProducers);

    for (uint64_t p = 0; p < kProducers; ++p) {
        producers.emplace_back([&queue, p] {
            uint64_t base = p * kPerProducer;
            for (uint64_t i = 1; i <= kPerProducer; ++i) {
                queue.push(base + i);
            }
        });
    }

    uint64_t taken = 0;
    uint64_t consumed_sum = 0;

    while (taken < kTotal) {
        std::optional<uint64_t> value = queue.pop();
        if (!value) {
            std::this_thread::yield();
            continue;
        }

        consumed_sum += *value;
        ++taken;
    }

    for (std::thread& t : producers) t.join();

    uint64_t expected = kTotal * (kTotal + 1) / 2;

    std::cout << "producers    " << kProducers << "\n"
              << "expected sum " << expected << "\n"
              << "consumed sum " << consumed_sum << "\n"
              << "match        " << (expected == consumed_sum ? "yes" : "NO") << "\n";
}
