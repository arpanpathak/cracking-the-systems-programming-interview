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


def block_at(path, first, last):
    """Lines `first` to `last` of a lab source file, with their common indentation removed."""
    source = (LAB / path).read_text(encoding="utf-8").splitlines()[first - 1:last]
    indent = min(len(line) - len(line.lstrip()) for line in source if line.strip())
    return [line[indent:] for line in source]


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


# ------------------------------------------------- 24.3: a pipeline, by hand

PIPE_CODE = lines_at("src/bin/fd_table.rs", range(158, 166))
ROW_H = 18
PROCS = {"parent": (88, 156), "ls": (350, 418), "wc": (600, 668)}   # robot x, table x
PDESK = 196
PIPE_Y = 266
PIPE_X0, PIPE_X1 = 360, 740
NAMES = ["a.txt", "b.txt", "c.txt"]


def fd_table(p, x, rows, opacity=1.0):
    """Descriptors 0 to 4 and what each points at."""
    colors = {"tty": MUTED, "read end": TEAL, "write end": BRASS, "closed": FAINT}
    with p.group(opacity=opacity):
        p.text(x, 80, "fd table", 10.5, MUTED, 600)
        for i, label in enumerate(rows.split("|")):
            y = 88 + i * ROW_H
            p.rect(x, y, 96, ROW_H - 2, PAPER if label != "closed" else STAGE, LINE, 3, 1.0)
            p.text(x + 8, y + 12, str(i), 10.5, INK, 700, mono=True)
            color = colors.get(label, INK)
            p.text(x + 24, y + 12, label, 10.5, color, 700 if label in ("read end", "write end")
                   else 400, mono=True)


