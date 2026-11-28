// ch19/priority_workers.cpp: worker threads that pop a fixed set of jobs from a priority heap.
#include <chrono>
#include <functional>
#include <iostream>
#include <mutex>
#include <queue>
#include <string>
#include <thread>
#include <tuple>
#include <vector>

using namespace std::chrono;

struct Job {
    std::function<std::string()> run;
    unsigned time;
    unsigned priority;
};

using JobState = std::tuple<unsigned, nanoseconds, size_t>;  // (rank, time queued, index)
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

std::vector<std::string> schedule(const std::vector<Job>& jobs, size_t workers, Policy policy) {
    auto start = steady_clock::now();  // Monotonic clock which never goes backward.
    MinHeap heap;
    for (size_t index = 0; index < jobs.size(); ++index) {
        heap.emplace(rank(policy, jobs[index].time, jobs[index].priority), steady_clock::now() - start, index);
    }
    std::mutex heap_mutex, results_mutex;
    std::vector<std::string> results;

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

                    auto out = jobs[index].run();
                    std::scoped_lock guard(results_mutex);
                    results.push_back(out);
                }
            });
        }
    }  // Each jthread joins here, like the end of thread::scope.

    return results;
}

void print(const char* label, const std::vector<std::string>& results) {
    std::cout << label << " [";
    for (size_t i = 0; i < results.size(); ++i) {
        std::cout << (i ? ", \"" : "\"") << results[i] << '"';
    }
    std::cout << "]\n";
}

int main() {
    auto job = [](std::string name, int millis, unsigned time, unsigned priority) {
        return Job{[=] { std::this_thread::sleep_for(milliseconds(millis)); return name; }, time, priority};
    };
    std::vector<Job> jobs = {job("a", 50, 5, 2), job("b", 20, 2, 3), job("c", 30, 3, 1), job("d", 40, 4, 1)};

    print("fcfs    ", schedule(jobs, 2, Policy::Fcfs));
    print("sjf     ", schedule(jobs, 2, Policy::Sjf));
    print("priority", schedule(jobs, 2, Policy::Priority));
}
