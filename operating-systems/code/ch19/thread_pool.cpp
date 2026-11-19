// ch19/thread_pool.cpp: a fixed set of worker threads that run queued tasks.
#include <atomic>
#include <condition_variable>
#include <cstdint>
#include <functional>
#include <iostream>
#include <mutex>
#include <queue>
#include <thread>
#include <vector>

/// Runs submitted tasks on `worker_count` threads. The destructor finishes all
/// queued tasks and then joins the workers.
class ThreadPool {
public:
    explicit ThreadPool(size_t worker_count) {
        for (size_t worker = 0; worker < worker_count; ++worker) {
            workers_.emplace_back([this] { run_worker(); });
        }
    }

    ~ThreadPool() {
        {
            std::lock_guard<std::mutex> lock(mutex_);
            stopping_ = true;
        }

        task_ready_.notify_all();

        for (std::thread& worker : workers_) {
            worker.join();
        }
    }

    /// Queues one task and wakes one idle worker.
    void submit(std::function<void()> task) {
        {
            std::lock_guard<std::mutex> lock(mutex_);
            tasks_.push(std::move(task));
        }

        task_ready_.notify_one();
    }

private:
    void run_worker() {
        while (true) {
            std::unique_lock<std::mutex> lock(mutex_);

            while (must_wait()) {
                task_ready_.wait(lock);
            }

            if (tasks_.empty()) return;   // stopping, and nothing left to run

            std::function<void()> task = std::move(tasks_.front());
            tasks_.pop();
            lock.unlock();

            task();                       // run without holding the lock
        }
    }

    /// A worker sleeps only while there is no task and the pool is still open.
    bool must_wait() const { return tasks_.empty() && !stopping_; }

    std::mutex mutex_;
    std::condition_variable task_ready_;
    std::queue<std::function<void()>> tasks_;
    std::vector<std::thread> workers_;
    bool stopping_ = false;
};

int main() {
    constexpr uint64_t kTasks = 1000;
    std::atomic<uint64_t> total{0};

    {
        ThreadPool pool(4);

        for (uint64_t task = 1; task <= kTasks; ++task) {
            pool.submit([&total, task] {
                total.fetch_add(task, std::memory_order_relaxed);
            });
        }
    }   // the destructor waits for every task here

    std::cout << "expected " << kTasks * (kTasks + 1) / 2 << "\n"
              << "total    " << total.load() << "\n";
}
