// ch05/sched_sim.cpp: FCFS, SJF, and round-robin, computed by hand inside a simulator.
#include <algorithm>
#include <deque>
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>

struct Job {
    std::string name;
    int arrival;
    int burst;
};

struct Stats {
    int completion;
    int turnaround;
    int wait;
};

// First-Come, First-Served: run jobs in arrival order, each to completion.
std::vector<Stats> fcfs(const std::vector<Job>& jobs) {
    std::vector<Stats> out;
    int t = 0;

    for (const Job& j : jobs) {
        t = std::max(t, j.arrival) + j.burst;
        out.push_back({t, t - j.arrival, t - j.arrival - j.burst});
    }

    return out;
}

// Shortest Job First: the order in which SJF runs jobs that arrive together.
// Running this order with fcfs() gives the SJF schedule.
std::vector<Job> shortest_first(std::vector<Job> jobs) {
    std::stable_sort(jobs.begin(), jobs.end(),
                     [](const Job& a, const Job& b) { return a.burst < b.burst; });
    return jobs;
}

// Round-Robin: rotate through a ready queue in fixed time slices.
std::vector<Stats> rr(const std::vector<Job>& jobs, int quantum) {
    std::deque<int> ready;
    std::vector<int> remaining(jobs.size());
    std::vector<int> completion(jobs.size());

    for (size_t i = 0; i < jobs.size(); ++i) {
        remaining[i] = jobs[i].burst;
        ready.push_back(static_cast<int>(i));
    }

    int t = 0;
    while (!ready.empty()) {
        int i = ready.front();
        ready.pop_front();

        int run = std::min(quantum, remaining[i]);
        t += run;
        remaining[i] -= run;

        if (remaining[i] == 0) {
            completion[i] = t;
        } else {
            ready.push_back(i);
        }
    }

    std::vector<Stats> out;
    for (size_t i = 0; i < jobs.size(); ++i) {
        out.push_back({completion[i], completion[i] - jobs[i].arrival,
                       completion[i] - jobs[i].arrival - jobs[i].burst});
    }

    return out;
}

void report(const std::string& title, const std::vector<Job>& jobs,
            const std::vector<Stats>& stats) {
    double avg_turnaround = 0, avg_wait = 0;

    std::cout << title << "\n";
    std::cout << "  job  completion  turnaround  wait\n";

    for (size_t i = 0; i < jobs.size(); ++i) {
        std::cout << "  " << jobs[i].name << "    "
                  << std::setw(6) << stats[i].completion << "   "
                  << std::setw(6) << stats[i].turnaround << "   "
                  << std::setw(6) << stats[i].wait << "\n";

        avg_turnaround += stats[i].turnaround;
        avg_wait += stats[i].wait;
    }

    avg_turnaround /= jobs.size();
    avg_wait /= jobs.size();

    std::cout << "  average turnaround " << avg_turnaround
              << ", average wait " << avg_wait << "\n\n";
}

int main() {
    const std::vector<Job> jobs = {
        {"A", 0, 10},
        {"B", 0, 5},
        {"C", 0, 5},
    };

    report("FCFS (arrival order)", jobs, fcfs(jobs));

    const std::vector<Job> by_burst = shortest_first(jobs);
    report("SJF  (shortest first)", by_burst, fcfs(by_burst));

    report("RR   (quantum 5)", jobs, rr(jobs, 5));
}
