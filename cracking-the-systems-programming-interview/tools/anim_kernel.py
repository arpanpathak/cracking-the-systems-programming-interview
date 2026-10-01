"""The kernel boundary animations (ch23-mmap.md), drawn with `motion`.

    python3 tools/animations.py mmap-faults
"""

import math
import pathlib

from motion import *  # noqa: F401,F403
from motion import Timeline, render

LAB = pathlib.Path(__file__).resolve().parent.parent.parent / "rust-interview-lab"


def lines_at(path, numbers):
    """Lines of a lab source file by number, without their indentation."""
    source = (LAB / path).read_text(encoding="utf-8").splitlines()
    return [source[n - 1].strip() for n in numbers]


# ------------------------------------------------- 23.1: faults on first touch

PAGES = 64
CELL = 17
TABLE = (196, 98)       # top-left of the page table grid
CACHE = (520, 98)       # top-left of the page cache grid
ROBOT_X, DESK = 92, 222
COPY = (356, 196)       # the private copy's frame
DISK = (736, 150)

MAIN = lines_at("src/bin/mmap_file.rs", [138, 141, 145, 151, 152, 159, 160])


def cell_xy(origin, i):
    """Centre of page `i` in an 8 by 8 grid."""
    return (origin[0] + (i % 8) * CELL + CELL / 2, origin[1] + (i // 8) * CELL + CELL / 2)


def mmap_faults():
    tl = Timeline(caption="", kind="step", code=-1.0, awake=1.0, mapped=0.0, filled=0.0,
                  cur=0, cur_a=0.0, hit=0.0, sweep=-1.0, first=0.0, second=0.0,
                  read_u=0.0, read_a=0.0, read_label="read", fault_u=0.0, fault_a=0.0,
                  fill_u=0.0, fill_a=0.0, dirty=0.0, cache0="aaaaa", disk0="aaaaa",
                  sync_u=0.0, sync_a=0.0, table="page table: MAP_SHARED", priv0=0.0,
                  copy_a=0.0, copy_text="aaaaa", copy_u=0.0, copy_fly=0.0, trunc=0.0,
                  missing=0.0, sigbus=0.0)

    def read(i, label="read", dur=0.8):
        """The thread touches page `i`: a request flies from the robot to the entry."""
        tl.set(cur=i, read_label=label, read_u=0.0)
        tl.to(0.2, read_a=1.0, cur_a=1.0)
        tl.to(dur, in_out, read_u=1.0)
        tl.to(0.15, read_a=0.0)

    def fault(i, slow=1.0):
        """The entry is empty: the CPU traps, the kernel finds the page, fills the entry."""
        tl.to(0.3 * slow, back, hit=1.0, awake=0.25)
        tl.set(fault_u=0.0)
        tl.to(0.2, fault_a=1.0)
        tl.to(0.9 * slow, in_out, fault_u=1.0)
        tl.to(0.15, fault_a=0.0)
        tl.set(fill_u=0.0)
        tl.to(0.2, fill_a=1.0)
        tl.to(0.7 * slow, in_out, fill_u=1.0)
        tl.to(0.3, hit=0.0, filled=float(i + 1), first=float(i + 1), awake=1.0)
        tl.to(0.3, fill_a=0.0)

    tl.chapter("mmap")
    tl.say("fs::write has just written the file, so all 64 of its pages are in the page cache.")
    tl.wait(1.0)
    tl.say("Mapping::new calls mmap. The kernel reserves 64 pages of addresses, and fills none "
           "of the 64 page table entries.")
    tl.to(0.4, code=0.0)
    tl.to(0.9, mapped=1.0)
    tl.wait(1.4)

    tl.chapter("first pass")
    tl.say("touch_every_page reads the first byte of page 0. Its page table entry is empty.")
    tl.to(0.4, code=1.0)
    read(0)
    tl.say("The CPU cannot translate the address, so it stops the thread and enters the "
           "kernel: a page fault.")
    tl.to(0.3, back, hit=1.0, awake=0.25)
    tl.wait(1.0)
    tl.say("The kernel finds page 0 in the page cache. No disk read is needed: a minor fault.")
    fault(0, slow=1.4)
    tl.say("It points the entry at the cache's frame, and the read finishes. Page 1 takes the "
           "same path.")
    read(1, dur=0.6)
    fault(1)
    tl.say("So does every other page. Each first touch is one more minor fault.")
    tl.to(6.0, linear, filled=64.0, first=64.0, cur=63)
    tl.to(0.3, cur_a=0.0)
    tl.say("First pass: 64 pages, 64 minor faults, as the macOS run printed.",
           "insight")
    tl.wait(1.6)

    tl.chapter("second pass")
    tl.say("The second pass reads the same 64 pages. Every entry is filled, so no read faults.")
    tl.to(0.4, code=2.0)
    tl.set(sweep=0.0)
    tl.to(4.0, linear, sweep=63.0)
    tl.set(sweep=-1.0)
    tl.say("Second pass: 0 minor faults. Each read costs what any memory read costs.", "insight")
    tl.wait(1.4)

    tl.chapter("HELLO")
    tl.say("Writing HELLO through the shared mapping changes the page cache's own page 0.")
    tl.to(0.4, code=3.0)
    tl.set(cur=0)
    tl.to(0.2, cur_a=1.0)
    read(0, "HELLO")
    tl.to(0.5, dirty=1.0)
    tl.set(cache0="HELLO")
    tl.wait(0.8)
    tl.say("The page is now dirty: newer than the disk. sync calls msync, which writes it to "
           "the disk now.")
    tl.to(0.4, code=4.0)
    tl.set(sync_u=0.0)
    tl.to(0.2, sync_a=1.0)
    tl.to(1.0, in_out, sync_u=1.0)
    tl.to(0.15, sync_a=0.0)
    tl.set(disk0="HELLO")
    tl.to(0.5, dirty=0.0, cur_a=0.0)
    tl.wait(1.2)

    tl.chapter("world")
    tl.say("The shared mapping is dropped. A private mapping of the same file starts with no "
           "entries filled.")
    tl.to(0.4, code=5.0)
    tl.to(0.8, filled=0.0, mapped=0.0)
    tl.set(table="page table: MAP_PRIVATE")
    tl.to(0.8, mapped=1.0)
    tl.say("Writing world to page 0 faults. For a private mapping, the kernel copies the page "
           "into a new frame.")
    tl.to(0.4, code=6.0)
    read(0, "world")
    tl.to(0.3, back, hit=1.0, awake=0.25)
    tl.set(copy_u=0.0, copy_text="HELLO")
    tl.to(0.2, copy_fly=1.0)
    tl.to(1.0, in_out, copy_u=1.0)
    tl.to(0.15, copy_fly=0.0)
    tl.to(0.5, copy_a=1.0)
    tl.to(0.4, priv0=1.0, hit=0.0, awake=1.0)
    tl.wait(0.4)
    tl.set(copy_text="world")
    tl.wait(1.0)
    tl.say("The entry points at the copy, and only the copy holds world. The page cache and the "
           "file still hold HELLO.", "insight")
    tl.wait(1.8)

    tl.chapter("truncated")
    tl.say("Now suppose the shared mapping is still alive, and another process truncates the "
           "file to one page.", "fail")
    tl.to(0.5, copy_a=0.0, priv0=0.0, cur_a=0.0)
    tl.set(table="page table: MAP_SHARED")
    tl.to(0.8, filled=64.0, first=64.0)
    tl.to(1.2, trunc=1.0, filled=1.0)
    tl.say("The kernel drops pages 1 to 63 from the page cache and empties their entries.",
           "fail")
    tl.wait(1.2)
    tl.say("Reading page 1 faults, and the kernel has no page to give. It sends SIGBUS, and "
           "the process dies.", "fail")
    tl.to(0.4, code=1.0)
    read(1)
    tl.to(0.3, back, hit=1.0, awake=0.25)
    tl.set(fault_u=0.0)
    tl.to(0.2, fault_a=1.0)
    tl.to(0.9, in_out, fault_u=1.0)
    tl.to(0.3, back, missing=1.0)
    tl.to(0.15, fault_a=0.0)
    tl.to(0.4, back, sigbus=1.0, awake=0.0)
    tl.say("A read call would have returned 0 bytes. A mapping has no return value, so the "
           "error arrives as a signal.", "fail")
    tl.wait(2.0)

    def grid(p, origin, s, color, fill, count, label):
        p.text(origin[0], origin[1] - 10, label, 11, MUTED, 600)
        for i in range(PAGES):
            x = origin[0] + (i % 8) * CELL
            y = origin[1] + (i // 8) * CELL
            on = i < count
            p.rect(x + 1, y + 1, CELL - 2, CELL - 2, fill if on else PAPER,
                   color if on else LINE, 3, 1.1)

    def draw(p, s, total):
        t = s.t
        title_block(p, "Mapping a file: one fault per page",
                    "mmap fills no page table entries. The first touch of each page does.")
        scoreboard(p, [("first pass", int(s.first), RUST), ("second", int(s.second), TEAL)],
                   y=34)

        robot(p, ROBOT_X, DESK, TEAL, s.awake, s.awake, "main", "mmap_file", look=0.9)
        if s.sigbus > 0.01:
            with p.group(opacity=clamp(s.sigbus)):
                chip(p, ROBOT_X, DESK - 140, "SIGBUS", RUST, RUST_LT, 13)

        # the process's page table
        with p.group(opacity=clamp(s.mapped)):
            filled = int(math.floor(s.filled + 1e-6))
            grid(p, TABLE, s, TEAL, TEAL_LT, filled, s.table)
            if s.priv0 > 0.01:
                x, y = TABLE
                p.rect(x + 1, y + 1, CELL - 2, CELL - 2, BRASS_LT, BRASS, 3, 1.4,
                       opacity=clamp(s.priv0))
                a = cell_xy(TABLE, 0)
                p.line(a[0] + 6, a[1] + 4, COPY[0] - 4, COPY[1] + 12, BRASS, 1.6,
                       dash="4 3", opacity=clamp(s.priv0))
            p.text(TABLE[0], TABLE[1] + 8 * CELL + 16, "64 entries, one per page", 10.5, MUTED)
        if s.cur_a > 0.01:
            x, y = cell_xy(TABLE, int(s.cur))
            p.rect(x - CELL / 2 - 3, y - CELL / 2 - 3, CELL + 6, CELL + 6, "none",
                   RUST if s.hit > 0.5 else BRASS, 5, 2.2, opacity=clamp(s.cur_a))
        if s.sweep >= 0:
            x, y = cell_xy(TABLE, int(s.sweep))
            p.rect(x - CELL / 2 - 3, y - CELL / 2 - 3, CELL + 6, CELL + 6, "none", TEAL, 5, 2.2)
        if s.hit > 0.01 and s.sigbus < 0.5:
            pill(p, ROBOT_X, DESK - 140, "page fault", RUST, RUST_LT, 10.5,
                 opacity=clamp(s.hit), shadow=None)

        # the kernel: page cache and disk
        p.rect(476, 70, W - 26 - 476, 196, "none", FAINT, 10, 1.2, dash="5 4")
        p.text(W - 38, 88, "kernel", 11, MUTED, 600, "end")
        cached = 1 if s.trunc > 0.5 else PAGES
        grid(p, CACHE, s, TEAL, "#cfe6ea", cached, "page cache: the file's pages")
        if s.dirty > 0.01:
            x, y = CACHE
            p.rect(x + 1, y + 1, CELL - 2, CELL - 2, BRASS, BRASS, 3, 1.2, opacity=clamp(s.dirty))
        p.text(CACHE[0], CACHE[1] + 8 * CELL + 16, "page 0: " + s.cache0 + "...", 10.5, INK,
               600, mono=True)
        if s.missing > 0.01:
            x, y = cell_xy(CACHE, 1)
            pill(p, x + 20, y + 28, "no page 1", RUST, RUST_LT, 10.5, opacity=clamp(s.missing),
                 shadow=None)

        dx, dy = DISK
        p.path("M %s %s v 44 a 30 9 0 0 0 60 0 v -44" % (dx - 30, dy), fill="#e6ebf0",
               stroke=INK, width=1.4)
        p.path("M %s %s a 30 9 0 1 0 60 0 a 30 9 0 1 0 -60 0" % (dx - 30, dy), fill="#eef3f7",
               stroke=INK, width=1.4)
        p.text(dx, dy + 74, "file on disk", 10.5, MUTED, 600, "middle")
        p.text(dx, dy + 30, "1 page" if s.trunc > 0.5 else s.disk0, 11, INK, 700, "middle",
               mono=True)

        # the private copy
        if s.copy_a > 0.01:
            with p.group(opacity=clamp(s.copy_a)):
                x, y = COPY
                p.rect(x, y, 96, 40, BRASS_LT, BRASS, 6, 1.4)
                p.text(x + 48, y + 16, "private copy", 10, MUTED, 600, "middle")
                p.text(x + 48, y + 32, s.copy_text, 12, INK, 700, "middle", mono=True)

        # things in flight
        if s.read_a > 0.01:
            a = (ROBOT_X + 40, DESK - 110)
            b = cell_xy(TABLE, int(s.cur))
            x, y = bezier(a, ((a[0] + b[0]) / 2, 74), b, s.read_u)
            pill(p, x, y, s.read_label, TEAL, PAPER, 10.5, opacity=s.read_a)
        if s.fault_a > 0.01:
            a = cell_xy(TABLE, int(s.cur))
            b = cell_xy(CACHE, int(s.cur))
            x, y = bezier(a, ((a[0] + b[0]) / 2, 76), b, s.fault_u)
            pill(p, x, y, "find page %d" % int(s.cur), RUST, RUST_LT, 10.5, opacity=s.fault_a)
        if s.fill_a > 0.01:
            a = cell_xy(CACHE, int(s.cur))
            b = cell_xy(TABLE, int(s.cur))
            e = (lerp(a[0], b[0], s.fill_u), lerp(a[1], b[1], s.fill_u))
            p.line(a[0], a[1], e[0], e[1], TEAL, 2.0, opacity=s.fill_a)
            p.circle(e[0], e[1], 3.5, TEAL, opacity=s.fill_a)
        if s.sync_a > 0.01:
            a = cell_xy(CACHE, 0)
            b = (DISK[0], DISK[1] - 4)
            x, y = bezier(a, ((a[0] + b[0]) / 2, 80), b, s.sync_u)
            pill(p, x, y, "msync", BRASS, BRASS_LT, 10.5, opacity=s.sync_a)
        if s.copy_fly > 0.01:
            a = cell_xy(CACHE, 0)
            b = (COPY[0] + 48, COPY[1] + 20)
            x, y = bezier(a, ((a[0] + b[0]) / 2, COPY[1] + 70), b, s.copy_u)
            pill(p, x, y, "copy page 0", BRASS, BRASS_LT, 10.5, opacity=s.copy_fly)

        code_panel(p, 26, 282, W - 52, "main", MAIN, s.code, size=10.6, lead=16.0,
                   reveal=s.timeline.reached("code", t))
        caption(p, tl, t, 448)
        progress(p, tl, t, total, 534)

    return tl, draw, 566


def build_mmap_faults(only=None):
    tl, draw, height = mmap_faults()
    return render("ch23-faults.gif", tl, draw, height, only=only)


BUILDERS = {
    "mmap-faults": build_mmap_faults,
}

if __name__ == "__main__":
    import sys
    for name in sys.argv[1:] or BUILDERS:
        print(BUILDERS[name]())