def pipeline():
    start = "tty|tty|tty|-|-"
    tl = Timeline(caption="", kind="step", code=-1.0, strike=-1.0,
                  parent=start, ls="tty|tty|tty|read end|write end",
                  wc="tty|tty|tty|read end|write end", ls_a=0.0, wc_a=0.0,
                  writers=0.0, pipe_a=0.0, fill=0.0, fly_u=0.0, fly_a=0.0, fly_label="",
                  ls_awake=1.0, ls_gone=0.0, wc_awake=1.0, wc_count=0.0, eof=0.0,
                  printed=0.0, clock="", focus_row=-1.0, focus_who="parent")

    def mark(who, row):
        tl.set(focus_who=who, focus_row=float(row))

    def run(keep_write_end):
        def chapter(label):
            if not keep_write_end:
                tl.chapter(label)

        chapter("fork ls")
        tl.set(code=0.0)
        tl.say("pipe creates the two ends in the parent's table: fd 3 is the read end, and fd 4 "
               "the write end.")
        mark("parent", 3)
        tl.to(0.6, pipe_a=1.0, writers=1.0)
        tl.set(parent="tty|tty|tty|read end|write end")
        tl.wait(1.2)

        tl.to(0.3, code=1.0)
        tl.say("fork copies the parent's table into the ls child. Two processes now hold the "
               "write end.")
        mark("ls", 4)
        tl.to(0.8, back, ls_a=1.0, writers=2.0)
        tl.wait(0.8)
        tl.say("In the child, dup2 points fd 1 at the write end. That is a third write end.")
        mark("ls", 1)
        tl.set(ls="tty|write end|tty|read end|write end")
        tl.to(0.5, writers=3.0)
        tl.wait(0.8)
        tl.say("exec starts ls. fds 3 and 4 are close-on-exec, so exec closes them. fd 1 stays.")
        tl.set(ls="tty|write end|tty|closed|closed")
        tl.to(0.5, writers=2.0)
        tl.wait(1.0)

        chapter("fork wc")
        tl.to(0.3, code=2.0)
        tl.say("The same for wc: fork, dup2 the read end onto fd 0, and exec closes 3 and 4.")
        mark("wc", 0)
        tl.to(0.8, back, wc_a=1.0, writers=3.0)
        tl.set(wc="read end|tty|tty|read end|write end")
        tl.wait(0.6)
        tl.set(wc="read end|tty|tty|closed|closed")
        tl.to(0.5, writers=2.0)
        tl.wait(1.0)

        chapter("close")
        tl.to(0.3, code=3.0)
        tl.say("The parent drops its read end. It will never read from this pipe.")
        mark("parent", 3)
        tl.set(parent="tty|tty|tty|closed|write end")
        tl.wait(1.2)
        if keep_write_end:
            tl.say("drop(write_end) is gone, so the parent still holds fd 4. Two write ends stay "
                   "open.", "fail")
            mark("parent", 4)
            tl.wait(1.4)
        else:
            tl.to(0.3, code=4.0)
            tl.say("The parent drops its write end. Now ls's fd 1 is the only write end.")
            mark("parent", 4)
            tl.set(parent="tty|tty|tty|closed|closed")
            tl.to(0.5, writers=1.0)
            tl.wait(1.2)

        chapter("data")
        tl.to(0.3, code=6.0)
        tl.set(focus_row=-1.0)
        tl.say("ls writes three names into the pipe, and wc reads them.")
        for k, name in enumerate(NAMES):
            tl.set(fly_label=name, fly_u=0.0)
            tl.to(0.15, fly_a=1.0)
            tl.to(0.7 if k == 0 else 0.45, in_out, fly_u=1.0)
            tl.to(0.1, fly_a=0.0)
            tl.to(0.2, fill=float(k + 1))
        tl.to(0.6, fill=0.0, wc_count=3.0)
        tl.say("The pipe is empty, so wc's next read waits. It cannot tell yet whether more is "
               "coming.")
        tl.to(0.5, wc_awake=0.0)
        tl.wait(1.0)
        tl.say("ls finishes and exits. Its fd 1 closes with it.")
        mark("ls", 1)
        tl.to(0.6, ls_awake=0.0, ls_gone=1.0)
        tl.set(ls="closed|closed|closed|closed|closed")
        tl.set(focus_row=-1.0)
        if keep_write_end:
            tl.to(0.4, writers=1.0)
            tl.say("The parent's fd 4 is still a write end. wc's read never returns 0.", "fail")
            mark("parent", 4)
            for label in ("1 s", "10 s", "1 min", "forever"):
                tl.set(clock=label)
                tl.wait(0.9)
            tl.say("Nothing uses the CPU and nothing reports an error. The pipeline hangs.",
                   "fail")
            tl.wait(1.6)
        else:
            tl.to(0.4, writers=0.0)
            tl.say("No write end is left, so wc's read returns 0: end-of-file. wc prints 3.",
                   "insight")
            tl.to(0.4, back, wc_awake=1.0, eof=1.0)
            tl.to(0.5, printed=1.0)
            tl.to(0.3, code=7.0)
            tl.wait(1.6)

    run(keep_write_end=False)
    tl.chapter("write end kept")
    tl.say("Now run it again with drop(write_end) removed.", "fail")
    tl.to(0.6, ls_a=0.0, wc_a=0.0, pipe_a=0.0, printed=0.0, eof=0.0, wc_count=0.0,
          writers=0.0)
    tl.set(parent=start, ls="tty|tty|tty|read end|write end",
           wc="tty|tty|tty|read end|write end", ls_awake=1.0, ls_gone=0.0, wc_awake=1.0,
           strike=4.0, code=-1.0)
    tl.wait(0.6)
    run(keep_write_end=True)

    def draw(p, s, total):
        t = s.t
        title_block(p, "ls | wc -l, built by hand",
                    "The reader sees end-of-file when the last write end closes, in any process.")
        scoreboard(p, [("write ends open", int(round(s.writers)), BRASS)])

        robot(p, PROCS["parent"][0], PDESK, TEAL, 1.0, 1.0, "parent", "fd_table")
        fd_table(p, PROCS["parent"][1], s.parent)
        for who, alpha, awake in (("ls", s.ls_a, s.ls_awake), ("wc", s.wc_a, s.wc_awake)):
            if alpha > 0.01:
                with p.group(opacity=clamp(alpha)):
                    gone = who == "ls" and s.ls_gone > 0.5
                    robot(p, PROCS[who][0], PDESK, FAINT if gone else NIGHT, awake, awake, who,
                          "exited" if gone else "child")
                    fd_table(p, PROCS[who][1], getattr(s, who))
        if s.focus_row >= 0:
            x = PROCS[s.focus_who][1]
            y = 88 + s.focus_row * ROW_H
            focus(p, x, y, 96, ROW_H - 2, 1.0, pad=3)
        if s.wc_awake < 0.5 and s.wc_a > 0.5:
            zzz(p, PROCS["wc"][0] + 44, PDESK - 108, t, 1 - s.wc_awake)
            p.text(PROCS["wc"][1] + 48, 214, "read waits", 11, NIGHT, 700, "middle")
        if s.clock:
            p.text(PROCS["wc"][1] + 48, 232, s.clock, 12, RUST, 700, "middle", mono=True)

        # the pipe
        if s.pipe_a > 0.01:
            with p.group(opacity=clamp(s.pipe_a)):
                p.rect(PIPE_X0, PIPE_Y, PIPE_X1 - PIPE_X0, 26, "#e6ecf6", INK, 13, 1.4)
                p.text(PIPE_X0 - 8, PIPE_Y + 17, "write end", 10.5, BRASS, 700, "end")
                p.text(PIPE_X1 + 8, PIPE_Y + 17, "read", 10.5, TEAL, 700)
                p.text((PIPE_X0 + PIPE_X1) / 2, PIPE_Y + 42, "pipe buffer (kernel)", 10.5, MUTED,
                       600, "middle")
                for k in range(int(math.floor(s.fill + 1e-6))):
                    chip(p, PIPE_X1 - 60 - 76 * k, PIPE_Y + 13, NAMES[k], BRASS, BRASS_LT, 10)
        if s.fly_a > 0.01:
            a = (PROCS["ls"][0] + 30, PDESK - 20)
            b = (PIPE_X1 - 60 - 76 * int(s.fill), PIPE_Y + 13)
            x, y = bezier(a, (a[0] + 80, PIPE_Y - 40), b, s.fly_u)
            pill(p, x, y, s.fly_label, BRASS, BRASS_LT, 10, opacity=s.fly_a, shadow=None)
        if s.wc_count > 0.01 and s.wc_a > 0.5:
            p.text(PROCS["wc"][1] + 48, 196, "lines: %d" % int(round(s.wc_count)), 11, INK, 700,
                   "middle", mono=True)
        if s.eof > 0.01:
            pill(p, PIPE_X1 - 30, PIPE_Y - 22, "read = 0", TEAL, TEAL_LT, 10.5,
                 opacity=clamp(s.eof), shadow=None)
        if s.printed > 0.01:
            chip(p, PROCS["wc"][1] + 48, 218, "stdout: 3", TEAL, TEAL_LT, 11, opacity=clamp(s.printed))

        code_panel(p, 26, 322, W - 52, "ls_wc", PIPE_CODE, s.code, size=10.6, lead=16.0,
                   strike=int(s.strike) if s.strike >= 0 else None,
                   reveal=s.timeline.reached("code", t))
        caption(p, tl, t, 502)
        progress(p, tl, t, total, 588)

    return tl, draw, 622


