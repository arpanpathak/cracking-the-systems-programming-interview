// ch19/ring_buffer_uninit.cpp: Zero-overhead fixed-capacity ring buffer using raw
// uninitialized aligned storage (C++20 counterpart to Rust's MaybeUninit<T>).
#include <atomic>
#include <cassert>
#include <condition_variable>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <memory>
#include <mutex>
#include <optional>
#include <string>
#include <thread>
#include <utility>

template <typename T>
class RawRing {
public:
    explicit RawRing(size_t capacity)
        : cap_(capacity == 0 ? 1 : capacity),
          storage_(std::make_unique<Slot[]>(cap_)),
          head_(0),
          len_(0) {}

    ~RawRing() {
        // Raw byte slots do NOT invoke ~T() automatically; destroy every live element.
        while (len_ > 0) {
            std::destroy_at(slot_ptr(head_));
            head_ = (head_ + 1) % cap_;
            --len_;
        }
    }

    RawRing(const RawRing&) = delete;
    RawRing& operator=(const RawRing&) = delete;

    bool is_full() const { return len_ == cap_; }
    bool is_empty() const { return len_ == 0; }

    void push_back(T item) {
        size_t tail = (head_ + len_) % cap_;
        std::construct_at(slot_ptr(tail), std::move(item));  // Placement new into raw bytes
        ++len_;
    }

    T pop_front() {
        T* ptr = slot_ptr(head_);
        T item = std::move(*ptr);
        std::destroy_at(ptr);  // Explicitly end lifetime so slot returns to raw uninit bytes
        head_ = (head_ + 1) % cap_;
        --len_;
        return item;
    }

private:
    struct Slot {
        alignas(T) std::byte bytes[sizeof(T)];  // Identical size & alignment to T; zero tag
    };

    T* slot_ptr(size_t index) { return std::launder(reinterpret_cast<T*>(storage_[index].bytes)); }

    size_t cap_;
    std::unique_ptr<Slot[]> storage_;
    size_t head_;
    size_t len_;
};

template <typename T>
class BoundedRawQueue {
public:
    explicit BoundedRawQueue(size_t capacity) : ring_(capacity) {}

    void push(T item) {
        {
            std::unique_lock<std::mutex> lock(mu_);
            not_full_.wait(lock, [this] { return !ring_.is_full(); });
            ring_.push_back(std::move(item));
        }
        not_empty_.notify_one();
    }

    T pop() {
        T item = [&] {
            std::unique_lock<std::mutex> lock(mu_);
            not_empty_.wait(lock, [this] { return !ring_.is_empty(); });
            return ring_.pop_front();
        }();
        not_full_.notify_one();
        return item;
    }

private:
    RawRing<T> ring_;
    std::mutex mu_;
    std::condition_variable not_full_;
    std::condition_variable not_empty_;
};

struct DropTracker {
    std::atomic<size_t>* count;
    ~DropTracker() {
        if (count != nullptr) count->fetch_add(1, std::memory_order_relaxed);
    }
    DropTracker(std::atomic<size_t>* c) : count(c) {}
    DropTracker(DropTracker&& other) noexcept : count(other.count) { other.count = nullptr; }
    DropTracker(const DropTracker&) = delete;
};

int main() {
    struct RawSlotU64 { alignas(uint64_t) std::byte bytes[sizeof(uint64_t)]; };
    printf("layouts (bytes): uint64_t=%zu, std::optional<uint64_t>=%zu, RawSlot<uint64_t>=%zu, std::string=%zu, std::optional<std::string>=%zu\n",
           sizeof(uint64_t), sizeof(std::optional<uint64_t>), sizeof(RawSlotU64),
           sizeof(std::string), sizeof(std::optional<std::string>));
    assert(sizeof(std::optional<uint64_t>) == 16);
    assert(sizeof(RawSlotU64) == 8);

    constexpr size_t kTotal = 200;
    BoundedRawQueue<std::string> queue(4);
    std::thread producer([&] {
        for (size_t i = 0; i < kTotal; ++i) {
            queue.push("raw-" + std::to_string(i));
        }
    });
    for (size_t expected = 0; expected < kTotal; ++expected) {
        assert(queue.pop() == "raw-" + std::to_string(expected));
    }
    producer.join();

    std::atomic<size_t> drops{0};
    {
        RawRing<DropTracker> ring(8);
        for (int i = 0; i < 3; ++i) ring.push_back(DropTracker(&drops));
    }
    assert(drops.load(std::memory_order_relaxed) == 3);
    printf("RawSlot ring: %zu std::strings transferred + partial-ring ~RawRing destroyed 3/3 live items (verified)\n",
           kTotal);
}
