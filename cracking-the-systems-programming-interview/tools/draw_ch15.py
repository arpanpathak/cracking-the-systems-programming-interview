"""Figures for chapter 15: memory, CPU caches, and the operating system."""
import math
from svgkit import *
OUT = "src/figures/"

# 1. the hierarchy, with measured latencies
f = Figure(760, 290)
f.text(20, 22, "Memory latency on an Intel Core i5-1038NG7, measured with a dependent pointer chase", 12, bold=True)
rows = [("16 KiB", "fits in L1 (48 KiB per core)", 2.2, GREEN), ("256 KiB", "fits in L2 (512 KiB per core)", 5.6, GREEN),
        ("2 MiB", "fits in L3 (6 MiB, shared)", 42.3, CREAM), ("32 MiB", "main memory", 120.0, PINK),
        ("256 MiB", "main memory", 146.2, PINK)]
f.text(20, 52, "data size", 10, MUTED); f.text(110, 52, "where it fits", 10, MUTED); f.text(330, 52, "time per dependent load", 10, MUTED)
for i, (size, where, ns, fill) in enumerate(rows):
    y = 62 + i * 36
    f.text(20, y + 18, size, 11, mono=True); f.text(110, y + 18, where, 10)
    w = max(4, math.log10(ns + 1) / math.log10(150) * 330)
    f.rect(330, y, w, 26, fill, INK, 3)
    f.text(338 + w, y + 18, f"{ns} ns", 11, mono=True)
f.text(20, 256, "Each load's address comes from the previous load, so the loads cannot overlap. The bar length is logarithmic.", 10, MUTED)
f.text(20, 272, "The larger sizes also pay for address translation misses (section 15.5). A cache line is 64 bytes on this CPU.", 10, MUTED)
f.save(OUT + "mem-latency.svg")

# 2. bump allocation
f = Figure(760, 190)
f.text(20, 22, "A 64-byte arena after alloc(1, 8) and alloc(4, 16)", 12, bold=True)
x0, cw = 20, 11
for b in range(64):
    fill = GREEN if b == 0 else (GREY if b < 16 else (CREAM if b < 20 else "#ffffff"))
    f.rect(x0 + b * cw, 50, cw, 30, fill, INK if b in (0, 16, 20) else "#b8c2cc", 0, width=0.8)
for b in (0, 8, 16, 24, 32, 48, 63):
    f.text(x0 + b * cw + cw / 2, 96, str(b), 9, MUTED, anchor="middle")
f.text(20, 124, "byte 0: the first block (1 byte, aligned to 8)", 10)
f.text(20, 142, "bytes 1 to 15: padding, so the next block starts at a multiple of 16", 10, MUTED)
f.text(20, 160, "bytes 16 to 19: the second block (4 bytes)", 10)
f.text(430, 124, "offset after both calls: 20", 10, TEAL, mono=True)
f.text(430, 142, "used() = 20, remaining() = 44", 10, TEAL, mono=True)
f.text(20, 180, "reset() sets the offset back to 0 and frees every block at once. No single block can be freed.", 10, MUTED)
f.save(OUT + "bump.svg")

# 3. cache lines: sequential against scattered
f = Figure(760, 230)
f.text(20, 22, "A cache line holds 8 u64 values. The order of access decides how many lines each load brings in", 12, bold=True)
f.text(20, 50, "in order: one line serves 8 loads, and the prefetcher fetches the next line early", 10, MUTED)
for line in range(6):
    for k in range(8):
        f.rect(20 + line * 120 + k * 14, 60, 14, 24, GREEN if line < 3 else PALE, INK if k == 0 else "#b8c2cc", 0, width=0.8)
    f.text(20 + line * 120 + 56, 100, f"line {line}", 9, MUTED, anchor="middle")
f.text(20, 136, "scattered: each load needs a different line, and 7 of its 8 values go unused", 10, MUTED)
hit = {1: 3, 4: 6, 0: 1, 5: 2, 2: 7, 3: 0}
for line in range(6):
    for k in range(8):
        used = hit[line] == k
        f.rect(20 + line * 120 + k * 14, 146, 14, 24, PINK if used else "#ffffff", INK if k == 0 else "#b8c2cc", 0, width=0.8)
    f.text(20 + line * 120 + 56, 186, f"line {line}", 9, MUTED, anchor="middle")
f.text(20, 216, "Both patterns read 6 values. The first reads 1 line of memory; the second reads 6.", 10, MUTED)
f.save(OUT + "cache-lines.svg")

# 4. false sharing
f = Figure(760, 280)
f.text(20, 22, "False sharing: two cores write different counters that sit on the same cache line", 12, bold=True)
def core(x, y, name):
    f.rect(x, y, 120, 44, PALE, INK, 6); f.text(x + 60, y + 18, name, 11, anchor="middle", bold=True)
    f.text(x + 60, y + 34, "own L1 cache", 9, MUTED, anchor="middle")
