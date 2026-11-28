// ch19/quantum_sched.cpp: FCFS, SJF, and priority scheduling with a time quantum on one heap.
#include <concepts>
#include <functional>
#include <iostream>
#include <queue>
#include <string>
#include <tuple>
#include <vector>

template <std::invocable F>
struct Job {
    F run;
    unsigned time;
    unsigned priority;  // Smaller priority means higher
};
template <typename F>
Job(F, unsigned, unsigned) -> Job<F>;

using JobState = std::tuple<unsigned, unsigned, size_t, unsigned>;  // (rank, queued at, index, time left)
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
std::vector<T> schedule(const std::vector<Job<F>>& jobs, unsigned quantum, Policy policy) {
    unsigned clock = 0;
    MinHeap heap;
    for (size_t index = 0; index < jobs.size(); ++index) {
        heap.emplace(rank(policy, jobs[index].time, jobs[index].priority), clock, index, jobs[index].time);
    }

    std::vector<T> results;
    while (!heap.empty()) {
        auto [rank_, queued_at, index, left] = heap.top();
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

template <typename T>
void print(const char* label, const std::vector<T>& results) {
    std::cout << label << " [";
    for (size_t i = 0; i < results.size(); ++i) {
        std::cout << (i ? ", \"" : "\"") << results[i] << '"';
    }
    std::cout << "]\n";
}

int main() {
    auto job = [](std::string name, unsigned time, unsigned priority) {
        return Job{[name] { return name + " done"; }, time, priority};
    };
    std::vector jobs = {job("a", 5, 2), job("b", 2, 3), job("c", 3, 1), job("d", 4, 1)};

    print("fcfs    ", schedule(jobs, 2, Policy::Fcfs));
    print("sjf     ", schedule(jobs, 2, Policy::Sjf));
    print("priority", schedule(jobs, 2, Policy::Priority));
}