def build_pipeline(only=None):
    tl, draw, height = pipeline()
    return render("ch24-pipe.gif", tl, draw, height, only=only)


# ------------------------------------------------- 25.2: levels and edges

EDGE_RUN = block_at("src/bin/epoll_edge.rs", 112, 116)
READ_ONCE = block_at("src/bin/epoll_edge.rs", 79, 82)
DRAIN = block_at("src/bin/epoll_edge.rs", 88, 95)
TANK = (330, 92, 70, 150)        # x, y, w, h of the receive buffer
READY = (520, 104, 190, 54)      # the ready list
LOOP_X, LOOP_DESK = 104, 222
TOTAL = 10_000


def edge():
    tl = Timeline(caption="", kind="step", mode="", handler="once", run_code=-1.0, h_code=-1.0,
                  buffer=0.0, listed=0.0, events=0.0, awake=0.0, ev_u=0.0, ev_a=0.0,
                  rd_u=0.0, rd_a=0.0, rd_label="", back_u=0.0, back_a=0.0, eagain=0.0,
                  checked=0.0, stuck=0.0, clock="", arrive=0.0)

    def arrive():
        tl.to(0.3, arrive=1.0)
        tl.to(1.0, in_out, buffer=float(TOTAL))
        tl.to(0.3, arrive=0.0)
        tl.to(0.5, back, listed=1.0)

    def event(n, k=1.0):
        tl.set(ev_u=0.0, run_code=1.0)
        tl.to(0.15, ev_a=1.0, listed=0.0)
        tl.to(0.7 * k, in_out, ev_u=1.0)
        tl.to(0.1, ev_a=0.0)
        tl.to(0.3 * k, back, awake=1.0, events=float(n), run_code=2.0)

    def read(amount, line, k=1.0):
        tl.set(rd_u=0.0, rd_label="read %d" % amount, h_code=float(line))
        tl.to(0.15, rd_a=1.0)
        tl.also(0.7 * k, in_out, buffer=max(0.0, tl._at("buffer", tl.now) - amount))
        tl.to(0.7 * k, in_out, rd_u=1.0)
        tl.to(0.1, rd_a=0.0)

    def put_back(k=1.0):
        tl.set(back_u=0.0)
        tl.to(0.15, back_a=1.0)
        tl.to(0.6 * k, in_out, back_u=1.0)
        tl.to(0.1, back_a=0.0, listed=1.0, awake=0.0, run_code=1.0, h_code=-1.0)

    def reset(mode, handler):
        tl.to(0.5, buffer=0.0, events=0.0, listed=0.0, awake=0.0, eagain=0.0, checked=0.0)
        tl.set(mode=mode, handler=handler, run_code=1.0, h_code=-1.0)

    tl.chapter("level-triggered")
    tl.set(mode="level-triggered, read once", handler="once", run_code=1.0)
    tl.say("The loop sleeps in epoll_wait. The socket is registered without EPOLLET: "
           "level-triggered.")
    tl.wait(0.6)
    tl.say("10,000 bytes arrive. epoll's callback puts the socket on the ready list.")
    arrive()
    tl.say("epoll_wait returns the socket, and the handler reads once: 4,096 bytes.")
    event(1)
    read(4096, 2)
    tl.say("Level-triggered: the kernel puts the socket back on the ready list. 5,904 bytes "
           "are still there.")
    put_back()
    tl.wait(0.6)
    tl.say("So the next epoll_wait reports it again. Two more events read the rest.")
    event(2, 0.6)
    read(4096, 2, 0.6)
    put_back(0.6)
    event(3, 0.6)
    read(1808, 2, 0.6)
    put_back(0.6)
    tl.say("The next epoll_wait checks the socket, finds it empty, and drops it from the list.")
    tl.to(0.4, checked=1.0)
    tl.to(0.5, listed=0.0)
    tl.to(0.3, checked=0.0)
    tl.say("Three events, and every byte read.", "insight")
    tl.wait(1.2)

    tl.chapter("edge, drained")
    tl.say("Now edge-triggered, with EPOLLET. The handler reads until EAGAIN.")
    reset("edge-triggered, read until EAGAIN", "drain")
    tl.wait(0.4)
    arrive()
    tl.say("One event. The handler's loop reads 4,096, then 4,096, then 1,808.")
    event(1)
    read(4096, 3)
    read(4096, 3, 0.7)
    read(1808, 3, 0.7)
    tl.say("The next read returns EAGAIN: the buffer is empty, and the handler returns.")
    tl.set(h_code=4.0)
    tl.to(0.4, back, eagain=1.0)
    tl.wait(0.8)
    tl.to(0.3, eagain=0.0, awake=0.0, run_code=1.0, h_code=-1.0)
    tl.say("Edge-triggered: the socket is not put back. Nothing is left to report.", "insight")
    tl.wait(1.2)

    tl.chapter("edge, read once")
    tl.say("Last, edge-triggered with the handler that reads once.", "fail")
    reset("edge-triggered, read once", "once")
    tl.wait(0.4)
    arrive()
    event(1)
    read(4096, 2)
    tl.say("The handler returns with 5,904 bytes still in the buffer. The socket is not put back.",
           "fail")
    tl.to(0.4, awake=0.0, run_code=1.0, h_code=-1.0)
    tl.to(0.4, stuck=1.0)
    for label in ("20 ms", "60 ms", "100 ms: no event"):
        tl.set(clock=label)
        tl.wait(0.8)
    tl.say("Only new bytes would make an edge. A peer waiting for a reply sends none: a stall.",
           "fail")
    tl.wait(1.6)

    def draw(p, s, total):
        t = s.t
        title_block(p, "Levels and edges",
                    "Level-triggered reports a socket while it has data. Edge-triggered reports "
                    "each arrival once.")
        scoreboard(p, [("events", int(round(s.events)), TEAL)], y=34)
        if s.mode:
            chip(p, READY[0], 200, s.mode, INK, STAGE, 11.5, anchor="start")

        robot(p, LOOP_X, LOOP_DESK, TEAL, s.awake, s.awake, "event loop", "one thread",
              look=0.9)
        zzz(p, LOOP_X + 44, LOOP_DESK - 108, t, 1 - s.awake)

        # the receive buffer, as a tank
        x, y, w, h = TANK
        p.text(x + w / 2, y - 8, "receive buffer", 11, MUTED, 600, "middle")
        p.rect(x, y, w, h, PAPER, INK, 8, 1.6)
        level = h * clamp(s.buffer / TOTAL)
        if level > 0.5:
            p.rect(x + 3, y + h - level, w - 6, level - 3, BRASS_LT if s.stuck < 0.5 else RUST_LT,
                   BRASS if s.stuck < 0.5 else RUST, 6, 1.2)
        p.text(x + w / 2, y + h + 20, "%d bytes" % int(round(s.buffer)), 12, INK, 700, "middle",
               mono=True)
        if s.arrive > 0.01:
            pill(p, x + w + 70, y + 20, "10,000 bytes", BRASS, BRASS_LT, 10.5,
                 opacity=s.arrive, shadow=None)
        if s.stuck > 0.01:
            focus(p, x, y, w, h, s.stuck, RUST)
            if s.clock:
                p.text(x + w / 2, y + h + 38, s.clock, 11.5, RUST, 700, "middle", mono=True)

        # the ready list
        rx, ry, rw, rh = READY
        p.text(rx, ry - 8, "ready list", 11, MUTED, 600)
        p.rect(rx, ry, rw, rh, STAGE, LINE, 8, 1.2)
        if s.listed > 0.01:
            chip(p, rx + 50, ry + rh / 2, "socket", TEAL, TEAL_LT, 11.5, opacity=clamp(s.listed))
        if s.checked > 0.01:
            p.text(rx + rw - 8, ry + rh / 2 + 4, "empty: drop", 10.5, MUTED, 700, "end",
                   opacity=clamp(s.checked))

        # in flight
        if s.ev_a > 0.01:
            a = (rx + 50, ry + rh / 2)
            b = (LOOP_X + 30, LOOP_DESK - 120)
            px, py = bezier(a, ((a[0] + b[0]) / 2, 70), b, s.ev_u)
            pill(p, px, py, "event", TEAL, PAPER, 10.5, opacity=s.ev_a)
        if s.rd_a > 0.01:
            a = (x + w / 2, y + h - 20)
            b = (LOOP_X + 40, LOOP_DESK - 40)
            px, py = bezier(a, ((a[0] + b[0]) / 2, y + h + 30), b, s.rd_u)
            pill(p, px, py, s.rd_label, BRASS, BRASS_LT, 10.5, opacity=s.rd_a, shadow=None)
        if s.back_a > 0.01:
            a = (LOOP_X + 30, LOOP_DESK - 120)
            b = (rx + 50, ry + rh / 2)
            px, py = bezier(a, ((a[0] + b[0]) / 2, ry + rh + 60), b, s.back_u)
            pill(p, px, py, "put back", TEAL, TEAL_LT, 10.5, opacity=s.back_a, shadow=None)
        if s.eagain > 0.01:
            pill(p, x + w / 2, y - 30, "EAGAIN", RUST, RUST_LT, 10.5, opacity=clamp(s.eagain),
                 shadow=None)

        code_panel(p, 26, 286, 250, "run", EDGE_RUN, s.run_code, size=9.0, lead=15.0,
                   reveal=s.timeline.reached("run_code", t))
        body = READ_ONCE if s.handler == "once" else DRAIN
        title = "read_once" if s.handler == "once" else "read_until_eagain"
        code_panel(p, 286, 286, W - 26 - 286, title, body, s.h_code, size=9.0, lead=15.0)
        caption(p, tl, t, 456)
        progress(p, tl, t, total, 542)

    return tl, draw, 576


def build_edge(only=None):
    tl, draw, height = edge()
    return render("ch25-edge.gif", tl, draw, height, only=only)


BUILDERS = {
    "mmap-faults": build_mmap_faults,
    "pipeline": build_pipeline,
    "edge": build_edge,
}

if __name__ == "__main__":
    import sys
    for name in sys.argv[1:] or BUILDERS:
        print(BUILDERS[name]())