core(40, 50, "core 0"); core(600, 50, "core 1")
f.rect(250, 58, 260, 28, PINK, RUST, 3)
f.rect(250, 58, 32, 28, CREAM, INK, 0); f.text(266, 77, "a", 11, mono=True, anchor="middle")
f.rect(282, 58, 32, 28, CREAM, INK, 0); f.text(298, 77, "b", 11, mono=True, anchor="middle")
f.text(410, 77, "one 64-byte line", 10, RUST, anchor="middle")
f.arrow(160, 66, 248, 66, RUST); f.arrow(248, 80, 160, 80, RUST, dash=True)
f.arrow(600, 66, 512, 66, RUST); f.arrow(512, 80, 600, 80, RUST, dash=True)
f.text(380, 118, "Each write needs the line in its own core's cache, in exclusive state.", 10, anchor="middle")
f.text(380, 134, "The line moves back and forth between the cores on almost every increment.", 10, anchor="middle")
core(40, 170, "core 0"); core(600, 170, "core 1")
f.rect(200, 178, 140, 28, GREEN, TEAL, 3); f.rect(200, 178, 32, 28, CREAM, INK, 0); f.text(216, 197, "a", 11, mono=True, anchor="middle")
f.text(290, 197, "line 1", 10, TEAL, anchor="middle")
f.rect(420, 178, 140, 28, GREEN, TEAL, 3); f.rect(420, 178, 32, 28, CREAM, INK, 0); f.text(436, 197, "b", 11, mono=True, anchor="middle")
f.text(510, 197, "line 2", 10, TEAL, anchor="middle")
f.arrow(160, 192, 198, 192, TEAL); f.arrow(600, 192, 562, 192, TEAL)
f.text(380, 238, "With #[repr(align(64))], each counter has its own line, and each core keeps its line.", 10, anchor="middle")
f.text(380, 256, "The program is the same. Only the placement of the counters in memory differs.", 10, MUTED, anchor="middle")
f.save(OUT + "false-sharing.svg")

# 5. paging
f = Figure(760, 306)
f.text(20, 22, "A virtual address is a page number and an offset. The page table maps pages to physical frames", 12, bold=True)
f.text(20, 52, "address 0x1234 with 4096-byte pages (12 offset bits)", 10, MUTED)
f.cell(20, 60, 160, 30, "page 0x1", CREAM, size=11); f.cell(180, 60, 160, 30, "offset 0x234", GREEN, size=11)
f.text(100, 106, "0x1234 / 4096 = 1", 10, MUTED, mono=True, anchor="middle"); f.text(260, 106, "0x1234 % 4096 = 0x234", 10, MUTED, mono=True, anchor="middle")
f.text(20, 140, "page table of one process", 10, MUTED)
entries = [("page 0", "frame 7", "present, read-only", PALE), ("page 1", "frame 3", "present, writable", GREEN),
           ("page 2", "on disk", "not present", PINK), ("page 3", "no entry", "unmapped", GREY)]
for i, (p, fr, st, fill) in enumerate(entries):
    y = 150 + i * 30
    f.cell(20, y, 80, 26, p, CREAM, size=10); f.cell(100, y, 90, 26, fr, fill, size=10); f.text(200, y + 17, st, 10)
f.text(420, 60, "Accessing a page raises a page fault when:", 11, bold=True)
faults = [("the page has no mapping", "invalid: the program crashes (SIGSEGV)"),
          ("the access breaks the page's permission", "protection: usually a crash"),
          ("the page is mapped but not in memory", "the kernel loads it, then retries"),
          ("the kernel must fix the entry first", "minor: e.g. copy-on-write, first touch")]
for i, (cond, res) in enumerate(faults):
    f.text(420, 88 + i * 42, cond, 10)
    f.text(430, 104 + i * 42, res, 10, TEAL)
f.text(20, 298, "A major fault reads from disk and costs milliseconds. A minor fault only updates tables and costs microseconds.", 10, MUTED)
f.save(OUT + "paging.svg")

# 6. round robin
f = Figure(760, 190)
f.text(20, 22, "Round robin with a 5 ms quantum: each runnable task gets one slice in turn", 12, bold=True)
colors = {"encoder": GREEN, "decoder": CREAM, "gc": PINK}
order = ["encoder", "decoder", "gc", "encoder", "decoder", "gc", "encoder"]
for i, t in enumerate(order):
    f.cell(20 + i * 100, 50, 100, 36, t, colors[t], size=11)
    f.text(20 + i * 100, 102, f"{i * 5}", 9, MUTED, anchor="middle")
f.text(720, 102, "35 ms", 9, MUTED, anchor="middle")
f.line(120, 118, 320, 118, TEAL, 1.4)
f.line(120, 112, 120, 124, TEAL); f.line(320, 112, 320, 124, TEAL)
f.text(220, 138, "encoder waits 10 ms between its slices: two other tasks x 5 ms", 10, TEAL, anchor="middle")
f.text(20, 172, "A task that still has work is stopped at the end of its slice and goes to the back of the line.", 10, MUTED)
f.save(OUT + "round-robin.svg")

# 7. system call
f = Figure(760, 240)
f.text(20, 22, "A system call crosses from user mode into the kernel and back", 12, bold=True)
f.rect(20, 44, 720, 70, PALE, INK, 6); f.text(34, 62, "user mode: your program and libc", 10, MUTED)
f.rect(20, 130, 720, 70, CREAM, INK, 6); f.text(34, 148, "kernel mode", 10, MUTED)
f.cell(60, 72, 140, 30, "getppid()", GREEN, size=11)
f.arrow(200, 90, 260, 160, RUST); f.cell(260, 158, 170, 30, "save state, check, run", "#ffffff", size=10)
f.arrow(430, 160, 490, 90, RUST); f.cell(490, 72, 110, 30, "return", GREEN, size=11)
f.text(620, 92, "594 ns", 11, RUST, bold=True)
f.text(20, 222, "macOS libc answers getpid() from a value it stored in the process, so that call never enters the kernel: 3 ns.", 10, MUTED)
f.save(OUT + "syscall.svg")
print("ok")
