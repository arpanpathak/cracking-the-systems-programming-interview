// ch19/ring_buffer.cpp: Hand-rolled fixed-capacity ring buffer (without std::deque)
// paired with std::mutex and dual std::condition_variables.
#include <cassert>
#include <condition_variable>
#include <cstddef>
#include <cstdio>
#include <mutex>
#include <optional>
#include <string>
#include <thread>
#include <utility>
#include <vector>

template <typename T>
class Ring {
public:
    explicit Ring(size_t capacity)
        : buf_(capacity == 0 ? 1 : capacity), head_(0), len_(0) {}

    bool is_full() const { return len_ == buf_.size(); }
    bool is_empty() const { return len_ == 0; }

    void push_back(T item) {
        size_t tail = (head_ + len_) % buf_.size();
        buf_[tail].emplace(std::move(item));
        ++len_;
    }

    T pop_front() {
        T item = std::move(*buf_[head_]);
        buf_[head_].reset();  // Destroy moved-from slot so empty slots stay disengaged
        head_ = (head_ + 1) % buf_.size();
        --len_;
        return item;
    }

private:
    std::vector<std::optional<T>> buf_;
    size_t head_;
    size_t len_;
};

template <typename T>
class BoundedRingQueue {
public:
    explicit BoundedRingQueue(size_t capacity) : ring_(capacity) {}

    void push(T item) {
        {
            std::unique_lock<std::mutex> lock(mu_);
            not_full_.wait(lock, [this] { return !ring_.is_full(); });
            ring_.push_back(std::move(item));
        }  // Unlock before notify_one to minimize mutex contention on wakeup
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
    Ring<T> ring_;
    std::mutex mu_;
    std::condition_variable not_full_;
    std::condition_variable not_empty_;
};

int main() {
    constexpr size_t kTotal = 200;
    BoundedRingQueue<std::string> queue(4);

    std::thread producer([&] {
        for (size_t i = 0; i < kTotal; ++i) {
            queue.push("msg-" + std::to_string(i));
        }
    });

    for (size_t expected = 0; expected < kTotal; ++expected) {
        std::string received = queue.pop();
        assert(received == "msg-" + std::to_string(expected));
    }

    producer.join();
    printf("hand-rolled ring queue: %zu std::string messages transferred in strict FIFO order (verified)\n",
           kTotal);
}
