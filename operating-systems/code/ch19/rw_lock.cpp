// ch19/rw_lock.cpp: a reader-writer lock built from a mutex and a condition variable.
#include <atomic>
#include <condition_variable>
#include <iostream>
#include <mutex>
#include <thread>
#include <vector>

/// Many readers may hold the lock together. A writer holds it alone.
class ReaderWriterLock {
public:
    void lock_shared() {
        std::unique_lock<std::mutex> lock(mutex_);

        while (reader_must_wait()) {
            changed_.wait(lock);
        }

        ++readers_active_;
    }

    void unlock_shared() {
        std::lock_guard<std::mutex> lock(mutex_);

        --readers_active_;
        if (readers_active_ == 0) changed_.notify_all();
    }

    void lock_exclusive() {
        std::unique_lock<std::mutex> lock(mutex_);

        ++writers_waiting_;   // new readers now queue behind this writer

        while (writer_must_wait()) {
            changed_.wait(lock);
        }

        --writers_waiting_;
        writer_active_ = true;
    }

    void unlock_exclusive() {
        std::lock_guard<std::mutex> lock(mutex_);

        writer_active_ = false;
        changed_.notify_all();
    }

private:
    /// A reader waits for an active writer, and also lets waiting writers go first.
    bool reader_must_wait() const { return writer_active_ || writers_waiting_ > 0; }

    /// A writer waits until nobody else is inside.
    bool writer_must_wait() const { return writer_active_ || readers_active_ > 0; }

    std::mutex mutex_;
    std::condition_variable changed_;
    int readers_active_ = 0;
    int writers_waiting_ = 0;
    bool writer_active_ = false;
};

int main() {
    constexpr int kWriters = 2;
    constexpr int kReaders = 4;
    constexpr int kRounds = 20'000;

    ReaderWriterLock lock;
    long balance_a = 1000;   // invariant: balance_a + balance_b == 1000
    long balance_b = 0;
    std::atomic<long> broken_reads{0};
    std::vector<std::thread> threads;

    for (int writer = 0; writer < kWriters; ++writer) {
        threads.emplace_back([&] {
            for (int round = 0; round < kRounds; ++round) {
                lock.lock_exclusive();
                --balance_a;
                ++balance_b;
                lock.unlock_exclusive();
            }
        });
    }

    for (int reader = 0; reader < kReaders; ++reader) {
        threads.emplace_back([&] {
            for (int round = 0; round < kRounds; ++round) {
                lock.lock_shared();
                bool consistent = (balance_a + balance_b == 1000);
                lock.unlock_shared();

                if (!consistent) ++broken_reads;
            }
        });
    }

    for (std::thread& thread : threads) thread.join();

    std::cout << "transfers    " << balance_b << "\n"
              << "broken reads " << broken_reads.load() << "\n";
}
