// ch19/priority_workers.cpp: worker threads that pop a fixed set of jobs from a priority heap.
#include <chrono>
#include <concepts>
#include <functional>
#include <iostream>
#include <mutex>
#include <queue>
#include <thread>
#include <tuple>
#include <vector>

using namespace std::chrono_literals;

template <std::invocable F>
struct Job {
    F run;
    unsigned time;
    unsigned priority;
};

using JobState = std::tuple<unsigned, std::chrono::nanoseconds, size_t>;  // (rank, time queued, index)
using MinHeap = std::priority_queue<JobState, std::vector<JobState>, std::greater<>>;

enum class Policy { Fcfs, Sjf, Priority };

unsigned rank(Policy policy, unsigned remaining, unsigned priority) {
    switch (policy) {
        case Policy::Fcfs: return 0;
        case Policy::Sjf: return remaining;
        case Policy::Priority: return priority;
    }
    return 0;
}

template <std::invocable F, typename T = std::invoke_result_t<F>>
std::vector<T> schedule(const std::vector<Job<F>>& jobs, size_t workers, Policy policy) {
    auto start = std::chrono::steady_clock::now();  // Monotonic Clock which never goes backward.
    MinHeap heap;
    for (size_t index = 0; index < jobs.size(); ++index) {
        heap.emplace(rank(policy, jobs[index].time, jobs[index].priority),
                     std::chrono::steady_clock::now() - start, index);
    }
    std::mutex heap_mutex, results_mutex;
    std::vector<T> results;

    {
        std::vector<std::jthread> threads;
        for (size_t worker = 0; worker < workers; ++worker) {
            threads.emplace_back([&] {
                while (true) {
                    std::unique_lock lock(heap_mutex);
                    if (heap.empty()) return;
                    auto [rank_, queued, index] = heap.top();
                    heap.pop();
                    lock.unlock();

                    T out = jobs[index].run();
                    std::scoped_lock guard(results_mutex);
                    results.push_back(out);
                }
            });
        }
    }  // Each jthread joins here, like the end of thread::scope.

    return results;
}

template <typename T>
void print(const char* label, const std::vector<T>& results) {
    std::cout << label << " [";
    for (size_t i = 0; i < results.size(); ++i) {
        std::cout << (i ? ", \"" : "\"") << results[i] << '"';
    }
    std::cout << "]\n";
}

int main() {
    std::vector<Job<const char* (*)()>> jobs = {
        {[] { std::this_thread::sleep_for(50ms); return "a"; }, 5, 2},
        {[] { std::this_thread::sleep_for(20ms); return "b"; }, 2, 3},
        {[] { std::this_thread::sleep_for(30ms); return "c"; }, 3, 1},
        {[] { std::this_thread::sleep_for(40ms); return "d"; }, 4, 1},
    };

    print("fcfs    ", schedule(jobs, 2, Policy::Fcfs));
    print("sjf     ", schedule(jobs, 2, Policy::Sjf));
    print("priority", schedule(jobs, 2, Policy::Priority));
}
