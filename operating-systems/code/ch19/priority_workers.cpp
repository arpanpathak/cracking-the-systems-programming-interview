// ch19/priority_workers.cpp: worker threads that pop a fixed set of jobs from a priority heap.
#include <chrono>
#include <cstdint>
#include <functional>
#include <iostream>
#include <mutex>
#include <optional>
#include <queue>
#include <string>
#include <thread>
#include <tuple>
#include <vector>

using Clock = std::chrono::steady_clock;  // Monotonic: it never moves backward.

struct Job {
    std::function<std::string()> run;
    std::uint32_t time;
    std::uint32_t priority;
};

// (rank, time queued, index). std::greater makes the smallest tuple pop first.
using JobState = std::tuple<std::uint32_t, Clock::duration, std::size_t>;
using MinHeap = std::priority_queue<JobState, std::vector<JobState>, std::greater<JobState>>;

enum class Policy { Fcfs, Sjf, Priority };

std::uint32_t rank(Policy policy, std::uint32_t remaining, std::uint32_t priority) {
    switch (policy) {
        case Policy::Fcfs:
            return 0;
        case Policy::Sjf:
            return remaining;
        case Policy::Priority:
            return priority;
    }
    return 0;
}

std::vector<std::string> schedule(const std::vector<Job>& jobs, std::size_t workers,
                                  Policy policy) {
    const Clock::time_point start = Clock::now();
    MinHeap heap;

    for (std::size_t index = 0; index < jobs.size(); ++index) {
        const Job& job = jobs[index];
        heap.emplace(rank(policy, job.time, job.priority), Clock::now() - start, index);
    }

    std::mutex heap_mutex;
    std::mutex results_mutex;
    std::vector<std::string> results;

    // The lock_guard is destroyed at the return, so the job runs without the heap lock.
    auto pop_next = [&]() -> std::optional<std::size_t> {
        std::lock_guard<std::mutex> lock(heap_mutex);
        if (heap.empty()) {
            return std::nullopt;
        }

        std::size_t index = std::get<2>(heap.top());
        heap.pop();
        return index;
    };

    auto worker = [&] {
        while (std::optional<std::size_t> index = pop_next()) {
            std::string out = jobs[*index].run();

            std::lock_guard<std::mutex> lock(results_mutex);
            results.push_back(std::move(out));
        }
    };

    {
        std::vector<std::jthread> threads;
        for (std::size_t count = 0; count < workers; ++count) {
            threads.emplace_back(worker);
        }
    }  // Each std::jthread joins in its destructor, like the end of thread::scope.

    return results;
}

void print(const std::string& label, const std::vector<std::string>& results) {
    std::cout << label << " [";

    for (std::size_t index = 0; index < results.size(); ++index) {
        const char* separator = index == 0 ? "" : ", ";
        std::cout << separator << '"' << results[index] << '"';
    }

    std::cout << "]\n";
}

int main() {
    auto job = [](std::string name, int millis, std::uint32_t time, std::uint32_t priority) {
        auto run = [name, millis] {
            std::this_thread::sleep_for(std::chrono::milliseconds(millis));
            return name;
        };
        return Job{run, time, priority};
    };
    const std::vector<Job> jobs = {job("a", 50, 5, 2), job("b", 20, 2, 3), job("c", 30, 3, 1),
                                   job("d", 40, 4, 1)};

    print("fcfs    ", schedule(jobs, 2, Policy::Fcfs));
    print("sjf     ", schedule(jobs, 2, Policy::Sjf));
    print("priority", schedule(jobs, 2, Policy::Priority));
}
