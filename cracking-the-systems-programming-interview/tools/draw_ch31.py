"""Figures for chapter 31: scheduling jobs by policy."""
import heapq

from svgkit import *
OUT = "src/figures/"
JOBS = [("a", 5, 2), ("b", 2, 3), ("c", 3, 1), ("d", 4, 1)]
JOB_FILL = {"a": PALE, "b": GREEN, "c": CREAM, "d": PINK}


def quantum_schedule(jobs, quantum, rank):
    """The heap scheduler of shortest_job_first_scheduling.rs, run on paper."""
    clock = 0
    heap = [(rank(time, priority), 0, index, time) for index, (name, time, priority) in enumerate(jobs)]
    heapq.heapify(heap)
    slices = []
    while heap:
        _, _, index, left = heapq.heappop(heap)
        run = min(left, quantum)
        slices.append((jobs[index][0], clock, clock + run, run == left))
        clock += run
        if left > quantum:
            heapq.heappush(heap, (rank(left - quantum, jobs[index][2]), clock, index, left - quantum))
    return slices


def worker_timeline(order, durations, workers):
    """Each idle worker pops the next job in heap order; returns (worker, job, begin, end)."""
    free_at = [0] * workers
    runs = []
    for job in order:
        worker = min(range(workers), key=lambda w: free_at[w])
        begin = free_at[worker]
        free_at[worker] = begin + durations[job]
        runs.append((worker, job, begin, free_at[worker]))
    return runs


# 1. the quantum scheduler under 3 policies
policies = [("Policy::Fcfs", lambda time, priority: 0),
            ("Policy::Sjf", lambda time, priority: time),
            ("Policy::Priority", lambda time, priority: priority)]
f = Figure(760, 330)
f.text(20, 22, "4 jobs on 1 CPU with a quantum of 2: the slice each pop runs, and when each job ends", 12, bold=True)
x0, unit = 140, 42
for r, (name, rank) in enumerate(policies):
    y = 56 + r * 82
    f.text(20, y + 21, name, 11, mono=True, bold=True)
    finished = []
    for job, begin, end, done in quantum_schedule(JOBS, 2, rank):
        f.cell(x0 + begin * unit, y, (end - begin) * unit, 32, job, JOB_FILL[job], size=12)
        if done:
            finished.append(f"{job} at {end}")
    f.text(x0, y + 50, "finished: " + ", ".join(finished), 10, MUTED)
for t in range(0, 15):
    f.text(x0 + t * unit, 302, str(t), 9, MUTED, anchor="middle")
f.text(x0 - 12, 302, "clock", 9, MUTED, anchor="end")
f.text(20, 322, "Jobs: a (time 5, priority 2), b (2, 3), c (3, 1), d (4, 1). A smaller rank pops first.", 10, MUTED)
f.save(OUT + "ch31-quantum-schedule.svg")

# 2. 2 workers popping from 1 priority heap
DURATIONS = {"a": 50, "b": 20, "c": 30, "d": 40}
orders = [("Policy::Fcfs", "abcd"), ("Policy::Sjf", "bcda"), ("Policy::Priority", "cdab")]
f = Figure(760, 400)
f.text(20, 22, "2 workers pop from 1 heap: the pop order is fixed, the finishing order is not", 12, bold=True)
x0, unit = 170, 6
for r, (name, order) in enumerate(orders):
    y = 50 + r * 110
    f.text(20, y + 14, name, 11, mono=True, bold=True)
    f.text(20, y + 32, "pop order: " + ", ".join(order), 10, MUTED)
    runs = worker_timeline(order, DURATIONS, 2)
    for worker in range(2):
        f.text(x0 - 10, y + worker * 34 + 19, f"worker {worker + 1}", 10, MUTED, anchor="end")
    for worker, job, begin, end in runs:
        f.cell(x0 + begin * unit, y + worker * 34, (end - begin) * unit, 28, f"{job}  {begin}-{end} ms", JOB_FILL[job], size=10)
    finishing = ", ".join(job for _, job, _, _ in sorted(runs, key=lambda run: (run[3], run[2])))
    f.text(x0, y + 86, "results: " + finishing, 10, TEAL, mono=True)
f.text(x0 + 300, 50 + 86, "a and c both end at 50 ms: either can be pushed first", 10, RUST)
for t in range(0, 100, 10):
    f.text(x0 + t * unit, 384, f"{t}", 9, MUTED, anchor="middle")
f.text(x0 - 10, 384, "ms", 9, MUTED, anchor="end")
f.save(OUT + "ch31-heap-workers.svg")
print("ok")
