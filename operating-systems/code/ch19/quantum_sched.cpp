// ch19/quantum_sched.cpp: FCFS, SJF, and priority scheduling with a time quantum on one heap.
#include <cstdint>
#include <functional>
#include <iostream>
#include <queue>
#include <string>
#include <tuple>
#include <vector>

struct Job {
    std::function<std::string()> run;
    std::uint32_t time;
    std::uint32_t priority;  // A smaller number means a more urgent job.
};

// (rank, queued at, index, time left). std::greater makes the smallest tuple pop first.
using JobState = std::tuple<std::uint32_t, std::uint32_t, std::size_t, std::uint32_t>;
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

std::vector<std::string> schedule(const std::vector<Job>& jobs, std::uint32_t quantum,
                                  Policy policy) {
    std::uint32_t clock = 0;
    MinHeap heap;

    for (std::size_t index = 0; index < jobs.size(); ++index) {
        const Job& job = jobs[index];
        heap.emplace(rank(policy, job.time, job.priority), clock, index, job.time);
    }

    std::vector<std::string> results;
    while (!heap.empty()) {
        auto [unused_rank, unused_queued_at, index, left] = heap.top();
        heap.pop();

        if (left > quantum) {
            clock += quantum;
            left -= quantum;
            heap.emplace(rank(policy, left, jobs[index].priority), clock, index, left);
            continue;
        }

        clock += left;
        results.push_back(jobs[index].run());
    }

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
    auto job = [](std::string name, std::uint32_t time, std::uint32_t priority) {
        return Job{[name] { return name + " done"; }, time, priority};
    };
    const std::vector<Job> jobs = {job("a", 5, 2), job("b", 2, 3), job("c", 3, 1),
                                   job("d", 4, 1)};

    print("fcfs    ", schedule(jobs, 2, Policy::Fcfs));
    print("sjf     ", schedule(jobs, 2, Policy::Sjf));
    print("priority", schedule(jobs, 2, Policy::Priority));
}
