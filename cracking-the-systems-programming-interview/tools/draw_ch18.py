"""Figures for chapter 18: thread pools."""
from svgkit import *
OUT = "src/figures/"

# 1. anatomy
f = Figure(760, 250)
f.text(20, 22, "The parts of every pool in this chapter", 12, bold=True)
f.cell(20, 90, 120, 34, "execute(job)", GREEN, size=10)
f.arrow(140, 107, 180, 107)
f.cell(180, 90, 110, 34, "Sender<Job>", CREAM, size=10)
f.arrow(290, 107, 320, 107)
for i in range(4):
    f.rect(322 + i * 32, 94, 28, 26, PALE, INK, 3)
f.text(386, 140, "channel: jobs in order", 9, MUTED, anchor="middle")
f.arrow(452, 107, 490, 107)
f.cell(490, 86, 150, 42, "Arc<Mutex<Receiver>>", CREAM, size=9)
for i in range(4):
    y = 40 + i * 34
    f.arrow(640, 107, 670, y + 14, MUTED, 1.1)
    f.cell(670, y, 80, 28, f"worker {i}", GREEN if i != 2 else PALE, size=10)
f.text(20, 190, "Job = Box<dyn FnOnce() + Send + 'static>: any closure, moved to the heap, runnable once on another thread.", 10)
f.text(20, 208, "The channel has one Receiver, so the workers share it behind an Arc<Mutex<...>>. A worker locks it to take a job.", 10)
f.text(20, 226, "Dropping the Sender closes the channel: recv() then returns Err, and each worker leaves its loop.", 10, MUTED)
f.save(OUT + "pool-parts.svg")

# 2. lock held during the job
f = Figure(760, 250)
f.text(20, 22, "Four jobs that sleep 200 ms on four workers, measured with each loop shape", 12, bold=True)
scale = 0.8
f.text(20, 56, "while let Ok(job) = rx.lock().unwrap().recv() { job(); }", 10, mono=True)
for i in range(4):
    f.cell(20 + i * 200 * scale, 66, 200 * scale, 24, f"worker {i}: job", PINK, size=9)
f.text(20 + 800 * scale + 8, 83, "814 ms", 11, RUST, bold=True)
f.text(20, 114, "The guard is a temporary of the while-let condition, so the lock stays held until the job ends.", 10, MUTED)
f.text(20, 152, "let job = rx.lock().unwrap().recv(); match job { ... }", 10, mono=True)
for i in range(4):
    f.cell(20, 162 + i * 16, 200 * scale, 14, "", GREEN, size=8)
    f.text(24, 173 + i * 16, f"worker {i}", 8)
f.text(20 + 200 * scale + 8, 200, "205 ms", 11, TEAL, bold=True)
f.text(20, 240, "The guard is a temporary of the let statement, so the lock is released before the job runs.", 10, MUTED)
f.save(OUT + "pool-lock-held.svg")

# 3. shutdown
f = Figure(760, 200)
f.text(20, 22, "Shutting down: close the channel, let the workers drain it, then join them", 12, bold=True)
steps = [("drop the Sender", CREAM), ("workers finish the\njobs still queued", GREEN), ("recv() returns Err:\nno sender, no jobs", PALE),
         ("each worker loop\nbreaks", PALE), ("join() each\nJoinHandle", GREEN)]
for i, (t, fill) in enumerate(steps):
    x = 20 + i * 148
    f.rect(x, 60, 132, 56, fill, INK, 4)
    for j, line in enumerate(t.split("\n")):
        f.text(x + 66, 84 + j * 16, line, 10, anchor="middle")
    if i:
        f.arrow(x - 14, 88, x, 88)
f.text(20, 150, "Version 1 and version 2 do this in join(self). Versions 3 and later also do it in Drop,", 10)
f.text(20, 168, "so a pool that goes out of scope still finishes its queued jobs.", 10)
f.save(OUT + "pool-shutdown.svg")

# 4. catch_unwind
f = Figure(760, 220)
f.text(20, 22, "Version 4 runs each job inside catch_unwind", 12, bold=True)
f.cell(20, 60, 170, 30, "worker takes a job", PALE, size=10)
f.arrow(190, 75, 230, 75)
f.cell(230, 60, 220, 30, "catch_unwind(AssertUnwindSafe(job))", CREAM, size=9)
f.arrow(450, 70, 500, 50, TEAL); f.arrow(450, 80, 500, 110, RUST)
f.cell(500, 36, 240, 28, "Ok(()): completed += 1", GREEN, size=10)
f.cell(500, 96, 240, 28, "Err(panic): panicked += 1", PINK, size=10)
f.text(20, 160, "The panic stops at catch_unwind. The worker thread survives and takes the next job.", 10)
f.text(20, 178, "Without it, a panicking job unwinds out of the worker's closure and ends the thread: the pool silently shrinks.", 10)
f.text(20, 200, "The default panic hook still prints the panic message to standard error.", 10, MUTED)
f.save(OUT + "pool-catch-unwind.svg")

# 5. ordered results
f = Figure(760, 250)
f.text(20, 22, "map_order: tag each input with its index, and put each result back in its slot", 12, bold=True)
f.text(20, 50, "jobs sent", 10, MUTED)
for i in range(5):
    f.cell(20 + i * 70, 58, 66, 26, f"({i}, x{i})", PALE, size=9)
f.text(400, 50, "results arrive in finishing order", 10, MUTED)
for k, i in enumerate([1, 0, 3, 4, 2]):
    f.cell(400 + k * 70, 58, 66, 26, f"({i}, r{i})", CREAM, size=9)
f.arrow(380, 71, 398, 71, MUTED)
f.text(20, 128, "ordered: Vec<Option<R>>, indexed by the tag", 10, MUTED)
for i in range(5):
    f.cell(20 + i * 70, 136, 66, 26, f"Some(r{i})", GREEN, size=9)
    f.text(53 + i * 70, 178, str(i), 9, MUTED, anchor="middle")
f.text(400, 150, "ordered[idx] = Some(value)", 10, TEAL, mono=True)
f.text(20, 220, "The result channel ends when every worker has dropped its Sender clone, so iter() stops after the last result.", 10, MUTED)
f.save(OUT + "pool-ordered.svg")
print("ok")
