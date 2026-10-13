#!/usr/bin/env python3
"""The book's diagrams, written to src/figures/ as SVG.

    python3 tools/draw_figures.py                  # every figure
    python3 tools/draw_figures.py ring-steps       # some of them

Every figure is 480 units wide and runs from top to bottom, so that it fits
the width of a phone with its labels still readable. `figkit` refuses to write
a figure in which a label is wider than its box or a wire runs at an angle.
"""
import sys
from pathlib import Path

from figkit import CARD, EDGE, KINDS, card, cylinder, legend, save, sheet, tag, text, wire, zone

OUT = Path(__file__).resolve().parent.parent / "src" / "figures"
WIDTH = 480
FIGURES = {}


def figure(draw):
    """Registers `draw` under its name, with underscores written as hyphens."""
    FIGURES[draw.__name__.replace("_", "-")] = draw

    return draw


def lines(x, y, rows, cls="note", anchor="start", lead=17):
    """Plain lines of text, one under the other."""

    return "\n".join(text(x, y + lead * row, body, cls, anchor) for row, body in enumerate(rows))


def box(x, y, w, h, fill, stroke=EDGE, rx=6, width=1.3):
    """A plain rectangle, for the pictures figkit has no part for."""

    return (f'  <rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}"'
            f' stroke="{stroke}" stroke-width="{width}"/>')


def fields(x, y, w, kind, title, rows):
    """A kernel structure: its name and one line for each field shown."""
    accent, tint = KINDS[kind]
    h = 34 + 19 * len(rows) + 8
    parts = [box(x, y, w, h, CARD, EDGE, 10), box(x, y, w, 28, tint, accent, 10),
             text(x + 12, y + 19, title, "mono strong")]
    parts += [text(x + 12, y + 50 + 19 * k, row, "mono") for k, row in enumerate(rows)]

    return "\n".join(parts), h



def annotated(name, title, lede, rows, alt):
    """A piece of raw output explained line by line: each line in a box, with what it means under it."""
    parts, y = [], 96

    for raw, note, kind in rows:
        accent, tint = KINDS[kind]
        parts += [box(32, y, 416, 30, "#0f1c2b", "#0f1c2b", 6), text(44, y + 20, raw, "mono", fill="#d7e3ee"),
                  box(32, y + 34, 5, 20 * len(note) - 2, accent, accent, 2)]
        parts += [text(46, y + 48 + 20 * k, line_, "sub") for k, line_ in enumerate(note)]
        y += 34 + 20 * len(note) + 18

    save(OUT / (name + ".svg"), WIDTH, y, alt, title, lede, parts)


def meter(x, y, w, label_, value, limit, unit, kind):
    """A horizontal gauge: how much of a limit is used."""
    accent, tint = KINDS[kind]
    filled = max(6, w * min(value / limit, 1.0))

    return "\n".join([text(x, y - 8, label_, "name"), text(x + w, y - 8, "%s of %s %s" % (value, limit, unit), "mono", "end"),
                      box(x, y, w, 22, CARD, EDGE, 6), box(x, y, filled, 22, tint, accent, 6)])


# --------------------------------------------------------------- chapter 1

@figure
def pipe_two_ends():
    accent, tint = KINDS["model"]
    parts = [
        card(100, 96, 280, 64, "client", "Writer", ["calls write on the write end"], glyph="pencil"),
        wire([(240, 160), (240, 226)], label="write end"),
        zone(32, 226, 416, 132, "the kernel"),
        text(240, 262, "one pipe: a ring of 16 pages of 4096 bytes", "sub", "middle"),
    ]

    for slot in range(16):
        used = 3 <= slot <= 8
        parts.append(box(48 + 24 * slot, 276, 20, 28, tint if used else CARD, accent if used else EDGE, 4))

    parts += [
        text(130, 322, "oldest", "note", "middle"),
        text(250, 322, "newest", "note", "middle"),
        text(240, 344, "bytes leave in the order they entered", "sub", "middle"),
        wire([(240, 358), (240, 424)], label="read end"),
        card(100, 424, 280, 64, "service", "Reader", ["calls read on the read end"], glyph="eye"),
    ]
    save(OUT / "pipe-two-ends.svg", WIDTH, 520,
         "A writer process calls write on the write end of a pipe. Inside the kernel the pipe is a ring of 16 "
         "pages of 4096 bytes; 6 of them hold bytes, from the oldest to the newest. A reader process calls "
         "read on the read end, and bytes leave in the order they entered.",
         "A pipe and its ends", "The bytes wait in the kernel between the write and the read.", parts)


@figure
def ring_steps():
    # (the call, its result, head, tail, the (offset, length) of each slot)
    rows = [
        ("new", "all 4 slots free", 0, 0, [None, None, None, None]),
        ("put 12", "12 bytes copied", 2, 0, [(0, 8), (0, 4), None, None]),
        ("take 3", "3 bytes moved", 2, 0, [(3, 5), (0, 4), None, None]),
        ("put 30", "20 bytes copied", 4, 0, [(3, 5), (0, 8), (0, 8), (0, 8)]),
        ("take 5", "5 bytes moved", 4, 1, [None, (0, 8), (0, 8), (0, 8)]),
        ("put 30", "8 bytes copied", 5, 1, [(0, 8), (0, 8), (0, 8), (0, 8)]),
    ]
    oldest, newest, tint = KINDS["store"][0], KINDS["client"][0], "#D4E8AE"
    parts = [text(197, 96, "head", "tab", "middle"), text(197, 111, "tail", "tab", "middle")]
    parts += [text(261 + 54 * slot, 104, "slot %d" % slot, "tab", "middle") for slot in range(4)]

    for k, (call, result, head, tail, slots) in enumerate(rows):
        y = 128 + 62 * k
        parts += [text(32, y + 15, call, "mono strong"), text(32, y + 32, result, "note"),
                  text(197, y + 15, str(head), "mono strong", "middle"), text(197, y + 32, str(tail), "mono strong", "middle")]

        for slot, state in enumerate(slots):
            x = 236 + 54 * slot
            edge, width = EDGE, 1.3

            if head != tail and slot == (head - 1) % 4:
                edge, width = newest, 2.2

            if head != tail and slot == tail % 4:
                edge, width = oldest, 2.2

            parts.append(box(x, y, 50, 40, CARD, edge, 6, width))

            if state:
                offset, length = state
                parts += [box(x + 4 + 42 * offset / 8, y + 4, 42 * length / 8, 32, tint, "none", 3),
                          text(x + 25, y + 25, str(length), "mono strong", "middle")]

    parts.append(legend(32, 520, [("store", "oldest page"), ("client", "newest page")]))
    save(OUT / "ring-steps.svg", WIDTH, 544,
         "A ring of 4 slots, each a page of 8 bytes, after each call of the trace. Put 12 fills slot 0 and "
         "half of slot 1. Take 3 leaves 5 bytes in slot 0. Put 30 copies 20 bytes and fills slots 1, 2 and 3. "
         "Take 5 empties slot 0 and tail becomes 1. Put 30 copies 8 bytes into slot 0, and head becomes 5.",
         "A ring of 4 pages of 8 bytes", "The ring after each call. A slot shows its unread bytes.", parts)


@figure
def pipe_cases():
    reads = [("good", "The ring holds bytes", "returns them, up to the size asked for"),
             ("idle", "Empty, and a write end is open", "the caller sleeps until bytes arrive"),
             ("store", "Empty, and no write end is open", "returns 0: the end of the stream")]
    writes = [("good", "The ring has room", "copies the bytes and returns the count"),
              ("idle", "Full, and a read end is open", "the caller sleeps until a slot is free"),
              ("danger", "No read end is open", "signal SIGPIPE; the call fails with EPIPE")]
    parts = []

    for top, label, cases in ((104, "read", reads), (364, "write", writes)):
        parts.append(zone(32, top, 416, 228, label))
        parts += [card(48, top + 24 + 64 * k, 384, 54, kind, name, [sub]) for k, (kind, name, sub) in enumerate(cases)]

    save(OUT / "pipe-cases.svg", WIDTH, 616,
         "What a read does: when the ring holds bytes it returns them; when the ring is empty and a write end "
         "is open the caller sleeps; when the ring is empty and no write end is open it returns 0. What a write "
         "does: when the ring has room it copies the bytes; when the ring is full and a read end is open the "
         "caller sleeps; when no read end is open the kernel sends SIGPIPE and the call fails with EPIPE.",
         "What read and write do", "Each call looks at the ring, then at the other end.", parts)


@figure
def pipeline_ends():
    accent, tint = KINDS["store"]
    stages = [("client", "seq 1 100000", "writes 100000 lines"), ("client", "grep 7", "keeps lines with a 7"),
              ("client", "wc -l", "counts the lines"), ("service", "pipeline", "reads the count: 40951")]
    notes = [["588895 bytes pass", "through pipe 1"], ["241976 bytes pass", "through pipe 2"],
             ["6 bytes pass", "through pipe 3"]]
    parts = []

    for k, (kind, name, sub) in enumerate(stages):
        y = 96 + 174 * k
        parts.append(card(32, y, 250, 56, kind, name, [sub], glyph="terminal"))

        if k == len(notes):
            break

        parts += [
            wire([(157, y + 56), (157, y + 100)], label="stdout"),
            box(82, y + 100, 150, 30, tint, accent, 15),
            text(157, y + 119.5, "pipe %d" % (k + 1), "mono strong", "middle"),
            wire([(157, y + 130), (157, y + 174)], label="stdin" if k < 2 else "read end"),
            lines(300, y + 111, notes[k]),
        ]

    parts.append(lines(32, 702, ["pipeline creates each pipe and starts the command that writes",
                                 "to it. Then it closes its own copies of the ends it gave away."]))
    save(OUT / "pipeline-ends.svg", WIDTH, 744,
         "A pipeline of 3 commands and 3 pipes, top to bottom. The standard output of seq 1 100000 is the write end "
         "of pipe 1, and the standard input of grep 7 is its read end; 588895 bytes pass through. grep writes "
         "to pipe 2, which wc -l reads; 241976 bytes pass through. wc writes 6 bytes to pipe 3, which the "
         "pipeline program reads: 40951.",
         "A pipeline of commands", "Each command's output is the next command's input.", parts)



def chain(steps, x=80, w=320, y0=96, pitch=76, h=58):
    """Cards one under the other, joined by arrows. Returns the parts and the bottom edge."""
    parts = []

    for k, (kind, name, sub, glyph) in enumerate(steps):
        y = y0 + pitch * k
        parts.append(card(x, y, w, h, kind, name, [sub] if isinstance(sub, str) else sub, glyph=glyph))

        if k:
            parts.append(wire([(x + w / 2, y - (pitch - h)), (x + w / 2, y)]))

    return parts, y0 + pitch * len(steps)


@figure
def pipe_write_path():
    parts, bottom = chain([
        ("client", "write(4, \"hello\", 5)", "descriptor 4 is the write end", "terminal"),
        ("service", "struct file", "f_op is the pipe's function table", "doc"),
        ("store", "pipe_write: lock the pipe", "pipe->mutex", "lock"),
        ("store", "Is a reader left?", "readers == 0: SIGPIPE and EPIPE", "search"),
        ("store", "Find room in the ring", "the newest page, or a free slot", "stack"),
        ("good", "Copy the 5 bytes", "from the process into the page", "pencil"),
        ("good", "Wake the readers", "those asleep on rd_wait", "listen"),
    ])
    save(OUT / "pipe-write-path.svg", WIDTH, bottom,
         "The path of write(4, hello, 5) on a pipe. Descriptor 4 is the write end. Its struct file has the "
         "pipe's function table in f_op, which leads to pipe_write. pipe_write locks the pipe's mutex, checks "
         "that a reader is left and otherwise sends SIGPIPE and fails with EPIPE, finds room in the newest "
         "page or a free slot of the ring, copies the 5 bytes from the process into the page, and wakes the "
         "readers asleep on rd_wait.",
         "One write to a pipe, step by step", "The system call reaches the pipe through struct file.", parts)


@figure
def pipe_structs():
    parts, y = [], 96
    blocks = [
        ("service", "2 x struct file", ["read end:  f_mode read", "write end: f_mode write", "both: f_inode, the same inode"]),
        ("store", "struct pipe_inode_info", ["mutex      the lock", "rd_wait    sleeping readers", "wr_wait    sleeping writers",
                                             "head, tail the 2 counters", "ring_size  16 slots", "readers, writers  open ends",
                                             "bufs       the array of slots"]),
        ("model", "struct pipe_buffer, 16 of them", ["page    a page of memory", "offset  first unread byte",
                                                    "len     unread bytes", "flags   may be appended to"]),
    ]

    for k, (kind, title, rows) in enumerate(blocks):
        block, h = fields(60, y, 360, kind, title, rows)
        parts.append(block)

        if k:
            parts.append(wire([(240, y - 26), (240, y)]))

        y += h + 26

    save(OUT / "pipe-structs.svg", WIDTH, y - 2,
         "The kernel structures of a pipe. The read end and the write end are 2 struct file objects that "
         "refer to the same inode. The inode refers to a struct pipe_inode_info, which has the mutex, the wait "
         "queues rd_wait and wr_wait, the counters head and tail, ring_size, the counts readers and writers, "
         "and the array bufs. bufs holds 16 struct pipe_buffer, each with a page, an offset, a length and "
         "flags.",
         "The structures of a pipe", "A selection of fields from Linux 5.15.", parts)


@figure
def pipe_ends_count():
    rows = [("pipe()", "shell", "1", "1", "idle"),
            ("fork, fork", "shell, a, b", "3", "3", "idle"),
            ("unused ends closed", "a writes, b reads", "1", "1", "good"),
            ("a exits", "b reads", "1", "0", "store"),
            ("b reads the last byte", "b", "1", "0", "good")]
    notes = ["", "", "", "", "read returns 0"]
    parts = [text(32, 108, "after", "tab"), text(318, 108, "read ends", "tab", "middle"),
             text(404, 108, "write ends", "tab", "middle")]

    for k, (step, holders, readers, writers, kind) in enumerate(rows):
        y = 122 + 66 * k
        accent, tint = KINDS[kind]
        parts += [box(32, y, 416, 54, CARD, EDGE, 8), text(46, y + 23, step, "name"), text(46, y + 42, holders, "sub"),
                  box(296, y + 13, 44, 28, tint, accent, 8), text(318, y + 32, readers, "mono strong", "middle"),
                  box(382, y + 13, 44, 28, tint, accent, 8), text(404, y + 32, writers, "mono strong", "middle")]

    parts.append(lines(32, 470, ["The counts are descriptors open on each end, in all processes. A reader",
                                 "sees the end of the stream only when the write count is 0. If the shell",
                                 "kept its write end, the count would stay at 1 and b would wait for ever."]))
    save(OUT / "pipe-ends-count.svg", WIDTH, 522,
         "The number of open read ends and write ends of the pipe in the pipeline a | b. After pipe the shell "
         "holds 1 of each. After 2 forks the shell, a and b hold 3 of each. After each process closes what it "
         "does not use, a holds the write end and b the read end: 1 and 1. After a exits the write count is 0. "
         "When b has read the last byte, read returns 0.",
         "Who holds the ends of a pipe", "The pipeline a | b, from pipe() to the end of the stream.", parts)


# --------------------------------------------------------------- chapter 2

def numbered(x, y, w, number, note, kind="client"):
    """One entry of a descriptor table: its number and what made it."""
    accent, tint = KINDS[kind]

    return "\n".join([box(x, y, w, 50, tint, accent, 8),
                      text(x + w / 2, y + 22, number, "mono strong", "middle"),
                      text(x + w / 2, y + 39, note, "note", "middle")])


@figure
def fd_tables():
    parts = [
        zone(32, 104, 416, 92, "descriptor table of the process"),
        numbered(48, 128, 104, "0 1 2", "terminal", "idle"),
        numbered(168, 128, 64, "3", "open"),
        numbered(248, 128, 64, "4", "dup of 3"),
        numbered(336, 128, 96, "5", "second open"),

        zone(32, 236, 416, 104, "descriptions"),
        card(160, 260, 160, 60, "service", "offset 5", ["O_WRONLY"]),
        card(328, 260, 104, 60, "service", "offset 0", ["O_WRONLY"]),
        wire([(200, 178), (200, 260)]),
        wire([(280, 178), (280, 260)]),
        wire([(384, 178), (384, 260)]),

        zone(32, 380, 416, 104, "inodes"),
        cylinder(180, 400, 260, 68, "store", "file", ["5 bytes: hello"]),
        wire([(240, 320), (240, 404)]),
        wire([(380, 320), (380, 404)]),
        lines(48, 276, ["offset and", "status flags", "live here"]),
        lines(48, 420, ["the data", "lives here"]),
    ]
    save(OUT / "fd-tables.svg", WIDTH, 508,
         "The descriptor table of a process has entries 0, 1 and 2 for the terminal, entry 3 from an open, "
         "entry 4 from a dup of 3, and entry 5 from a second open of the same file. Entries 3 and 4 refer to one "
         "open file description with offset 5. Entry 5 refers to another description with offset 0. Both "
         "descriptions refer to the same inode, a file of 5 bytes.",
         "From a descriptor to the file", "Descriptor, then description, then inode.", parts)


@figure
def redirect_shared():
    parts = [
        zone(32, 104, 416, 160, "> file 2>&1"),
        numbered(48, 128, 56, "1", "stdout"),
        numbered(48, 194, 56, "2", "stderr"),
        card(150, 128, 150, 116, "service", "1 description", ["offset 0, 4, 8"]),
        wire([(104, 153), (150, 153)]),
        wire([(104, 219), (150, 219)]),
        box(346, 148, 86, 76, CARD, KINDS["good"][0], 8, 1.6),
        lines(360, 180, ["out", "err"], "mono strong"),
        wire([(300, 186), (346, 186)]),

        zone(32, 304, 416, 160, "> file 2> file"),
        numbered(48, 328, 56, "1", "stdout"),
        numbered(48, 394, 56, "2", "stderr"),
        card(150, 328, 150, 50, "service", "offset 0, 4", []),
        card(150, 394, 150, 50, "service", "offset 0, 4", []),
        wire([(104, 353), (150, 353)]),
        wire([(104, 419), (150, 419)]),
        box(346, 346, 86, 80, CARD, KINDS["danger"][0], 8, 1.6),
        lines(360, 390, ["err"], "mono strong"),
        wire([(300, 362), (346, 362)]),
        wire([(300, 410), (346, 410)]),
        lines(32, 492, ["With separate descriptions, the second write starts at offset 0",
                        "and overwrites the first."]),
    ]
    save(OUT / "redirect-shared.svg", WIDTH, 528,
         "With > file 2>&1, descriptors 1 and 2 refer to one open file description. The write of out moves its "
         "offset from 0 to 4, the write of err continues at 4, and the file holds out and err. With > file 2> "
         "file, each descriptor has its own description with offset 0. The write of err starts at offset 0 "
         "and overwrites out, and the file holds err.",
         "The same file on descriptors 1 and 2", "The result depends on whether the offset is shared.", parts)



@figure
def read_path():
    steps = [("client", "read(3, buf, 100)", "the process enters the kernel", "terminal"),
             ("service", "Descriptor table", "entry 3 gives a struct file", "stack"),
             ("service", "struct file", "supplies the offset, f_pos", "doc"),
             ("store", "The file system's read", "found through f_op", "gear"),
             ("store", "struct inode", "gives the size and the page cache", "doc"),
             ("good", "Copy to buf", "then f_pos += bytes copied", "pencil")]
    parts = []

    for k, (kind, name, sub, glyph) in enumerate(steps):
        y = 96 + 76 * k
        parts.append(card(80, y, 320, 58, kind, name, [sub], glyph=glyph))

        if k:
            parts.append(wire([(240, y - 18), (240, y)]))

    save(OUT / "read-path.svg", WIDTH, 96 + 76 * len(steps),
         "The path of read(3, buf, 100) through the kernel. The process enters the kernel. Entry 3 of the "
         "descriptor table gives a struct file. The struct file supplies the offset, f_pos. The read function "
         "of the file system is found through f_op. The struct inode gives the size of the file and its page "
         "cache. The bytes are copied to buf, and f_pos is increased by the number of bytes copied.",
         "One read, step by step", "Each step uses one of the structures of this chapter.", parts)


@figure
def file_structs():
    parts, y = [], 96
    blocks = [
        ("service", "struct fdtable", ["fd[]           one pointer per descriptor", "open_fds       bitmap: numbers in use",
                                       "close_on_exec  bitmap: FD_CLOEXEC"]),
        ("service", "struct file", ["f_pos     the offset", "f_flags   O_APPEND, O_NONBLOCK, ...",
                                    "f_count   references to this file", "f_inode, f_path"]),
        ("outside", "struct dentry", ["d_name    one component of a path", "d_parent  the directory", "d_inode"]),
        ("store", "struct inode", ["i_ino     the inode number", "i_mode    type and permissions",
                                   "i_nlink   names that refer to it", "i_size, i_uid, i_gid, times",
                                   "i_mapping the cached pages"]),
    ]

    for k, (kind, title, rows) in enumerate(blocks):
        block, h = fields(60, y, 360, kind, title, rows)
        parts.append(block)

        if k:
            parts.append(wire([(240, y - 26), (240, y)]))

        y += h + 26

    save(OUT / "file-structs.svg", WIDTH, y - 2,
         "The kernel structures behind a descriptor, top to bottom, each pointing to the next. struct fdtable "
         "has the array fd with one pointer per descriptor and the bitmaps open_fds and close_on_exec. struct "
         "file has f_pos, f_flags, f_count, f_inode and f_path. struct dentry has d_name, d_parent and d_inode. "
         "struct inode has i_ino, i_mode, i_nlink, i_size, the owner and times, and i_mapping.",
         "The structures behind a descriptor", "A selection of fields from Linux 5.15.", parts)


@figure
def names_inodes():
    accent, tint = KINDS["store"]
    parts = [
        zone(32, 104, 416, 118, "directory /tmp/x"),
        card(48, 130, 184, 72, "outside", "report.txt", ["inode 19927765"]),
        card(248, 130, 184, 72, "outside", "copy.txt", ["inode 19927765"]),
        wire([(140, 202), (140, 262), (188, 262), (188, 284)]),
        wire([(340, 202), (340, 262), (292, 262), (292, 284)]),
        card(90, 284, 300, 96, "store", "inode 19927765", ["i_nlink 2, i_size 6", "owner, permissions, times",
                                                           "the location of the data"]),
        wire([(240, 380), (240, 412)]),
        box(165, 412, 150, 36, tint, accent, 8),
        text(240, 435, "hello\\n", "mono strong", "middle"),
        lines(32, 478, ["A directory holds names and inode numbers and nothing else. The",
                        "permissions, the size and the data belong to the inode, so both",
                        "names show the same file."]),
    ]
    save(OUT / "names-inodes.svg", WIDTH, 530,
         "The directory /tmp/x has the entries report.txt and copy.txt, and both hold the inode number "
         "19927765. That inode has a link count of 2 and a size of 6, the owner, the permissions and the "
         "times, and the location of the data, which is the text hello followed by a newline.",
         "Names and inodes", "A name is an entry in a directory. The file is the inode.", parts)


@figure
def unlink_open():
    rows = [("create", "1", "0", "exists", "good"), ("open", "1", "1", "exists", "good"),
            ("unlink", "0", "1", "exists, has no name", "store"), ("close", "0", "0", "freed", "danger")]
    parts = [text(32, 108, "call", "tab"), text(150, 108, "names", "tab", "middle"),
             text(230, 108, "open", "tab", "middle"), text(290, 108, "the inode", "tab")]

    for k, (call, names, opens, state, kind) in enumerate(rows):
        y = 122 + 60 * k
        accent, tint = KINDS[kind]
        parts += [box(32, y, 416, 46, CARD, EDGE, 8), text(48, y + 28, call, "mono strong"),
                  text(150, y + 28, names, "mono strong", "middle"), text(230, y + 28, opens, "mono strong", "middle"),
                  box(282, y + 9, 154, 28, tint, accent, 14), text(359, y + 28, state, "pill", "middle", accent)]

    parts.append(lines(32, 388, ["names is i_nlink, the number of directory entries. open is the number",
                                 "of open file descriptions. The kernel frees the inode and its data",
                                 "when both are 0."]))
    save(OUT / "unlink-open.svg", WIDTH, 440,
         "The counts of an inode through 4 calls. After create it has 1 name and is open 0 times, and it "
         "exists. After open it has 1 name and is open once. After unlink it has 0 names and is still open "
         "once, so it exists without a name. After close both counts are 0 and the inode is freed.",
         "A file removed while it is open", "The inode lives until both counts are 0.", parts)


@figure
def fork_shared():
    parts = [
        zone(32, 104, 196, 150, "parent"),
        numbered(48, 128, 76, "1", "stdout"), numbered(136, 128, 76, "3", "log"),
        zone(252, 104, 196, 150, "child, after fork"),
        numbered(268, 128, 76, "1", "stdout"), numbered(356, 128, 76, "3", "log"),
        text(130, 208, "table copied", "note", "middle"), text(350, 208, "by fork", "note", "middle"),
        card(48, 300, 180, 64, "service", "terminal", ["f_count 2"]),
        card(252, 300, 180, 64, "service", "log file", ["f_pos 120, f_count 2"]),
        wire([(86, 178), (86, 300)]),
        wire([(306, 178), (306, 268), (120, 268), (120, 300)]),
        wire([(174, 178), (174, 244), (290, 244), (290, 300)]),
        wire([(394, 178), (394, 300)]),
        lines(32, 398, ["fork copies the table. The entries of the child point to the same",
                        "struct file objects as the entries of the parent, so both processes",
                        "append to the log at the same offset."]),
    ]
    save(OUT / "fork-shared.svg", WIDTH, 450,
         "A parent has descriptor 1 on the terminal and descriptor 3 on a log file. After fork the child has "
         "the same entries, and they point to the same open file descriptions: the terminal, with a reference "
         "count of 2, and the log file, with offset 120 and a reference count of 2.",
         "Descriptors after fork", "The table is copied. The open files are shared.", parts)


# --------------------------------------------------------------- chapter 3

@figure
def process_life():
    parts = [
        card(70, 96, 340, 64, "client", "fork", ["the parent gets a child with a new pid"], glyph="swap"),
        wire([(240, 160), (240, 204)]),
        card(70, 204, 340, 82, "good", "Running", ["exec replaces the program;", "pid, parent and descriptors stay"], glyph="gear"),
        wire([(240, 286), (240, 342)], label="exit, or a signal"),
        card(70, 342, 340, 82, "store", "Zombie", ["memory and descriptors are released;", "the entry keeps the exit status"], glyph="clock"),
        wire([(240, 424), (240, 480)], label="wait by the parent"),
        card(70, 480, 340, 64, "idle", "Entry removed", ["the pid can be given out again"], dashed=True),
    ]
    save(OUT / "process-life.svg", WIDTH, 572,
         "The life of a process, top to bottom. Fork gives the parent a child with a new pid. The child runs; "
         "exec replaces its program and keeps the pid, the parent and the descriptors. After exit or a signal "
         "the process is a zombie: its memory and descriptors are released and its table entry keeps the exit "
         "status. When the parent calls wait, the entry is removed and the pid can be given out again.",
         "The life of a process", "A table entry is created by fork and removed by wait.", parts)


def proc(x, y, pid, note, kind="client", dashed=False):
    return card(x, y, 86, 52, kind, pid, [note], dashed=dashed)


@figure
def orphan_adoption():
    parts = [
        zone(32, 104, 416, 96, "before pid 3 exits"),
        proc(44, 128, "1", "init", "idle"), proc(146, 128, "2", "of 1"), proc(248, 128, "3", "of 2"),
        proc(350, 128, "4", "of 3"),
        wire([(130, 154), (146, 154)]), wire([(232, 154), (248, 154)]), wire([(334, 154), (350, 154)]),

        zone(32, 240, 416, 176, "after pid 3 exits"),
        proc(44, 264, "1", "init", "idle"), proc(146, 264, "2", "of 1"), proc(248, 264, "3", "zombie", "store"),
        wire([(130, 290), (146, 290)]), wire([(232, 290), (248, 290)]),
        proc(44, 348, "4", "of 1"),
        wire([(87, 316), (87, 348)]),
        lines(160, 364, ["The kernel makes init the parent of 4.", "Pid 3 stays until its parent, 2, waits."]),
    ]
    save(OUT / "orphan-adoption.svg", WIDTH, 440,
         "Before pid 3 exits, the processes form a chain: 1 is the parent of 2, 2 of 3, and 3 of 4. After pid 3 "
         "exits it is a zombie child of 2, and the kernel has made pid 1, init, the parent of 4.",
         "An orphan gets a new parent", "Every process has a parent that can wait for it.", parts)



@figure
def fork_exec_wait():
    left = [("client", "shell", "reads the line: ls"), ("client", "fork()", "returns the child's pid"),
            ("idle", "wait()", "sleeps until it ends"), ("idle", "", ""), ("idle", "", ""),
            ("client", "wait() returns", "child's pid and status"), ("client", "shell", "prints the next prompt")]
    right = [None, ("outside", "fork() returns 0", "a copy of the shell"), ("outside", "exec(\"ls\")", "the program is replaced"),
             ("good", "ls runs", "writes to descriptor 1"), ("store", "exit(0)", "becomes a zombie"), None, None]
    parts = [text(128, 104, "parent, pid 500", "tab", "middle"), text(352, 104, "child, pid 501", "tab", "middle")]

    for k in range(7):
        y = 118 + 66 * k

        if left[k][1]:
            parts.append(card(32, y, 192, 54, left[k][0], left[k][1], [left[k][2]]))
        else:
            parts.append(box(120, y, 16, 54, KINDS["idle"][1], KINDS["idle"][0], 8))

        if right[k]:
            parts.append(card(256, y, 192, 54, right[k][0], right[k][1], [right[k][2]]))

    parts += [wire([(224, 211), (256, 211)], kind="flow"),
              wire([(256, 409), (240, 409), (240, 475), (224, 475)], kind="idle"),
              text(240, 596, "time runs downward", "note", "middle")]
    save(OUT / "fork-exec-wait.svg", WIDTH, 612,
         "A shell runs ls, in 2 columns with time running downward. The parent, pid 500, reads the line and "
         "calls fork, which returns the child's pid. The child, pid 501, is a copy of the shell in which fork "
         "returns 0. The parent calls wait and sleeps. The child calls exec and its program is replaced by ls, "
         "which runs and writes to descriptor 1, then calls exit and becomes a zombie. wait returns in the "
         "parent with the pid and status of the child, and the shell prints the next prompt.",
         "A shell runs a command", "fork in the parent, exec in the child, wait in the parent.", parts)


@figure
def task_struct_map():
    block, h = fields(110, 96, 260, "store", "struct task_struct", [
        "pid, tgid       its numbers", "__state         R, S, D, T", "exit_state      zombie",
        "exit_code       for the parent", "real_parent     who created it", "children        list of children",
        "comm            name, 15 chars"])
    parts = [block]
    y = 96 + h + 40
    targets = [("mm", "address space", "", "chapter 7"),
               ("files", "descriptor table", "", "chapter 2"),
               ("signal, sighand", "signal state", "", "chapter 5"),
               ("se", "scheduling state", "", "chapter 6"),
               ("nsproxy", "namespaces", "", "chapter 11"),
               ("cgroups", "control groups", "", "chapter 12")]

    for k, (field, name, what, where) in enumerate(targets):
        x, yy = 32 + 212 * (k % 2), y + 76 * (k // 2)
        parts.append(card(x, yy, 204, 64, "service" if k % 2 == 0 else "client", field, [name, where]))

    parts.append(wire([(240, 96 + h), (240, y)]))
    save(OUT / "task-struct-map.svg", WIDTH, y + 76 * 3 + 4,
         "struct task_struct has the fields pid and tgid, __state, exit_state, exit_code, real_parent, children "
         "and comm, and pointers to other structures: mm to struct mm_struct, the address space of chapter 7; "
         "files to struct files_struct, the descriptor table of chapter 2; signal and sighand to the signal "
         "state of chapter 5; se, the struct sched_entity of chapter 6; nsproxy to the namespaces of chapter "
         "11; and cgroups to the control groups of chapter 12.",
         "The kernel's record of a process", "struct task_struct and what it points to.", parts)


@figure
def wait_status():
    accent, tint = KINDS["good"]
    red, redtint = KINDS["danger"]
    parts = [text(32, 104, "ended by exit(7)", "tab")]

    def bits(y, cells):
        out, x = [], 32

        for width, label, value, colour, fill in cells:
            ink = "#5D6B7A" if colour == EDGE else colour
            out += [box(x, y, width, 44, fill, colour, 6), text(x + width / 2, y + 19, label, "pill", "middle", ink),
                    text(x + width / 2, y + 36, value, "mono strong", "middle")]
            x += width + 6

        return out

    parts += bits(116, [(200, "bits 15 to 8: exit status", "7", accent, tint), (36, "bit 7", "0", EDGE, CARD),
                        (168, "bits 6 to 0: signal", "0", EDGE, CARD)])
    parts.append(text(32, 204, "ended by SIGTERM", "tab"))
    parts += bits(216, [(200, "bits 15 to 8", "0", EDGE, CARD), (36, "core", "0", EDGE, CARD),
                        (168, "bits 6 to 0: signal", "15", red, redtint)])
    parts.append(lines(32, 296, ["wait returns 1 integer. A signal number other than 0 means the process",
                                 "was ended by that signal. Otherwise bits 15 to 8 hold the 8 bits that",
                                 "the process passed to exit, which is why exit(300) is reported as 44."]))
    save(OUT / "wait-status.svg", WIDTH, 350,
         "The integer that wait returns. For a process ended by exit(7), bits 15 to 8 hold the exit status 7 "
         "and bits 6 to 0, the signal number, are 0. For a process ended by SIGTERM, bits 15 to 8 are 0 and "
         "bits 6 to 0 hold the signal number 15. Bit 7 records whether a core dump was written.",
         "The status that wait returns", "An exit status or a signal number, in 1 integer.", parts)


# --------------------------------------------------------------- chapter 4

@figure
def shell_loop():
    parts = [
        card(90, 96, 300, 56, "client", "Read a line", ["from the terminal or a script"], glyph="terminal"),
        wire([(240, 152), (240, 184)]),
        card(90, 184, 300, 56, "service", "Parse", ["words, | and redirections"], glyph="doc"),
        wire([(240, 240), (240, 272)]),
        card(90, 272, 300, 56, "store", "cd or exit?", ["run it inside the shell process"], glyph="gear"),
        wire([(240, 328), (240, 376)], label="otherwise"),
        card(90, 376, 300, 74, "model", "Start each command", ["a child process per command,", "descriptors 0 and 1 arranged"], glyph="swap"),
        wire([(240, 450), (240, 482)]),
        card(90, 482, 300, 56, "good", "Wait for all of them", ["keep the status of the last"], glyph="clock"),
        wire([(390, 510), (432, 510), (432, 124), (390, 124)], kind="idle"),
        text(48, 300, "builtin", "note"),
    ]
    save(OUT / "shell-loop.svg", WIDTH, 566,
         "The loop of a shell, top to bottom: read a line; parse it into words, pipes and redirections; if the "
         "command is cd or exit, run it inside the shell process; otherwise start a child process for each "
         "command with its descriptors 0 and 1 arranged; wait for all of them and keep the status of the last; "
         "then read the next line.",
         "The loop of a shell", "Read, parse, start, wait.", parts)


@figure
def shell_plan():
    accent, tint = KINDS["store"]
    parts = [
        text(240, 100, "sort -rn < numbers | head -n 2 >> numbers", "mono strong", "middle"),
        cylinder(150, 124, 180, 62, "store", "numbers", ["opened for reading"]),
        wire([(240, 186), (240, 236)], label="descriptor 0"),
        card(110, 236, 260, 56, "client", "sort -rn", ["child 1"], glyph="terminal"),
        wire([(240, 292), (240, 342)], label="descriptor 1"),
        box(165, 342, 150, 30, tint, accent, 15),
        text(240, 361.5, "pipe", "mono strong", "middle"),
        wire([(240, 372), (240, 422)], label="descriptor 0"),
        card(110, 422, 260, 56, "client", "head -n 2", ["child 2"], glyph="terminal"),
        wire([(240, 478), (240, 528)], label="descriptor 1"),
        cylinder(150, 528, 180, 62, "store", "numbers", ["opened with O_APPEND"]),
    ]
    save(OUT / "shell-plan.svg", WIDTH, 614,
         "The plan for the line sort -rn < numbers | head -n 2 >> numbers. Descriptor 0 of sort is the file "
         "numbers, opened for reading. Descriptor 1 of sort is the write end of a pipe. Descriptor 0 of head is "
         "the read end of that pipe. Descriptor 1 of head is the file numbers, opened with O_APPEND.",
         "Descriptors for one command line", "The shell arranges descriptors 0 and 1 of each child.", parts)



def chip(x, y, w, body, kind, h=30):
    accent, tint = KINDS[kind]

    return "\n".join([box(x, y, w, h, tint, accent, 8), text(x + w / 2, y + h / 2 + 4, body, "pill", "middle", accent)])


@figure
def shell_parse():
    words = [("sort", "client"), ("-rn", "client"), ("<", "store"), ("numbers", "client"), ("|", "danger"),
             ("head", "client"), ("-n", "client"), ("2", "client"), (">>", "store"), ("numbers", "client")]
    parts = [text(240, 104, "sort -rn < numbers | head -n 2 >> numbers", "mono strong", "middle"),
             wire([(240, 114), (240, 144)], label="split at spaces")]
    x, y = 32, 144

    for k, (word, kind) in enumerate(words):
        if k == 5:
            x, y = 32, 184

        width = 30 + 9 * len(word)
        parts.append(chip(x, y, width, word, kind))
        x += width + 6

    block_a, h = fields(32, 274, 200, "client", "command 1", ["args    sort -rn", "input   numbers", "output  (none)", "append  false"])
    block_b, _ = fields(248, 274, 200, "client", "command 2", ["args    head -n 2", "input   (none)", "output  numbers", "append  true"])
    parts += [wire([(240, 224), (240, 252), (132, 252), (132, 274)]), wire([(240, 224), (240, 252), (348, 252), (348, 274)]),
              block_a, block_b,
              lines(32, 274 + h + 30, ["A | starts a new command. A redirection operator takes the next word",
                                      "as a file name. Every other word is an argument."])]
    save(OUT / "shell-parse.svg", WIDTH, 274 + h + 68,
         "The line sort -rn < numbers | head -n 2 >> numbers is split at spaces into 10 words. The words form 2 "
         "commands. Command 1 has the arguments sort -rn, the input file numbers, and no output file. Command 2 "
         "has the arguments head -n 2, no input file, the output file numbers, and append set.",
         "From a line to a pipeline", "The parser turns words into a list of commands.", parts)


@figure
def shell_syscalls():
    cols = [("shell, pid 570272", 32), ("seq, pid 570273", 172), ("wc, pid 570274", 312)]
    rows = [[("pipe2: 3 and 4", "store"), None, None],
            [("clone", "client"), ("starts as a copy", "idle"), None],
            [("close(4)", "idle"), ("dup3(4, 1)", "store"), None],
            [("clone", "client"), ("execve seq", "good"), ("starts as a copy", "idle")],
            [("close(3)", "idle"), None, ("dup3(3, 0)", "store")],
            [("wait4 ...", "idle"), None, ("openat count.txt", "store")],
            [None, None, ("dup3(3, 1)", "store")],
            [None, ("exit 0", "danger"), ("execve wc", "good")],
            [("wait4: 570273", "client"), None, ("exit 0", "danger")],
            [("wait4: 570274", "client"), None, None]]
    parts = [text(x + 68, 104, label, "tab", "middle") for label, x in cols]

    for k, row in enumerate(rows):
        for (label, x), cell in zip(cols, row):
            if cell:
                parts.append(chip(x, 118 + 38 * k, 136, cell[0], cell[1]))

    parts.append(lines(32, 118 + 38 * len(rows) + 22, ["Descriptor 3 is the read end of the pipe and 4 is the write end.",
                                                       "Each child rearranges its own descriptors before execve."]))
    save(OUT / "shell-syscalls.svg", WIDTH, 118 + 38 * len(rows) + 60,
         "The system calls of sh for the line seq 1 3 | wc -l > count.txt, in 3 columns. The shell calls pipe2 "
         "and gets descriptors 3 and 4, then clone. The first child calls dup3(4, 1) and execve seq, while the "
         "shell closes 4 and calls clone again. The second child calls dup3(3, 0), opens count.txt, calls "
         "dup3(3, 1) and execve wc, while the shell closes 3 and calls wait4. Both children exit with 0, and "
         "wait4 returns their pids.",
         "The system calls of a pipeline", "seq 1 3 | wc -l > count.txt, as traced on this machine.", parts)


# --------------------------------------------------------------- chapter 5

def bits(x, y, label, on, kind):
    """A row of 16 mask bits for signals 1 to 16, with the set ones filled."""
    accent, tint = KINDS[kind]
    parts = [text(x, y + 15, label, "note")]

    for n in range(1, 17):
        left = x + 70 + 20 * (n - 1)
        parts.append(box(left, y, 16, 22, tint if n in on else CARD, accent if n in on else EDGE, 3))

        if n in on:
            parts.append(text(left + 8, y + 15, str(n), "pill", "middle", accent))

    return "\n".join(parts)


@figure
def signal_path():
    parts = [
        card(90, 96, 300, 56, "client", "Sender", ["kill(pid, SIGUSR1)"], glyph="terminal"),
        wire([(240, 152), (240, 204)], label="sets a bit"),
        zone(32, 204, 416, 110, "state of the target"),
        bits(48, 228, "pending", {10}, "store"),
        bits(48, 262, "blocked", {2}, "idle"),
        text(240, 304, "delivered: pending and not blocked", "sub", "middle"),
        wire([(240, 314), (240, 378)], label="on return to user mode"),
        card(32, 414, 128, 64, "danger", "Default", ["end process"]),
        card(176, 414, 128, 64, "idle", "Ignore", ["discard"]),
        card(320, 414, 128, 64, "good", "Handler", ["run a function"]),
        wire([(240, 378), (96, 378), (96, 414)]),
        wire([(240, 378), (240, 414)]),
        wire([(240, 378), (384, 378), (384, 414)]),
    ]
    save(OUT / "signal-path.svg", WIDTH, 506,
         "A sender calls kill with a pid and SIGUSR1. The kernel sets bit 10 in the pending mask of the target. "
         "The target also has a blocked mask, here with bit 2 set. When the target is about to return to user "
         "mode, each signal that is pending and not blocked is delivered, and its action is performed: the "
         "default, which ends the process for most signals; ignore, which discards it; or a handler function.",
         "From kill to an action", "Sending sets a bit. Delivery happens later, in the target.", parts)


@figure
def signal_eintr():
    parts = [
        card(90, 96, 300, 56, "client", "read(fd, ...)", ["no data: the process sleeps"], glyph="clock"),
        wire([(240, 152), (240, 204)], label="a signal arrives"),
        card(90, 204, 300, 56, "store", "The process is woken", ["the read is abandoned"], glyph="gear"),
        wire([(240, 260), (240, 292)]),
        card(90, 292, 300, 56, "good", "The handler runs", ["in user mode"], glyph="doc"),
        wire([(240, 348), (240, 380)]),
        wire([(240, 380), (130, 380), (130, 412)]),
        wire([(240, 380), (350, 380), (350, 412)]),
        card(32, 412, 196, 74, "danger", "Without SA_RESTART", ["read returns -1,", "errno is EINTR"]),
        card(252, 412, 196, 74, "good", "With SA_RESTART", ["the kernel calls", "read again"]),
    ]
    save(OUT / "signal-eintr.svg", WIDTH, 514,
         "A process calls read and sleeps because there is no data. A signal arrives, and the kernel wakes the "
         "process and abandons the read. The handler runs in user mode. Then, for a handler installed without "
         "SA_RESTART, read returns -1 with the error EINTR. For a handler installed with SA_RESTART, the kernel "
         "calls read again.",
         "A signal during a blocking call", "The handler runs first. Then the call fails or restarts.", parts)



@figure
def signal_ctrl_c():
    parts, bottom = chain([
        ("client", "Ctrl-C is pressed", "the terminal receives the byte 0x03", "terminal"),
        ("store", "Terminal driver", "recognises the interrupt character", "gear"),
        ("store", "SIGINT is sent", "to every foreground process", "swap"),
        ("store", "A pending bit is set", "in the mask of each process", "stack"),
        ("service", "The process is woken", "if it sleeps in a system call", "clock"),
        ("good", "On return to user mode", "the kernel performs the action", "doc"),
    ])
    save(OUT / "signal-ctrl-c.svg", WIDTH, bottom,
         "What happens when Ctrl-C is pressed. The terminal receives the byte 0x03. The terminal driver in the "
         "kernel recognises the interrupt character and sends SIGINT to each process of the foreground process "
         "group. The pending bit of SIGINT is set in the mask of each process. A process that sleeps in a system call is "
         "woken. When the process returns to user mode, the kernel performs the action of the signal.",
         "From Ctrl-C to an action", "The kernel sends the signal. The process receives it later.", parts)


@figure
def signal_structs():
    parts, y = [], 96
    blocks = [
        ("client", "struct task_struct (1 per thread)", ["blocked   mask: delivery postponed", "pending   signals sent to this thread"]),
        ("store", "struct signal_struct (1 per process)", ["shared_pending  signals sent to the process"]),
        ("service", "struct sighand_struct", ["action[64]  1 struct k_sigaction per signal:", "  sa_handler  default, ignore, or a function",
                                             "  sa_flags    SA_RESTART, ...", "  sa_mask     blocked while the handler runs"]),
    ]

    for k, (kind, title, rows) in enumerate(blocks):
        block, h = fields(40, y, 400, kind, title, rows)
        parts.append(block)

        if k:
            parts.append(wire([(240, y - 26), (240, y)]))

        y += h + 26

    parts.append(lines(32, y + 6, ["kill sends to a process and sets a bit in shared_pending. Any thread",
                                  "that does not block the signal may take it."]))
    save(OUT / "signal-structs.svg", WIDTH, y + 44,
         "The kernel structures of signal handling. Each thread has a struct task_struct with a blocked mask "
         "and a pending set for signals sent to that thread. Each process has a struct signal_struct with "
         "shared_pending for signals sent to the process. A struct sighand_struct holds the array action with "
         "a struct k_sigaction for each of the 64 signals: sa_handler, sa_flags and sa_mask.",
         "Where signal state is kept", "A selection of fields from Linux 5.15.", parts)


@figure
def signal_frame():
    parts, bottom = chain([
        ("client", "The program is interrupted", "at any instruction", "terminal"),
        ("store", "The registers are saved", "by the kernel, on the user stack", "stack"),
        ("store", "The program counter is set", "to the address of the handler", "gear"),
        ("good", "The handler runs", "in user mode, on the same stack", "doc"),
        ("store", "The handler returns", "into a call of sigreturn", "swap"),
        ("client", "The registers are restored", "the program continues", "terminal"),
    ])
    save(OUT / "signal-frame.svg", WIDTH, bottom,
         "How a handler is run. The program is interrupted at any instruction. The kernel saves the registers "
         "in a frame on the user stack and sets the program counter to the address of the handler. The handler "
         "runs in user mode on the same stack. When it returns, it returns into a call of sigreturn, and the "
         "kernel restores the registers so that the program continues where it was interrupted.",
         "Running a handler", "The kernel borrows the program's own stack.", parts)


# --------------------------------------------------------------- chapter 6

@figure
def cfs_queue():
    accent, tint = KINDS["model"]
    rows = [("B", "nice 0, weight 1024", 2.0, "runs next"), ("A", "nice 0, weight 1024", 3.0, ""),
            ("C", "nice 5, weight 335", 3.06, "")]
    parts = [zone(32, 104, 416, 236, "run queue, ordered by virtual runtime")]

    for k, (name, sub, vruntime, mark) in enumerate(rows):
        y = 128 + 68 * k
        parts += [card(48, y, 170, 56, "good" if mark else "client", name, [sub]),
                  box(234, y + 16, 46 * vruntime, 24, tint, accent, 5),
                  text(242 + 46 * vruntime, y + 33, "%.2f ms" % vruntime, "mono strong")]

        if mark:
            parts.append(text(240, y + 10, mark, "note"))

    parts += [
        card(60, 380, 360, 74, "store", "After a task runs for 1 slice", ["vruntime += slice x 1024 / weight", "then it is put back in order"], glyph="clock"),
        wire([(240, 340), (240, 380)]),
        lines(32, 484, ["A task of weight 1024 is charged the time it ran. C is charged 3.06 ms",
                        "for each 1 ms, so it reaches the front of the queue less often."]),
    ]
    save(OUT / "cfs-queue.svg", WIDTH, 522,
         "A run queue of 3 tasks ordered by virtual runtime. B, at nice 0 with weight 1024, has 2.00 ms and "
         "runs next. A, also nice 0, has 3.00 ms. C, at nice 5 with weight 335, has 3.06 ms. After a task runs "
         "for a slice, its virtual runtime grows by the slice times 1024 divided by its weight, and it is put "
         "back in order.",
         "The smallest vruntime runs next", "Weight decides how fast a task's vruntime grows.", parts)


@figure
def nice_shares():
    rows = [(-5, 3121, 75), (0, 1024, 50), (5, 335, 25), (10, 110, 10)]
    accent, tint = KINDS["client"]
    parts = [text(32, 104, "nice", "tab"), text(92, 104, "weight", "tab"),
             text(176, 104, "share against a task of nice 0", "tab")]

    for k, (nice, weight, share) in enumerate(rows):
        y = 122 + 52 * k
        parts += [text(32, y + 23, str(nice), "mono strong"), text(92, y + 23, str(weight), "mono strong"),
                  box(176, y, 272, 36, CARD, EDGE, 6),
                  box(176, y, 272 * share / 100, 36, tint, accent, 6),
                  text(184 + 272 * share / 100, y + 23, "%d%%" % share, "mono strong")]

    parts.append(lines(32, 356, ["share = weight / (weight + 1024). Each step of nice changes",
                                 "the weight by about 25%."]))
    save(OUT / "nice-shares.svg", WIDTH, 394,
         "The weight of 4 nice values and the share of a CPU each receives against a task of nice 0. Nice -5 "
         "has weight 3121 and receives 75%. Nice 0 has weight 1024 and receives 50%. Nice 5 has weight 335 and "
         "receives 25%. Nice 10 has weight 110 and receives 10%.",
         "From nice to a share of the CPU", "The share is the task's weight over the sum of the weights.", parts)



@figure
def sched_tick():
    parts, bottom = chain([
        ("client", "Task A is running", "on CPU 0", "terminal"),
        ("store", "Timer interrupt", "every 4 ms on this machine", "clock"),
        ("store", "Charge A", "vruntime += time run x 1024 / weight", "pencil"),
        ("store", "Has A used its slice?", "if so, mark A: reschedule", "search"),
        ("service", "Pick the next task", "the smallest vruntime in the queue", "stack"),
        ("good", "Context switch", "save A's registers, load B's", "swap"),
        ("client", "Task B is running", "A waits in the run queue", "terminal"),
    ])
    save(OUT / "sched-tick.svg", WIDTH, bottom,
         "How the scheduler takes a CPU from a task. Task A is running on CPU 0. A timer interrupt arrives. The "
         "kernel charges A: its vruntime grows by the time it ran times 1024 divided by its weight. If A has "
         "used its slice, it is marked for rescheduling. The scheduler picks the task with the smallest "
         "vruntime in the queue and performs a context switch, saving A's registers and loading B's. Task B "
         "is now running and A waits in the run queue.",
         "From one task to the next", "A timer interrupt gives the scheduler control.", parts)


@figure
def sched_structs():
    parts, y = [], 96
    blocks = [
        ("client", "struct task_struct", ["policy       SCHED_OTHER, SCHED_FIFO, ...", "static_prio  from the nice value",
                                          "se           the entity below"]),
        ("store", "struct sched_entity", ["load.weight      1024 for nice 0", "vruntime         virtual runtime, ns",
                                          "sum_exec_runtime real CPU time, ns", "on_rq            in the run queue?",
                                          "run_node         its node in the tree"]),
        ("service", "struct cfs_rq (1 per CPU)", ["tasks_timeline  tree ordered by vruntime", "min_vruntime    smallest in the queue",
                                                 "nr_running      runnable tasks", "curr            the entity on the CPU"]),
    ]

    for k, (kind, title, rows) in enumerate(blocks):
        block, h = fields(40, y, 400, kind, title, rows)
        parts.append(block)

        if k:
            parts.append(wire([(240, y - 26), (240, y)]))

        y += h + 26

    save(OUT / "sched-structs.svg", WIDTH, y - 2,
         "The scheduler's structures. struct task_struct has the policy, static_prio derived from the nice "
         "value, and the entity se. struct sched_entity has load.weight, vruntime, sum_exec_runtime, on_rq and "
         "run_node. Each CPU has a struct cfs_rq with tasks_timeline, a tree ordered by vruntime, min_vruntime, "
         "nr_running and curr.",
         "The structures of the scheduler", "A selection of fields from Linux 5.15.", parts)


@figure
def sched_classes():
    rows = [("danger", "Deadline", "SCHED_DEADLINE", "runs first: tasks with a declared deadline"),
            ("store", "Real time", "SCHED_FIFO, SCHED_RR", "fixed priority 1 to 99, highest first"),
            ("good", "Fair", "SCHED_OTHER, SCHED_BATCH", "nice -20 to 19: the subject of this chapter"),
            ("idle", "Idle", "SCHED_IDLE", "runs when nothing else is runnable")]
    parts = []

    for k, (kind, name, policies, what) in enumerate(rows):
        y = 96 + 84 * k
        parts.append(card(48, y, 384, 68, kind, name, [policies, what]))

        if k:
            parts.append(wire([(240, y - 16), (240, y)]))

    parts.append(lines(32, 96 + 84 * len(rows) + 10, ["The scheduler asks each class in this order for a task. A runnable",
                                                      "real-time task always runs before any task of the fair class."]))
    save(OUT / "sched-classes.svg", WIDTH, 96 + 84 * len(rows) + 48,
         "The scheduling classes in order of precedence. Deadline, with the policy SCHED_DEADLINE, runs first. "
         "Real time, with SCHED_FIFO and SCHED_RR, has fixed priorities 1 to 99. Fair, with SCHED_OTHER and "
         "SCHED_BATCH, uses nice values -20 to 19. Idle, with SCHED_IDLE, runs when nothing else is runnable.",
         "Scheduling classes", "Almost every task on a system is in the fair class.", parts)


@figure
def sched_cpus():
    accent, tint = KINDS["good"]
    parts = []

    for cpu, (count, y) in enumerate([(4, 104), (1, 278)]):
        parts.append(zone(32, y, 416, 104, "CPU %d: its own run queue" % cpu))

        for k in range(count):
            parts.append(box(52 + 62 * k, y + 30, 54, 44, tint if k else KINDS["client"][1],
                             accent if k else KINDS["client"][0], 8))
            parts.append(text(79 + 62 * k, y + 57, "ABCD"[k] if cpu == 0 else "E", "mono strong", "middle"))

        parts.append(text(432, y + 90, "running: %s" % ("A" if cpu == 0 else "E"), "note", "end"))

    parts += [wire([(300, 208), (300, 264)], label="load balancing moves a task"),
              lines(32, 418, ["Each CPU schedules its own queue under its own lock. Periodically,",
                              "and when a CPU becomes idle, the kernel moves tasks from a long",
                              "queue to a short one."])]
    save(OUT / "sched-cpus.svg", WIDTH, 474,
         "CPU 0 has its own run queue with 4 tasks, A, B, C and D, of which A is running. CPU 1 has its own run "
         "queue with 1 task, E. Load balancing moves a task from the longer queue to the shorter one.",
         "A run queue for each CPU", "Balancing keeps the queues of the CPUs similar in length.", parts)


# --------------------------------------------------------------- chapter 7

@figure
def page_fault():
    parts = [
        card(90, 96, 300, 56, "client", "The program reads or writes", ["a virtual address"], glyph="terminal"),
        wire([(240, 152), (240, 184)]),
        card(90, 184, 300, 56, "service", "Processor: page table", ["is there an entry that allows it?"], glyph="chip"),
        wire([(240, 240), (240, 296)], label="no: page fault"),
        card(90, 296, 300, 56, "store", "Kernel: mappings", ["does a mapping allow the access?"], glyph="search"),
        wire([(240, 352), (240, 408)], label="yes"),
        card(90, 408, 300, 74, "good", "Fill in the entry", ["zero frame, new frame,", "or a private copy"], glyph="pencil"),
        wire([(390, 445), (432, 445), (432, 212), (390, 212)], kind="idle"),
        text(436, 330, "retry", "note", "middle"),
        wire([(90, 324), (56, 324), (56, 526), (90, 526)], kind="danger"),
        card(90, 498, 300, 56, "danger", "SIGSEGV", ["no mapping allows the access"]),
        text(52, 420, "no", "note", "end"),
    ]
    save(OUT / "page-fault.svg", WIDTH, 582,
         "A program reads or writes a virtual address. The processor looks in the page table for an entry that "
         "allows the access. When there is none, it raises a page fault. The kernel checks whether a mapping "
         "allows the access. If so, it fills in the page table entry with the zero frame, a new frame or a "
         "private copy, and the access is retried. If no mapping allows it, the kernel sends SIGSEGV.",
         "A page fault", "The page table is filled in when a page is first used.", parts)


def table_entry(x, y, name, note, kind):
    return card(x, y, 150, 52, kind, name, [note])


@figure
def cow_fork():
    accent, tint = KINDS["store"]
    parts = [
        zone(32, 104, 416, 170, "after fork"),
        table_entry(48, 128, "parent, page 0", "read-only", "client"),
        table_entry(282, 128, "child, page 0", "read-only", "outside"),
        box(180, 216, 120, 40, tint, accent, 8),
        text(240, 241, "frame 1: a", "mono strong", "middle"),
        wire([(123, 180), (123, 236), (180, 236)]),
        wire([(357, 180), (357, 236), (300, 236)]),

        zone(32, 314, 416, 170, "after the child writes b"),
        table_entry(48, 338, "parent, page 0", "read-only", "client"),
        table_entry(282, 338, "child, page 0", "writable", "outside"),
        box(48, 426, 150, 40, tint, accent, 8),
        text(123, 451, "frame 1: a", "mono strong", "middle"),
        box(282, 426, 150, 40, KINDS["good"][1], KINDS["good"][0], 8),
        text(357, 451, "frame 3: b", "mono strong", "middle"),
        wire([(123, 390), (123, 426)]),
        wire([(357, 390), (357, 426)]),
        lines(32, 512, ["The write faults because the entry is read-only. The kernel copies",
                        "the frame for the writer and leaves the other process untouched."]),
    ]
    save(OUT / "cow-fork.svg", WIDTH, 548,
         "After fork, page 0 of the parent and page 0 of the child both refer to frame 1, which holds a, and "
         "both entries are read-only. After the child writes b, the child's entry is writable and refers to a "
         "new frame 3 that holds b. The parent's entry still refers to frame 1.",
         "Copy-on-write after fork", "Frames are shared until one side writes.", parts)



@figure
def address_layout():
    rows = [("idle", "[stack]", "rw-p", "local variables; grows downward", 46),
            ("idle", "(unmapped)", "", "", 26),
            ("outside", "libc.so.6, ld-linux", "r-xp, r--p, rw-p", "shared libraries, mapped from files", 56),
            ("service", "anonymous mappings", "rw-p", "large allocations, thread stacks", 46),
            ("idle", "(unmapped)", "", "", 26),
            ("store", "[heap]", "rw-p", "malloc; grows upward with brk", 46),
            ("client", "/usr/bin/cat, data", "rw-p", "global variables", 46),
            ("client", "/usr/bin/cat, code", "r-xp", "the program's instructions", 46)]
    parts = [text(32, 104, "high addresses", "tab"), text(448, 104, "permissions", "tab", "end")]
    y = 116

    for kind, name, perms, what, h in rows:
        accent, tint = KINDS[kind]
        gap = name == "(unmapped)"
        parts.append(box(32, y, 416, h, CARD if gap else tint, EDGE if gap else accent, 6))
        parts.append(text(46, y + (17 if what else h / 2 + 4), name, "mono dim" if gap else "mono strong"))

        if what:
            parts += [text(46, y + 35, what, "note"), text(434, y + 17, perms, "mono", "end")]

        y += h + 6

    parts.append(text(32, y + 12, "low addresses", "tab"))
    save(OUT / "address-layout.svg", WIDTH, y + 30,
         "The address space of a cat process from high addresses to low. The stack, read-write, holds local "
         "variables and grows downward. Below it are the shared libraries libc and ld-linux, mapped from files. "
         "Then anonymous mappings for large allocations and thread stacks. Then the heap, read-write, used by "
         "malloc and grown upward with brk. Then the data of /usr/bin/cat, read-write, with its global "
         "variables. At the lowest addresses is the code of /usr/bin/cat, readable and executable.",
         "The layout of an address space", "The mappings of a small program, from /proc/self/maps.", parts)


@figure
def va_split():
    cells = [("level 0", 9, "client"), ("level 1", 9, "client"), ("level 2", 9, "client"), ("level 3", 9, "client"),
             ("offset", 12, "store")]
    parts, x = [text(32, 104, "a virtual address: 48 bits", "tab")], 32

    for name, bits, kind in cells:
        w = 76 if bits == 9 else 100
        accent, tint = KINDS[kind]
        parts += [box(x, 116, w, 50, tint, accent, 6), text(x + w / 2, 137, name, "pill", "middle", accent),
                  text(x + w / 2, 156, "%d bits" % bits, "mono strong", "middle")]
        x += w + 4

    parts.append(lines(32, 200, ["Each of the 4 index fields selects 1 of 512 entries in a table of the",
                                 "page table tree. The last table gives the frame. The offset, 12 bits,",
                                 "selects 1 of 4096 bytes inside the frame."]))
    save(OUT / "va-split.svg", WIDTH, 256,
         "A virtual address of 48 bits is divided into 5 fields: 4 index fields of 9 bits each, for levels 0 "
         "to 3 of the page table, and an offset of 12 bits. Each index selects 1 of 512 entries of a table, and "
         "the offset selects a byte within the frame.",
         "The fields of a virtual address", "arm64 with pages of 4096 bytes, as on this machine.", parts)


@figure
def page_table_walk():
    parts, bottom = chain([
        ("client", "Virtual address", "split into 4 indexes and an offset", "terminal"),
        ("service", "Level 0 table", "the root, mm->pgd; index 0 selects an entry", "stack"),
        ("service", "Level 1 table", "index 1 selects an entry", "stack"),
        ("service", "Level 2 table", "index 2 selects an entry", "stack"),
        ("service", "Level 3 table", "index 3 selects the page table entry", "stack"),
        ("good", "Frame + offset", "the physical address", "chip"),
    ], x=60, w=360)
    parts.append(lines(32, bottom + 4, ["An empty entry at any level means that the page has no frame, and",
                                        "the processor raises a page fault. The TLB, a cache in the processor,",
                                        "keeps recent results, so most accesses skip the walk."]))
    save(OUT / "page-table-walk.svg", WIDTH, bottom + 60,
         "The translation of a virtual address. The address is split into 4 indexes and an offset. The level 0 "
         "table, the root that mm->pgd points to, is indexed with index 0, and the entry leads to a level 1 "
         "table. Index 1 leads to a level 2 table, index 2 to a level 3 table, and index 3 selects the page "
         "table entry, which gives the frame. The frame and the offset form the physical address.",
         "Walking the page table", "The processor does this by itself, without the kernel.", parts)


@figure
def vm_structs():
    parts, y = [], 96
    blocks = [
        ("client", "struct mm_struct (1 per process)", ["mmap, mm_rb   the mappings: list and tree", "pgd           the root of the page table",
                                                        "map_count     number of mappings", "total_vm      pages mapped",
                                                        "start_brk, brk  the heap", "start_stack   the stack"]),
        ("store", "struct vm_area_struct (1 per mapping)", ["vm_start, vm_end  the address range", "vm_flags   read, write, exec, shared",
                                                            "vm_file    the mapped file, or NULL", "vm_pgoff   offset in the file, in pages"]),
        ("service", "struct page (1 per frame)", ["_refcount  users of the frame", "_mapcount  page table entries mapping it",
                                                  "mapping    the file it caches, if any", "flags      dirty, locked, ..."]),
    ]

    for k, (kind, title, rows) in enumerate(blocks):
        block, h = fields(40, y, 400, kind, title, rows)
        parts.append(block)

        if k:
            parts.append(wire([(240, y - 26), (240, y)]))

        y += h + 26

    save(OUT / "vm-structs.svg", WIDTH, y - 2,
         "The memory structures. Each process has a struct mm_struct with the list and tree of mappings, pgd, "
         "the root of the page table, map_count, total_vm, and the bounds of the heap and the stack. Each "
         "mapping is a struct vm_area_struct with vm_start and vm_end, vm_flags, vm_file and vm_pgoff. Each "
         "frame of physical memory has a struct page with _refcount, _mapcount, mapping and flags.",
         "The structures of an address space", "A selection of fields from Linux 5.15.", parts)


# --------------------------------------------------------------- chapter 8

@figure
def cache_paths():
    clean, dirty = KINDS["model"], KINDS["danger"]
    parts = [
        card(32, 96, 196, 64, "client", "read", ["copies from a page"], glyph="eye"),
        card(252, 96, 196, 64, "client", "write", ["copies into a page"], glyph="pencil"),
        wire([(130, 228), (130, 160)]),
        wire([(350, 160), (350, 228)]),
        zone(32, 228, 416, 110, "page cache of the file"),
    ]

    for k in range(8):
        accent, tint = dirty if k == 5 else clean
        present = k not in (2, 7)
        parts.append(box(56 + 46 * k, 254, 38, 38, tint if present else CARD, accent if present else EDGE, 6))
        parts.append(text(75 + 46 * k, 278, str(k), "mono strong" if present else "mono dim", "middle"))

    parts += [
        text(240, 322, "pages 2 and 7 are not cached; page 5 is dirty", "sub", "middle"),
        wire([(130, 412), (130, 338)], label="on a miss"),
        wire([(350, 338), (350, 412)], label="writeback"),
        cylinder(90, 412, 300, 70, "store", "disk", ["the file's blocks"]),
    ]
    save(OUT / "cache-paths.svg", WIDTH, 510,
         "A read copies from a cached page of the file and a write copies into one. The page cache holds pages 0 "
         "to 7 of the file, except pages 2 and 7, which are not cached. Page 5 is dirty. A page is read from "
         "the disk on a miss, and dirty pages are written to the disk later, by writeback.",
         "Between a program and the disk", "Reads and writes go to memory first.", parts)


@figure
def readahead_windows():
    groups = [(0, 2, "client"), (2, 6, "service"), (6, 14, "store"), (14, 16, "outside")]
    parts = []

    for k, (first, last, kind) in enumerate(groups):
        y = 104 + 62 * k
        accent, tint = KINDS[kind]
        parts.append(text(32, y + 12, "request %d: pages %d to %d" % (k + 1, first, last - 1), "note"))

        for page in range(16):
            mine = first <= page < last
            earlier = page < first
            parts.append(box(32 + 26 * page, y + 20, 22, 26, tint if mine else ("#EEF0F3" if earlier else CARD),
                             accent if mine else EDGE, 4))
            parts.append(text(43 + 26 * page, y + 38, str(page), "pill", "middle", accent if mine else "#8794A3"))

    parts.append(lines(32, 372, ["The window is 2 pages, then 4, then 8. Request 4 stops at the end",
                                 "of the file. 16 pages arrive in 4 requests."]))
    save(OUT / "readahead-windows.svg", WIDTH, 410,
         "A sequential read of a file of 16 pages makes 4 disk requests. Request 1 loads pages 0 and 1. Request "
         "2 loads pages 2 to 5. Request 3 loads pages 6 to 13. Request 4 loads pages 14 and 15, where the file "
         "ends.",
         "Readahead for a sequential read", "Each miss loads a window of pages, and the window doubles.", parts)



@figure
def cache_read_path():
    parts, bottom = chain([
        ("client", "read(fd, buf, 4096)", "at offset 8192 of the file", "terminal"),
        ("service", "struct file, then the inode", "f_pos gives page number 2", "doc"),
        ("store", "Look up page 2", "in the inode's address_space", "search"),
        ("good", "Cached: copy to buf", "no disk request", "pencil"),
    ], x=60, w=360)
    parts += [
        wire([(60, 257), (40, 257), (40, 440), (60, 440)], kind="danger"),
        card(60, bottom + 10, 360, 74, "danger", "Missing: read from disk", ["allocate a frame, read the block and its", "neighbours, insert them, then copy"], glyph="chip"),
        text(36, 350, "miss", "note", "end"),
    ]
    save(OUT / "cache-read-path.svg", WIDTH, bottom + 104,
         "The path of a read of 4096 bytes at offset 8192. The struct file and the inode give page number 2. "
         "The kernel looks page 2 up in the inode's address_space. If it is cached, the bytes are copied to "
         "the buffer with no disk request. If it is missing, the kernel allocates a frame, reads the block and "
         "its neighbours from the disk, inserts them in the cache, and then copies.",
         "One read through the page cache", "The cache is consulted before the disk.", parts)


@figure
def write_durability():
    steps = [("client", "write returns", "the data is in a cached page, marked dirty", "0 s"),
             ("store", "The page becomes old enough", "dirty for dirty_expire_centisecs: 30 s", "30 s"),
             ("store", "A flusher thread writes it", "they wake every 5 s", "30 to 35 s"),
             ("good", "The data is on the disk", "the page is clean again", "")]
    parts = []

    for k, (kind, name, sub, when) in enumerate(steps):
        y = 96 + 76 * k
        parts.append(card(110, y, 338, 58, kind, name, [sub]))
        parts.append(text(96, y + 34, when, "mono strong", "end"))

        if k:
            parts.append(wire([(279, y - 18), (279, y)]))

    y = 96 + 76 * len(steps) + 8
    parts += [card(32, y, 416, 82, "danger", "A power failure before this loses the data",
                   ["fsync(fd) returns when the file's dirty pages", "are on the disk"])]
    save(OUT / "write-durability.svg", WIDTH, y + 102,
         "The timeline of written data. At 0 seconds write returns, and the data is in a cached page marked "
         "dirty. After 30 seconds the page is old enough to be written. A flusher thread, which wakes every 5 "
         "seconds, writes it between 30 and 35 seconds. Then the data is on the disk and the page is clean. A "
         "power failure before the last step loses the data, and fsync waits until the file's dirty pages are "
         "on the disk.",
         "When written data reaches the disk", "With the default settings of this machine.", parts)


@figure
def lru_lists():
    hot, cold = KINDS["good"], KINDS["idle"]
    parts = [zone(32, 104, 416, 96, "active list"), text(432, 190, "used more than once recently", "note", "end")]

    for k in range(6):
        parts.append(box(52 + 64 * k, 128, 54, 40, hot[1], hot[0], 6))

    parts += [zone(32, 272, 416, 96, "inactive list"), text(432, 358, "candidates for eviction", "note", "end")]

    for k in range(6):
        parts.append(box(52 + 64 * k, 296, 54, 40, cold[1], cold[0], 6))

    parts += [
        wire([(150, 200), (150, 260)], label="not used lately"),
        wire([(330, 260), (330, 200)], label="used again"),
        wire([(79, 420), (79, 368)]),
        text(92, 412, "a new page enters here", "note"),
        wire([(412, 368), (412, 420)], kind="danger"),
        text(400, 440, "evicted from here when memory is needed", "note", "end"),
        lines(32, 476, ["A page read once, such as a page of a large file copied a single",
                        "time, passes through the inactive list and leaves. Pages in constant",
                        "use stay on the active list."]),
    ]
    save(OUT / "lru-lists.svg", WIDTH, 528,
         "The kernel keeps cached pages on 2 lists. A new page enters the inactive list, which holds the "
         "candidates for eviction. A page that is used again moves to the active list, and a page on the "
         "active list that has not been used lately moves back to the inactive list. Pages are evicted from "
         "the tail of the inactive list when memory is needed.",
         "The lists behind eviction", "An approximation of least recently used.", parts)


# --------------------------------------------------------------- chapter 9

@figure
def epoll_lists():
    accent, tint = KINDS["good"]
    parts = [zone(32, 104, 416, 96, "interest list: every registered descriptor")]

    for k in range(8):
        hot = k in (2, 5)
        parts.append(box(48 + 49 * k, 130, 41, 38, tint if hot else CARD, accent if hot else EDGE, 6))
        parts.append(text(68.5 + 49 * k, 154, str(5 + k), "mono strong" if hot else "mono dim", "middle"))

    parts += [
        text(240, 188, "data arrived on descriptors 7 and 10", "sub", "middle"),
        wire([(240, 200), (240, 262)], label="each arrival adds an entry"),
        zone(32, 262, 416, 84, "ready list"),
        box(170, 286, 60, 38, tint, accent, 6), text(200, 310, "10", "mono strong", "middle"),
        box(250, 286, 60, 38, tint, accent, 6), text(280, 310, "7", "mono strong", "middle"),
        wire([(240, 346), (240, 408)], label="epoll_wait copies it out"),
        card(90, 408, 300, 64, "client", "The program", ["handles descriptor 10, then 7"], glyph="terminal"),
    ]
    save(OUT / "epoll-lists.svg", WIDTH, 500,
         "An epoll instance has an interest list of every registered descriptor, here 5 to 12. Data arrived on "
         "descriptors 7 and 10, and each arrival added an entry to the ready list, which holds 10 and then 7. "
         "epoll_wait copies the ready list to the program, which handles descriptor 10 and then 7.",
         "The lists of an epoll instance", "A wait reads the ready list and leaves the rest alone.", parts)


def step(x, y, w, body, kind):
    accent, tint = KINDS[kind]

    return "\n".join([box(x, y, w, 34, tint, accent, 8), text(x + w / 2, y + 22, body, "pill", "middle", accent)])


@figure
def level_edge():
    rows = [("level-triggered", [("write", "client"), ("wait: 1", "good"), ("wait: 1", "good"), ("read all", "client"),
                                 ("wait: 0", "idle")]),
            ("edge-triggered", [("write", "client"), ("wait: 1", "good"), ("wait: 0", "idle"), ("write", "client"),
                                ("wait: 1", "good")])]
    parts = []

    for k, (label, steps) in enumerate(rows):
        y = 104 + 110 * k
        parts.append(zone(32, y, 416, 78, label))
        parts += [step(44 + 79 * i, y + 26, 73, body, kind) for i, (body, kind) in enumerate(steps)]

    parts.append(lines(32, 322, ["Level-triggered reports a descriptor while it is readable.",
                                 "Edge-triggered reports it when new data arrives."]))
    save(OUT / "level-edge.svg", WIDTH, 360,
         "With a level-triggered registration, after a write the first wait returns 1 event, a second wait "
         "without reading returns 1 event again, and after reading all the data a wait returns 0 events. With "
         "an edge-triggered registration, after a write the first wait returns 1 event, a second wait returns 0 "
         "events, and after another write a wait returns 1 event.",
         "Level-triggered and edge-triggered", "The same writes and waits, registered in 2 ways.", parts)



@figure
def epoll_wake_path():
    parts, bottom = chain([
        ("client", "A peer writes to descriptor 7", "data arrives in its buffer", "pencil"),
        ("store", "Its wait queue is woken", "as for any sleeping reader", "listen"),
        ("store", "ep_poll_callback runs", "the entry epoll added to that queue", "gear"),
        ("service", "The item joins the ready list", "rdllist of the epoll instance", "stack"),
        ("service", "The waiting thread is woken", "it sleeps in epoll_wait", "clock"),
        ("good", "epoll_wait returns", "the event, with the stored data value", "terminal"),
    ])
    save(OUT / "epoll-wake-path.svg", WIDTH, bottom,
         "How a descriptor reaches the ready list. A peer writes to descriptor 7 and data arrives in its "
         "buffer. The wait queue of the file is woken, as for any sleeping reader. The entry that epoll added "
         "to that queue runs ep_poll_callback, which puts the item on rdllist, the ready list of the epoll "
         "instance, and wakes the thread that sleeps in epoll_wait. epoll_wait returns the event with the "
         "stored data value.",
         "From arriving data to epoll_wait", "The writer does the work of finding the ready descriptor.", parts)


@figure
def epoll_structs():
    parts, y = [], 96
    blocks = [
        ("service", "struct eventpoll (the epoll instance)", ["rbr      interest list: tree of items", "rdllist  ready list",
                                                             "wq       threads asleep in epoll_wait", "mtx      lock for epoll_ctl"]),
        ("store", "struct epitem (1 per registration)", ["ffd      the file and descriptor watched", "event    events asked for, and data",
                                                         "rbn      its node in the interest tree", "rdllink  its link in the ready list",
                                                         "pwqlist  its entry on the file's wait queue"]),
        ("client", "struct epoll_event (seen by the program)", ["events  EPOLLIN, EPOLLOUT, EPOLLHUP, EPOLLET", "data    64 bits chosen by the program"]),
    ]

    for k, (kind, title, rows) in enumerate(blocks):
        block, h = fields(40, y, 400, kind, title, rows)
        parts.append(block)

        if k:
            parts.append(wire([(240, y - 26), (240, y)]))

        y += h + 26

    save(OUT / "epoll-structs.svg", WIDTH, y - 2,
         "The structures of epoll. A struct eventpoll is the epoll instance, with rbr, the interest list as a "
         "tree of items, rdllist, the ready list, wq, the threads asleep in epoll_wait, and mtx. A struct "
         "epitem is a registration, with ffd, the file and descriptor watched, event, its node in the tree, "
         "its link in the ready list, and its entry on the file's wait queue. A struct epoll_event is what "
         "the program sees: events and 64 bits of data.",
         "The structures of epoll", "From fs/eventpoll.c of Linux 5.15.", parts)


@figure
def server_loop():
    parts = [
        card(70, 96, 340, 58, "client", "epoll_create1", ["returns a descriptor for the instance"], glyph="terminal"),
        wire([(240, 154), (240, 172)]),
        card(70, 172, 340, 58, "client", "epoll_ctl: add the listener", ["EPOLLIN on a listening socket"], glyph="pencil"),
        wire([(240, 230), (240, 248)]),
        card(70, 248, 340, 58, "service", "epoll_wait", ["sleeps until a descriptor is ready"], glyph="clock"),
        wire([(240, 306), (240, 336), (130, 336), (130, 366)]),
        wire([(240, 306), (240, 336), (350, 336), (350, 366)]),
        card(32, 366, 196, 92, "good", "The listener", ["accept the connection,", "set it non-blocking,", "add it with epoll_ctl"]),
        card(252, 366, 196, 92, "good", "A connection", ["read until EAGAIN,", "handle the request,", "write the reply"]),
        wire([(448, 412), (464, 412), (464, 277), (410, 277)], kind="idle"),
        text(240, 486, "then back to epoll_wait", "note", "middle"),
    ]
    save(OUT / "server-loop.svg", WIDTH, 506,
         "The structure of a server built on epoll. epoll_create1 returns a descriptor for the instance. "
         "epoll_ctl adds the listening socket for EPOLLIN. epoll_wait sleeps until a descriptor is ready. For "
         "the listener, the server accepts the connection, sets it non-blocking, and adds it with epoll_ctl. "
         "For a connection, it reads until EAGAIN, handles the request and writes the reply. Then it returns "
         "to epoll_wait.",
         "A server on a single thread", "The 3 calls of epoll in the order a server makes them.", parts)


# --------------------------------------------------------------- chapter 10

@figure
def socket_demux():
    parts = [
        card(90, 96, 300, 56, "client", "A segment arrives", ["from 10.0.0.2:5000, for port 80"], glyph="swap"),
        wire([(240, 152), (240, 200)]),
        zone(32, 200, 416, 150, "connections"),
        card(48, 224, 384, 50, "idle", "10.0.0.1:5000, port 80", ["a different connection on port 80"]),
        card(48, 284, 384, 50, "good", "10.0.0.2:5000, port 80", ["match: the data goes to this socket"]),
        wire([(240, 350), (240, 412)], label="no match, and a SYN"),
        zone(32, 412, 416, 100, "listener on port 80"),
        text(48, 444, "accept queue, backlog 2", "note"),
        box(48, 456, 120, 38, KINDS["store"][1], KINDS["store"][0], 8),
        text(108, 480, "10.0.0.1:5000", "pill", "middle", KINDS["store"][0]),
        box(178, 456, 120, 38, KINDS["store"][1], KINDS["store"][0], 8),
        text(238, 480, "10.0.0.2:5000", "pill", "middle", KINDS["store"][0]),
        text(312, 480, "full: a SYN is dropped", "note"),
    ]
    save(OUT / "socket-demux.svg", WIDTH, 540,
         "A segment arrives from 10.0.0.2 port 5000 for local port 80. The kernel looks it up in the table of "
         "connections, which is keyed by remote endpoint and local port. The entry for 10.0.0.1 port 5000 is a "
         "different connection on port 80. The entry for 10.0.0.2 port 5000 matches, and the data goes to that "
         "socket. A SYN that matches no connection goes to the listener on port 80, whose accept queue has a "
         "backlog of 2 and is full, so a further SYN is dropped.",
         "Finding the socket for a segment", "Many connections share port 80 and are kept apart.", parts)


@figure
def socket_buffers():
    accent, tint = KINDS["store"]
    parts = [
        card(90, 96, 300, 56, "client", "Sender: write", ["copies into the send buffer"], glyph="pencil"),
        wire([(240, 152), (240, 184)]),
        box(110, 184, 260, 40, tint, accent, 8), text(240, 209, "send buffer", "mono strong", "middle"),
        wire([(240, 224), (240, 286)], label="segments, up to the window"),
        box(110, 286, 260, 40, tint, accent, 8), text(240, 311, "receive buffer", "mono strong", "middle"),
        wire([(240, 326), (240, 358)]),
        card(90, 358, 300, 56, "service", "Receiver: read", ["copies out of the receive buffer"], glyph="eye"),
        wire([(370, 306), (432, 306), (432, 204), (370, 204)], kind="idle"),
        lines(32, 448, ["The receiver reports the free space of its receive buffer in every",
                        "acknowledgement. That number is the window. When it reaches 0 the",
                        "sender stops sending, its send buffer fills, and write blocks."]),
        text(436, 262, "window", "note", "middle"),
    ]
    save(OUT / "socket-buffers.svg", WIDTH, 504,
         "The sender's write copies into a send buffer. The kernel sends segments from it, up to the window, to "
         "the receive buffer of the peer. The receiver's read copies out of the receive buffer. The receiver "
         "reports the free space of its receive buffer back to the sender as the window. When the window is 0 "
         "the sender stops sending, its send buffer fills, and write blocks.",
         "The buffers of a connection", "The receiver's free space limits the sender.", parts)



@figure
def tcp_exchange():
    rows = [(">", "SYN, seq 1000", "connect"), ("<", "SYN + ACK, seq 5000, ack 1001", ""), (">", "ACK, ack 5001", "established"),
            (">", "5 bytes, seq 1001", "write"), ("<", "ACK, ack 1006, window 65531", ""),
            (">", "FIN, seq 1006", "close"), ("<", "ACK, ack 1007", "read returns 0")]
    parts = [card(32, 96, 150, 44, "client", "client", []), card(298, 96, 150, 44, "service", "server", []),
             f'  <line x1="107" y1="140" x2="107" y2="{164 + 46 * len(rows)}" stroke="{EDGE}" stroke-width="2"/>',
             f'  <line x1="373" y1="140" x2="373" y2="{164 + 46 * len(rows)}" stroke="{EDGE}" stroke-width="2"/>']

    for k, (way, label, note) in enumerate(rows):
        y = 172 + 46 * k
        ends = [(107, y), (373, y)] if way == ">" else [(373, y), (107, y)]
        parts.append(wire(ends, label=label))

        if note:
            parts.append(text(107 if way == ">" else 373, y - 12, note, "note", "middle"))

    y = 172 + 46 * len(rows)
    parts.append(lines(32, y + 8, ["Every byte has a sequence number. An acknowledgement names",
                                  "the next byte the receiver expects, and carries the window."]))
    save(OUT / "tcp-exchange.svg", WIDTH, y + 48,
         "The segments of a short TCP connection between a client and the server's kernel. The client sends "
         "SYN with sequence number 1000. The server answers SYN and ACK with its own sequence number 5000 and "
         "acknowledgement 1001. The client sends ACK with acknowledgement 5001, and the connection is "
         "established. The client sends 5 bytes at sequence 1001, and the server acknowledges 1006 with a "
         "window of 65531. The client sends FIN at sequence 1006, and the server acknowledges 1007.",
         "The segments of a connection", "A handshake, 5 bytes of data, and the close of 1 direction.", parts)


@figure
def net_layers():
    parts, bottom = chain([
        ("client", "write(fd, buf, n)", "the program", "terminal"),
        ("service", "Socket", "copies into the send buffer", "stack"),
        ("store", "TCP", "segments, sequence numbers, window", "swap"),
        ("store", "IP", "adds the addresses, chooses a route", "search"),
        ("outside", "Network device", "Ethernet, Wi-Fi, or loopback", "chip"),
        ("good", "The peer's kernel", "the same layers, upward", "listen"),
    ])
    save(OUT / "net-layers.svg", WIDTH, bottom,
         "The layers a write passes through. The program calls write. The socket copies the data into the "
         "send buffer. TCP cuts it into segments and adds sequence numbers and the window. IP adds the "
         "addresses and chooses a route. A network device, Ethernet, Wi-Fi or loopback, carries the packet. "
         "The peer's kernel passes it through the same layers upward.",
         "From write to the network", "Each layer adds a header and hands the packet down.", parts)


@figure
def sock_structs():
    parts, y = [], 96
    blocks = [
        ("service", "struct file", ["f_op    the socket's read and write", "private_data  the struct socket"]),
        ("store", "struct sock", ["skc_daddr, skc_dport   remote address, port", "skc_rcv_saddr, skc_num  local address, port",
                                  "skc_state         ESTABLISHED, LISTEN, ...", "sk_receive_queue  data received, not read",
                                  "sk_rcvbuf         limit of that queue", "sk_write_queue    data written, not acked",
                                  "sk_sndbuf         limit of that queue"]),
        ("client", "struct tcp_sock (extends struct sock)", ["snd_una  oldest byte not yet acknowledged", "snd_nxt  next byte to send",
                                                             "rcv_nxt  next byte expected", "snd_wnd  window the peer offered",
                                                             "snd_cwnd congestion window"]),
    ]

    for k, (kind, title, rows) in enumerate(blocks):
        block, h = fields(40, y, 400, kind, title, rows)
        parts.append(block)

        if k:
            parts.append(wire([(240, y - 26), (240, y)]))

        y += h + 26

    save(OUT / "sock-structs.svg", WIDTH, y - 2,
         "The structures of a TCP socket. A struct file leads to a struct sock, which has the remote address "
         "and port, the local address and port, the state, the receive queue with its limit sk_rcvbuf, and the "
         "write queue with its limit sk_sndbuf. A struct tcp_sock extends it with snd_una, snd_nxt, rcv_nxt, "
         "snd_wnd and snd_cwnd.",
         "The structures of a socket", "A selection of fields from Linux 5.15.", parts)


# --------------------------------------------------------------- chapter 11

@figure
def namespace_kinds():
    kinds = [("pid", "process numbers"), ("mnt", "mounted file systems"), ("uts", "host name"),
             ("net", "interfaces, ports, routes"), ("user", "user and group numbers"),
             ("ipc", "shared memory, queues"), ("cgroup", "the control group root"), ("time", "clock offsets")]
    parts = []

    for k, (name, isolates) in enumerate(kinds):
        x, y = 32 + 212 * (k % 2), 96 + 68 * (k // 2)
        parts.append(card(x, y, 204, 56, "outside" if name in ("pid", "uts", "user") else "idle", name, [isolates]))

    parts.append(lines(32, 388, ["A process is in exactly 1 namespace of each kind. The 3 marked kinds",
                                 "are the ones this chapter creates."]))
    save(OUT / "namespace-kinds.svg", WIDTH, 426,
         "The 8 kinds of namespace and what each isolates: pid, process numbers; mnt, mounted file systems; "
         "uts, host name; net, interfaces, ports and routes; user, user and group numbers; ipc, shared memory "
         "and queues; cgroup, the control group root; time, clock offsets.",
         "The kinds of namespace", "Each kind gives processes their own view of 1 resource.", parts)


def numbered_process(x, y, label, numbers, kind="client"):
    return card(x, y, 112, 52, kind, label, [numbers])


@figure
def pid_namespaces():
    parts = [
        zone(32, 104, 416, 414, "root PID namespace"),
        numbered_process(48, 128, "first", "pid 1", "idle"),
        numbered_process(184, 128, "shell", "pid 2", "idle"),
        wire([(160, 154), (184, 154)]),

        zone(48, 224, 184, 278, "namespace A"),
        numbered_process(60, 248, "first", "1, root 3"),
        numbered_process(60, 318, "child", "2, root 4"),
        wire([(116, 300), (116, 318)]),
        zone(60, 402, 160, 86, "nested"),
        numbered_process(72, 422, "first", "1, 3, 6", "outside"),

        zone(248, 224, 184, 100, "namespace B"),
        numbered_process(260, 248, "first", "1, root 5", "service"),
        lines(248, 352, ["A process has a number in", "its own namespace and in", "every namespace around it.", "",
                         "A and B cannot see each", "other. The root namespace", "sees every process."]),
    ]
    save(OUT / "pid-namespaces.svg", WIDTH, 546,
         "The root PID namespace contains the first process, pid 1, and a shell, pid 2. It encloses namespace A "
         "and namespace B. In A, the first process has pid 1 inside and pid 3 in the root, and its child has "
         "pid 2 inside and pid 4 in the root. A namespace nested in A has a first process with pid 1 inside, "
         "pid 3 in A, and pid 6 in the root. In B, the first process has pid 1 inside and pid 5 in the root.",
         "Nested PID namespaces", "The numbers of the model's trace.", parts)



@figure
def nsproxy_map():
    parts, y = [], 96
    blocks = [
        ("client", "struct task_struct", ["nsproxy     most of its namespaces", "cred->user_ns  its user namespace",
                                          "thread_pid  its struct pid"]),
        ("store", "struct nsproxy", ["uts_ns    host name", "ipc_ns    shared memory, queues", "mnt_ns    mounted file systems",
                                     "net_ns    interfaces, routes, ports", "cgroup_ns the control group root",
                                     "time_ns   clock offsets", "pid_ns_for_children"]),
        ("outside", "struct pid", ["level       depth of its PID namespace", "numbers[]   1 struct upid per level:",
                                   "  nr        the number at that level", "  ns        the namespace of that level"]),
    ]

    for k, (kind, title, rows) in enumerate(blocks):
        block, h = fields(40, y, 400, kind, title, rows)
        parts.append(block)

        if k == 1:
            parts.append(wire([(240, y - 26), (240, y)]))

        y += h + 26

    save(OUT / "nsproxy-map.svg", WIDTH, y - 2,
         "How a task refers to its namespaces. struct task_struct has nsproxy, a pointer to its user namespace "
         "through cred, and thread_pid. struct nsproxy has a pointer for each of the UTS, IPC, mount, network, "
         "cgroup and time namespaces, and pid_ns_for_children. struct pid has the level of its PID namespace "
         "and an array numbers with a struct upid for each level, holding the number at that level and the "
         "namespace.",
         "A task and its namespaces", "A selection of fields from Linux 5.15.", parts)


@figure
def uid_map():
    parts = [
        zone(32, 104, 416, 150, "inside the user namespace"),
        card(48, 128, 184, 64, "good", "user 0", ["root, all capabilities"]),
        card(248, 128, 184, 64, "idle", "other users", ["unmapped: seen as 65534"]),
        text(240, 232, "uid_map:   0   1000   1", "mono strong", "middle"),
        wire([(140, 254), (140, 312)], label="maps to"),
        zone(32, 312, 416, 110, "outside: the host"),
        card(48, 336, 184, 64, "client", "user 1000", ["an ordinary user"]),
        lines(32, 450, ["The 3 numbers of a line of uid_map are: the first user number inside,",
                        "the first user number outside, and how many numbers are mapped.",
                        "Capabilities held inside apply to objects the namespace owns. A file",
                        "on the host is still accessed as user 1000."]),
    ]
    save(OUT / "uid-map.svg", WIDTH, 522,
         "A user namespace with the mapping 0 1000 1. Inside the namespace the process is user 0, root, with "
         "all capabilities, and other users are unmapped and shown as 65534. User 0 inside maps to user 1000 "
         "outside, an ordinary user on the host.",
         "A user namespace maps user numbers", "Privileged inside, ordinary outside.", parts)


@figure
def ns_create():
    parts, bottom = chain([
        ("client", "clone with namespace flags", "CLONE_NEWUTS and CLONE_NEWPID", "terminal"),
        ("store", "Permission check", "CAP_SYS_ADMIN in its user namespace", "lock"),
        ("store", "New namespace objects", "the UTS one starts as a copy", "stack"),
        ("store", "A new struct nsproxy", "new pointers for those 2, old for the rest", "doc"),
        ("good", "The child starts", "pid 1 in the new PID namespace", "swap"),
    ], x=50, w=380)
    parts.append(lines(32, bottom + 4, ["The parent keeps its own nsproxy. Nothing changes for it or for any",
                                        "other process."]))
    save(OUT / "ns-create.svg", WIDTH, bottom + 44,
         "What clone does with namespace flags. The parent calls clone with CLONE_NEWUTS and CLONE_NEWPID. The "
         "kernel checks that the caller has CAP_SYS_ADMIN in its user namespace. It creates new namespace "
         "objects; the UTS one starts as a copy of the parent's. It builds a new struct nsproxy with new "
         "pointers for those 2 kinds and the old pointers for the rest. The child starts as pid 1 in the new "
         "PID namespace. The parent keeps its own nsproxy.",
         "Creating a process in new namespaces", "Only the pointers of the child change.", parts)


# --------------------------------------------------------------- chapter 12

@figure
def cgroup_files():
    parts = [
        sheet(32, 96, 416, 262, "store", "A GROUP IS A DIRECTORY", [
            ("strong", "/sys/fs/cgroup/.../team/"),
            ("", "  cgroup.procs      the processes in it"),
            ("", "  pids.max          4"),
            ("", "  pids.current      3"),
            ("", "  pids.events       max 1"),
            ("", "  memory.max        104857600"),
            ("", "  memory.current    52428800"),
            ("", "  memory.events     oom_kill 1"),
            ("strong", "  job-a/  job-b/    child groups"),
        ], footer=["mkdir creates a group. rmdir removes an empty one."]),
        lines(32, 386, ["Writing a process number to cgroup.procs moves that process into",
                        "the group. Writing to a .max file sets a limit. The other files are",
                        "counters that the kernel keeps."]),
    ]
    save(OUT / "cgroup-files.svg", WIDTH, 440,
         "A control group is a directory under /sys/fs/cgroup. It contains cgroup.procs, which lists the "
         "processes in the group; pids.max, pids.current and pids.events; memory.max, memory.current and "
         "memory.events; and a subdirectory for each child group. mkdir creates a group and rmdir removes an "
         "empty one.",
         "The files of a control group", "The interface is a file system.", parts)


@figure
def cgroup_tree():
    parts = [
        card(110, 96, 260, 82, "store", "team", ["pids.max 4, pids.current 4", "memory.max 100, memory.current 60"]),
        wire([(240, 178), (240, 212), (128, 212), (128, 246)]),
        wire([(240, 178), (240, 212), (352, 212), (352, 246)]),
        card(32, 246, 192, 82, "client", "job-a", ["pids.current 3", "memory.current 60"]),
        card(256, 246, 192, 82, "service", "job-b", ["pids.current 1", "memory.current 0"]),
        lines(32, 362, ["job-b has no limit of its own. A fork in job-b is still refused,",
                        "because it would raise the count of team above 4.",
                        "",
                        "If job-b allocates 50, team holds 110 and exceeds its limit. The",
                        "kernel then ends the largest process below team, which is in job-a."]),
    ]
    save(OUT / "cgroup-tree.svg", WIDTH, 448,
         "The group team has pids.max 4 and memory.max 100. Its children job-a and job-b have no limits of "
         "their own. job-a holds 3 processes and 60 units of memory, job-b holds 1 process and no memory, and "
         "team counts both: 4 processes and 60 units.",
         "A group counts its whole subtree", "The limits of team apply to job-a and job-b together.", parts)



@figure
def cgroup_fork_check():
    parts, bottom = chain([
        ("client", "fork in a process of job-b", "the kernel is about to create a task", "terminal"),
        ("store", "job-b: 1 of max", "no limit: charge, count becomes 2", "stack"),
        ("danger", "team: 4 of 4", "at its limit: the charge is refused", "lock"),
        ("store", "Undo the charge in job-b", "the count returns to 1", "swap"),
        ("danger", "fork fails with EAGAIN", "pids.events of team: max + 1", "terminal"),
    ], x=60, w=360)
    parts.append(lines(32, bottom + 4, ["The check walks from the group of the process up to the root. A limit",
                                        "at any level stops the fork."]))
    save(OUT / "cgroup-fork-check.svg", WIDTH, bottom + 44,
         "The check the kernel makes on fork for a process in the group job-b. job-b has no limit, so it is "
         "charged and its count becomes 2. Its parent team is at 4 of 4, so the charge is refused. The kernel "
         "undoes the charge in job-b, fork fails with EAGAIN, and the max counter in pids.events of team is "
         "increased.",
         "A fork under a limit", "Every group above the process is asked.", parts)


@figure
def memory_charge():
    parts, bottom = chain([
        ("client", "A process touches a new page", "a page fault needs a frame", "terminal"),
        ("store", "Charge the frame", "to its group and every group above", "stack"),
        ("store", "A group would exceed memory.max", "the charge cannot be made yet", "lock"),
        ("service", "Reclaim inside that group", "drop clean cache, write dirty pages, swap", "swap"),
        ("good", "Enough was freed", "the charge succeeds, the fault returns", "pencil"),
    ], x=60, w=360)
    parts += [
        wire([(60, 80 + 76 * 4 - 51), (40, 80 + 76 * 4 - 51), (40, bottom + 39), (60, bottom + 39)], kind="danger"),
        card(60, bottom + 10, 360, 58, "danger", "Too little was freed", ["the OOM killer ends a process of the group"]),
        text(36, bottom - 40, "else", "note", "end"),
    ]
    save(OUT / "memory-charge.svg", WIDTH, bottom + 88,
         "What happens when a process in a limited group needs memory. The process touches a new page and the "
         "page fault needs a frame. The kernel charges the frame to the group and every group above. If a "
         "group would exceed memory.max, the kernel reclaims memory inside that group by dropping clean cache "
         "pages, writing dirty pages and swapping. If enough was freed, the charge succeeds and the fault "
         "returns. If too little was freed, the OOM killer ends a process of the group.",
         "A page under a memory limit", "Reclaim first. The OOM killer is the last resort.", parts)


@figure
def cgroup_structs():
    parts, y = [], 96
    blocks = [
        ("client", "struct task_struct", ["cgroups  a struct css_set"]),
        ("service", "struct css_set", ["subsys[]  for each controller, the state", "          of the group this task is in",
                                       "tasks     the tasks that share this set"]),
        ("store", "struct cgroup (a directory)", ["kn               its directory in cgroupfs", "level            depth in the tree",
                                                  "subtree_control  controllers for children", "subsys[]         its state per controller"]),
        ("outside", "per controller, per group", ["pids:    counter, limit, events", "memory:  struct page_counter:",
                                                  "         usage, max, parent"]),
    ]

    for k, (kind, title, rows) in enumerate(blocks):
        block, h = fields(40, y, 400, kind, title, rows)
        parts.append(block)

        if k:
            parts.append(wire([(240, y - 26), (240, y)]))

        y += h + 26

    save(OUT / "cgroup-structs.svg", WIDTH, y - 2,
         "The structures of control groups. struct task_struct has cgroups, a pointer to a struct css_set. The "
         "css_set has, for each controller, the state of the group the task is in, and the list of tasks that "
         "share the set. A struct cgroup is a directory, with its node in cgroupfs, its level, subtree_control "
         "and its state for each controller. For each controller and group there is a state: for pids a "
         "counter, a limit and events; for memory a struct page_counter with usage, max and parent.",
         "The structures of control groups", "A selection of fields from Linux 5.15.", parts)


# --------------------------------------------------------------- chapter 13

@figure
def container_parts():
    parts = [
        zone(32, 104, 416, 368, "control group: pids.max 5"),
        zone(52, 140, 376, 316, "namespaces: user, mnt, uts, pid, ipc, net"),
        card(90, 170, 300, 64, "good", "sh", ["process 1, user 0, host name box"], glyph="terminal"),
        wire([(240, 234), (240, 268)]),
        zone(72, 268, 336, 172, "root file system"),
        card(88, 290, 148, 56, "store", "/", ["a new tmpfs"]),
        card(244, 290, 148, 56, "idle", "/usr", ["from the host"]),
        card(88, 356, 148, 56, "outside", "/proc", ["a new proc"]),
        card(244, 356, 148, 56, "idle", "/dev/null", ["from the host"]),
        lines(32, 500, ["The namespaces decide what the process can see. The root file system",
                        "decides which files exist for it. The control group decides how much",
                        "it can use."]),
    ]
    save(OUT / "container-parts.svg", WIDTH, 554,
         "A container is a process, here sh running as process 1 and user 0 with the host name box, inside new "
         "user, mount, UTS, PID, IPC and network namespaces, with a root file system made of a new tmpfs, /usr and "
         "/dev/null bound from the host and a new /proc, and inside a control group with pids.max 5.",
         "The parts of a container", "An ordinary process with a restricted view and a limit.", parts)


@figure
def box_steps():
    steps = [("client", "box", "creates a group, sets pids.max"),
             ("client", "box", "clones a child into new namespaces"),
             ("outside", "child, process 1", "mounts a tmpfs, binds /usr"),
             ("outside", "child, process 1", "mounts a new /proc"),
             ("outside", "child, process 1", "pivot_root, detaches the old root"),
             ("outside", "child, process 1", "sets the host name"),
             ("good", "child, process 1", "exec: becomes the shell")]
    parts = []

    for k, (kind, who, what) in enumerate(steps):
        y = 96 + 68 * k
        parts.append(card(70, y, 360, 52, kind, what, [who]))
        parts.append(text(48, y + 31, str(k + 1), "name", "middle"))

        if k:
            parts.append(wire([(240, y - 16), (240, y)]))

    save(OUT / "box-steps.svg", WIDTH, 96 + 68 * len(steps) + 16,
         "The steps of box. 1: box creates a control group and sets pids.max. 2: box creates a child with the "
         "namespace flags. 3: the child, process 1 of the new PID namespace, mounts a tmpfs and binds /usr and "
         "/dev/null. 4: it mounts a new /proc. 5: it calls pivot_root and detaches the old root. 6: it sets "
         "the host name. 7: it calls exec and becomes the shell.",
         "Starting a container", "Each step is a system call from an earlier chapter.", parts)



@figure
def pivot_root_steps():
    def tree(x, y, title, rows, kind):
        block, h = fields(x, y, 200, kind, title, rows)

        return block, h

    a, h = tree(32, 104, "1. before", ["/          the host", "  usr  home  etc", "  tmp/box-root  tmpfs", "    usr  dev  proc"], "idle")
    b, _ = tree(248, 104, "2. after pivot_root", ["/          the tmpfs", "  usr  dev  proc", "  old      the host", "    usr  home  etc"], "store")
    c, h2 = tree(140, 104 + h + 44, "3. after unmounting /old", ["/          the tmpfs", "  usr  dev  proc", "", "the host is unreachable"], "good")
    parts = [a, b, c, wire([(232, 104 + h / 2), (248, 104 + h / 2)]),
             wire([(348, 104 + h), (348, 104 + h + 22), (240, 104 + h + 22), (240, 104 + h + 44)]),
             lines(32, 104 + h + 44 + h2 + 28, ["pivot_root exchanges the 2 mounts: the tmpfs becomes the root, and",
                                                "the old root is attached inside it. All of this happens in the",
                                                "container's mount namespace, and the host's mounts do not change."])]
    save(OUT / "pivot-root-steps.svg", WIDTH, 104 + h + 44 + h2 + 80,
         "The root directory of the container in 3 steps. Before, the root is the host's file system, and the "
         "tmpfs with usr, dev and proc is mounted at tmp/box-root. After pivot_root, the tmpfs is the root, and "
         "the host's file system is attached at old inside it. After unmounting old, only the tmpfs remains "
         "and the host is unreachable.",
         "Changing the root directory", "pivot_root, then unmount the old root.", parts)


@figure
def image_layers():
    rows = [("good", "merged view: the root of the container", "what the processes see"),
            ("client", "upper layer: writable, 1 per container", "files the container creates or changes"),
            ("store", "image layer 3: the application", "read-only, shared by all containers"),
            ("store", "image layer 2: libraries", "read-only"),
            ("store", "image layer 1: a base system", "read-only")]
    parts = []

    for k, (kind, name, sub) in enumerate(rows):
        y = 96 + 68 * k + (16 if k else 0)
        parts.append(card(48, y, 384, 56, kind, name, [sub]))

    parts += [wire([(240, 180), (240, 152)]),
              lines(32, 96 + 68 * len(rows) + 30, ["An overlay file system shows several directories as 1. A file is",
                                                  "looked up from the top layer downward, and a write copies the file",
                                                  "into the upper layer first."])]
    save(OUT / "image-layers.svg", WIDTH, 96 + 68 * len(rows) + 84,
         "The root file system of a container built from an image. The processes see a merged view. Below it "
         "are an upper layer, writable and private to the container, which holds the files the container "
         "creates or changes, and the read-only layers of the image: the application, libraries and a base "
         "system, shared by all containers of the image.",
         "The root of a real container", "An image is a stack of read-only layers.", parts)


@figure
def runtime_stack():
    parts, bottom = chain([
        ("client", "docker run, or kubectl", "the command a person types", "terminal"),
        ("service", "Container engine", "dockerd, containerd: images, networks", "gear"),
        ("store", "OCI runtime: runc", "reads config.json: namespaces, mounts, limits", "doc"),
        ("store", "clone, mount, pivot_root, cgroupfs", "the calls of this chapter", "stack"),
        ("good", "exec", "the program of the image, as process 1", "swap"),
    ], x=50, w=380)
    save(OUT / "runtime-stack.svg", WIDTH, bottom,
         "The layers of container software. A person types docker run or uses kubectl. A container engine, "
         "dockerd or containerd, manages images and networks. An OCI runtime, runc, reads config.json, which "
         "lists the namespaces, mounts and limits. It makes the calls of this chapter: clone, mount, "
         "pivot_root and writes to cgroupfs. Then it calls exec, and the program of the image runs as "
         "process 1.",
         "From docker run to the kernel", "box does the work of the lowest 2 layers.", parts)



# ------------------------------------------------------- intuition, chapters 1 to 7

@figure
def pipe_why():
    parts = [
        zone(32, 104, 416, 150, "without a pipe: a temporary file"),
        card(44, 130, 110, 56, "client", "seq", ["writes all"]), cylinder(170, 126, 140, 66, "store", "file", ["588895 bytes"]),
        card(326, 130, 110, 56, "client", "wc", ["reads all"]),
        wire([(154, 158), (170, 158)]), wire([(310, 158), (326, 158)]),
        text(240, 228, "seq must finish before wc starts. The disk holds everything.", "sub", "middle"),
        zone(32, 294, 416, 150, "with a pipe"),
        card(44, 320, 110, 56, "client", "seq", ["writes"]), box(170, 330, 140, 36, KINDS["model"][1], KINDS["model"][0], 18),
        text(240, 353, "at most 65536 bytes", "pill", "middle", KINDS["model"][0]),
        card(326, 320, 110, 56, "client", "wc", ["reads"]),
        wire([(154, 348), (170, 348)]), wire([(310, 348), (326, 348)]),
        text(240, 418, "Both run at the same time. Memory stays small and fixed.", "sub", "middle"),
    ]
    save(OUT / "pipe-why.svg", WIDTH, 468,
         "2 ways to pass the output of seq to wc. Without a pipe, seq writes all 588895 bytes to a temporary file and wc "
         "reads it afterwards: seq must finish before wc starts, and the disk holds everything. With a pipe, seq writes and "
         "wc reads at the same time through a buffer of at most 65536 bytes, and memory stays small and fixed.",
         "What a pipe saves", "The same job with a temporary file and with a pipe.", parts)


@figure
def proc_fd_annotated():
    annotated("proc-fd-annotated", "Reading /proc/<pid>/fd", "Each line is a descriptor and the object behind it.", [
        ("/proc/4121903/fd/1 -> pipe:[33835818]", ["process 4121903, descriptor 1 (standard output):", "the write end of pipe number 33835818"], "client"),
        ("/proc/4121904/fd/0 -> pipe:[33835818]", ["process 4121904, descriptor 0 (standard input):", "the read end of the same pipe: the numbers match"], "service"),
    ], "The 2 lines of the listing explained. The first line is process 4121903, descriptor 1, standard output, which is the "
       "write end of pipe number 33835818. The second line is process 4121904, descriptor 0, standard input, which is the read "
       "end of the same pipe, because the pipe numbers match.")


@figure
def stat_annotated():
    annotated("stat-annotated", "Reading stat and ls -li", "Every value shown comes from a field of the inode.", [
        ("19927765 -rw-rw-r-- 2 jetson jetson 6 copy.txt", ["19927765 is i_ino, the inode number", "the 2 after the permissions is i_nlink: 2 names", "6 is i_size, in bytes"], "store"),
        ("19927765 -rw-rw-r-- 2 jetson jetson 6 report.txt", ["the same inode number: the same file", "only the name, which is in the directory, differs"], "store"),
        ("Size: 6   Blocks: 8   Inode: 19927765   Links: 2", ["stat prints the same fields with their names", "Blocks counts 512-byte units: 8 is 1 page of 4096 bytes"], "service"),
    ], "The output of ls -li and stat explained. In each line of ls, 19927765 is the inode number, the 2 after the "
       "permissions is the link count, and 6 is the size. Both lines have the same inode number, so they are the same file, "
       "and only the name differs. stat prints the same fields with their names, and Blocks counts units of 512 bytes.")


@figure
def fork_copies():
    def column(x, title, kind):
        return [card(x, 104, 196, 44, kind, title, [])]

    rows = [("pid", "500", "501", "new"), ("memory", "pages", "same pages", "shared until a write"), ("descriptors", "table", "copy of table", "same open files"),
            ("signal handlers", "table", "copy", "independent"), ("working directory", "/home", "/home", "copied")]
    parts = column(32, "parent", "client") + column(252, "child", "outside")

    for k, (what, left, right, note) in enumerate(rows):
        y = 164 + 58 * k
        parts += [box(32, y, 196, 44, CARD, EDGE, 8), box(252, y, 196, 44, CARD, EDGE, 8),
                  text(44, y + 18, what, "tab"), text(44, y + 35, left, "mono strong"),
                  text(264, y + 18, note, "tab"), text(264, y + 35, right, "mono strong"),
                  wire([(228, y + 22), (252, y + 22)])]

    save(OUT / "fork-copies.svg", WIDTH, 164 + 58 * len(rows) + 10,
         "What fork gives the child, resource by resource. The pid is new: 500 in the parent, 501 in the child. The memory "
         "is the same pages, shared until one side writes. The descriptor table is a copy that refers to the same open "
         "files. The signal handlers are a copy and independent afterwards. The working directory is copied.",
         "What a child receives from fork", "Each resource is copied, shared, or new.", parts)


@figure
def status_annotated():
    annotated("status-annotated", "Reading /proc/<pid>/status", "The kernel's record of a process, as text.", [
        ("Name:   sleep", ["the program name: task_struct.comm"], "client"),
        ("State:  S (sleeping)", ["waiting for an event, here a timer", "R would mean running or ready to run"], "good"),
        ("Tgid:   565534      Pid:    565534", ["process number and thread number", "equal: this process has a single thread"], "client"),
        ("PPid:   565533", ["the parent: the shell that started it"], "service"),
        ("Threads:        1", ["how many tasks share this address space"], "client"),
    ], "The lines of /proc/pid/status explained. Name is the program name. State S means sleeping, waiting for an event. "
       "Tgid and Pid are the process number and the thread number, equal for a process with a single thread. PPid is the "
       "parent. Threads is the number of tasks that share the address space.")


@figure
def shell_fd_states():
    def table(x, y, title, rows, kind):
        block, h = fields(x, y, 200, kind, title, rows)

        return block

    parts = [
        table(32, 104, "shell, after pipe2", ["0  terminal", "1  terminal", "3  pipe, read end", "4  pipe, write end"], "client"),
        table(248, 104, "seq, before execve", ["0  terminal", "1  pipe, write end", "3  (closed)", "4  (closed)"], "good"),
        table(32, 260, "wc, before execve", ["0  pipe, read end", "1  count.txt", "3  (closed)", "4  (closed)"], "good"),
        table(248, 260, "shell, while waiting", ["0  terminal", "1  terminal", "3  (closed)", "4  (closed)"], "client"),
        lines(32, 420, ["Each child moves the pipe end it needs onto descriptor 0 or 1",
                        "and closes the rest. The shell closes both ends. The programs",
                        "find everything on the standard descriptors."]),
    ]
    save(OUT / "shell-fd-states.svg", WIDTH, 474,
         "The descriptor tables at 4 moments of the trace. After pipe2 the shell has the terminal on 0 and 1, the read end "
         "of the pipe on 3 and the write end on 4. Before execve, seq has the write end on descriptor 1 and has closed 3 and "
         "4. Before execve, wc has the read end on descriptor 0 and count.txt on descriptor 1. While waiting, the shell has "
         "closed 3 and 4 and still has the terminal on 0 and 1.",
         "The descriptor tables during the trace", "What each process holds at 4 moments.", parts)


@figure
def mask_decode():
    bits_on = {9: "SIGUSR1 (10)", 16: "SIGCHLD (17)"}
    parts = [text(240, 108, "SigCgt:  0000000000010200", "mono strong", "middle"),
             text(240, 132, "in binary, bit 0 on the right", "sub", "middle")]

    for k in range(20):
        bit = 19 - k
        x = 36 + 20.6 * k
        on = bit in bits_on
        accent, tint = KINDS["good" if on else "idle"]
        parts += [box(x, 146, 18, 28, tint if on else CARD, accent if on else EDGE, 4),
                  text(x + 9, 165, "1" if on else "0", "mono strong" if on else "mono dim", "middle"),
                  text(x + 9, 190, str(bit), "note", "middle")]

    parts += [wire([(251, 196), (251, 232)]), card(150, 232, 230, 52, "good", "bit 9 is set", ["signal 9 + 1 = 10: SIGUSR1"]),
              wire([(107, 196), (107, 304), (150, 304)]), card(150, 290, 230, 52, "good", "bit 16 is set", ["signal 16 + 1 = 17: SIGCHLD"]),
              lines(32, 372, ["A mask is a number read bit by bit. Bit n stands for signal n + 1,",
                              "because signals are numbered from 1 and bits from 0."])]
    save(OUT / "mask-decode.svg", WIDTH, 412,
         "The mask 0x10200 written in binary, with bit 0 on the right. Bits 9 and 16 are 1 and all others are 0. Bit 9 "
         "stands for signal 10, SIGUSR1, and bit 16 for signal 17, SIGCHLD. Bit n stands for signal n plus 1.",
         "Decoding a signal mask", "0x10200 has 2 bits set, so 2 signals have a handler.", parts)


@figure
def slice_division():
    accent = [KINDS["client"], KINDS["service"], KINDS["store"]]
    tasks = [("A", 1024, 10.3), ("B", 1024, 10.3), ("C", 335, 3.4)]
    parts, x = [text(32, 108, "1 scheduling period of 24 ms", "tab")], 32.0

    for k, (name, weight, ms) in enumerate(tasks):
        w = 416 * ms / 24.0
        parts += [box(x, 120, w, 50, accent[k][1], accent[k][0], 6), text(x + w / 2, 142, name, "name", "middle"),
                  text(x + w / 2, 160, "%.1f ms" % ms, "mono", "middle")]
        x += w

    parts += [lines(32, 204, ["The weights 1024, 1024 and 335 add up to 2383. A gets",
                             "1024 / 2383 = 43% of the period, B the same, C 335 / 2383 = 14%."]),
              card(32, 252, 416, 74, "good", "Then the period repeats", ["Over a second, A and B each run for about 430 ms", "and C for about 140 ms."])]
    save(OUT / "slice-division.svg", WIDTH, 346,
         "A scheduling period of 24 ms divided between 3 tasks by weight. A and B, each with weight 1024, get 10.3 ms. C, "
         "with weight 335, gets 3.4 ms. The weights add up to 2383, so A and B each get 43 percent and C gets 14 percent. "
         "The period then repeats.",
         "Dividing a period by weight", "A share of the period for each task, by weight.", parts)


@figure
def same_address():
    frame, ftint = KINDS["store"]
    parts = [
        card(32, 104, 196, 64, "client", "process A", ["reads address 0x1000"]),
        card(252, 104, 196, 64, "outside", "process B", ["reads address 0x1000"]),
        card(32, 198, 196, 56, "client", "A's page table", ["page 1 -> frame 5"]), card(252, 198, 196, 56, "outside", "B's page table", ["page 1 -> frame 7"]),
        wire([(130, 168), (130, 198)]), wire([(350, 168), (350, 198)]),
        zone(32, 300, 416, 100, "physical memory: frames"),
    ]

    for k in range(8):
        hot = k in (5, 7)
        parts += [box(48 + 49 * k, 326, 41, 40, ftint if hot else CARD, frame if hot else EDGE, 6),
                  text(68.5 + 49 * k, 351, str(k), "mono strong" if hot else "mono dim", "middle")]

    parts += [wire([(130, 254), (130, 290), (313, 290), (313, 326)]), wire([(350, 254), (350, 280), (411, 280), (411, 326)]),
              lines(32, 428, ["The same address leads to different memory in each process, because",
                              "each process has its own table. Neither can name the other's frame."])]
    save(OUT / "same-address.svg", WIDTH, 468,
         "Process A and process B both read address 0x1000. A's page table maps page 1 to frame 5, and B's page table maps "
         "page 1 to frame 7. The same address leads to different frames of physical memory, because each process has its own "
         "page table.",
         "The same address in 2 processes", "A virtual address has a meaning only inside its own process.", parts)


@figure
def address_worked():
    parts = [
        text(240, 108, "a small machine: 16-bit addresses, pages of 256 bytes", "sub", "middle"),
        box(140, 122, 96, 46, KINDS["client"][1], KINDS["client"][0], 6), box(244, 122, 96, 46, KINDS["store"][1], KINDS["store"][0], 6),
        text(188, 142, "page", "pill", "middle", KINDS["client"][0]), text(188, 160, "0x12", "mono strong", "middle"),
        text(292, 142, "offset", "pill", "middle", KINDS["store"][0]), text(292, 160, "0x34", "mono strong", "middle"),
        text(120, 150, "0x1234 =", "mono strong", "end"),
        wire([(188, 168), (188, 206)]),
        card(80, 206, 216, 56, "service", "page table entry 0x12", ["holds frame 0x7A"]),
        wire([(188, 262), (188, 300)]), wire([(292, 168), (292, 300)]),
        box(140, 300, 96, 46, KINDS["service"][1], KINDS["service"][0], 6), box(244, 300, 96, 46, KINDS["store"][1], KINDS["store"][0], 6),
        text(188, 320, "frame", "pill", "middle", KINDS["service"][0]), text(188, 338, "0x7A", "mono strong", "middle"),
        text(292, 320, "offset", "pill", "middle", KINDS["store"][0]), text(292, 338, "0x34", "mono strong", "middle"),
        text(352, 328, "= 0x7A34", "mono strong"),
        lines(32, 380, ["The page number is looked up and replaced by a frame number. The",
                        "offset is copied unchanged. A page and a frame have the same size, so",
                        "byte 0x34 of the page is byte 0x34 of the frame."]),
    ]
    save(OUT / "address-worked.svg", WIDTH, 434,
         "The translation of address 0x1234 on a small machine with 16-bit addresses and pages of 256 bytes. The address "
         "splits into page 0x12 and offset 0x34. Entry 0x12 of the page table holds frame 0x7A. The physical address is frame "
         "0x7A followed by the unchanged offset 0x34: 0x7A34.",
         "Translating 1 address by hand", "Split the address, look up the page, keep the offset.", parts)


@figure
def maps_annotated():
    annotated("maps-annotated", "Reading /proc/<pid>/maps", "Each line is a range of addresses and what it holds.", [
        ("aaaab7c80000-aaaab7c86000 r-xp   /usr/bin/cat", ["end - start = 0x6000 bytes = 6 pages", "r-x: readable and executable: the program's code"], "client"),
        ("aaaacae31000-aaaacae52000 rw-p   [heap]", ["0x21000 bytes = 33 pages", "rw-: readable and writable: memory from malloc"], "store"),
        ("ffffaa650000-ffffaa7d8000 r-xp   libc.so.6", ["0x188000 bytes = 392 pages of library code", "the same frames serve every program that uses libc"], "outside"),
        ("fffff2ebe000-fffff2ee0000 rw-p   [stack]", ["0x22000 bytes = 34 pages", "local variables and return addresses"], "idle"),
    ], "4 lines of /proc/pid/maps explained. The line for /usr/bin/cat covers 0x6000 bytes, 6 pages, readable and "
       "executable: the program's code. The heap line covers 0x21000 bytes, 33 pages, readable and writable: memory from "
       "malloc. The libc line covers 0x188000 bytes, 392 pages of library code shared by every program that uses libc. The "
       "stack line covers 0x22000 bytes, 34 pages, for local variables and return addresses.")


@figure
def vsz_rss():
    parts = [
        meter(32, 130, 416, "VSZ: addresses mapped", 11204, 11204, "kB", "idle"),
        meter(32, 200, 416, "RSS: pages that have a frame", 776, 11204, "kB", "good"),
        lines(32, 258, ["Of the 11204 kB the process may use, 776 kB has been touched",
                        "and given memory: 7%. The rest costs nothing until it is used."]),
    ]
    save(OUT / "vsz-rss.svg", WIDTH, 304,
         "2 gauges for a sleep process. VSZ, the addresses mapped, is 11204 kB. RSS, the pages that have a frame, is 776 kB, "
         "7 percent of the mapped size.",
         "Mapped and resident", "A process is charged for the pages it touches.", parts)



# ------------------------------------------------------ intuition, chapters 8 to 13

def two_views(name, title, lede, left, right, rows, alt, note):
    """2 columns that describe the same thing from 2 sides, row by row."""
    parts = [card(32, 104, 200, 44, "client", left, []), card(248, 104, 200, 44, "outside", right, [])]

    for k, (what, a, b) in enumerate(rows):
        y = 162 + 58 * k
        parts += [box(32, y, 200, 46, CARD, EDGE, 8), box(248, y, 200, 46, CARD, EDGE, 8),
                  text(44, y + 18, what, "tab"), text(44, y + 36, a, "mono strong"),
                  text(260, y + 18, what, "tab"), text(260, y + 36, b, "mono strong")]

    y = 162 + 58 * len(rows) + 18
    parts.append(lines(32, y, note))
    save(OUT / (name + ".svg"), WIDTH, y + 17 * len(note) + 10, alt, title, lede, parts)


@figure
def memory_bar():
    from figkit import stacked, swatches
    used, cache, free = 8881, 6473, 300
    parts = [text(32, 108, "15655 MB of memory", "tab"),
             stacked(32, 120, 416, 46, [(used, "#5b6b7c", "programs 8881"), (cache, "#5e9400", "page cache 6473"), (free, "#d5dbe3", "")]),
             swatches(32, 200, [("#5b6b7c", "used by programs"), ("#5e9400", "page cache"), ("#d5dbe3", "free: 300")]),
             card(32, 226, 416, 82, "good", "available: 6197 MB", ["The kernel can drop clean cache pages at any moment,", "so most of the cache counts as memory a program can get."])]
    save(OUT / "memory-bar.svg", WIDTH, 328,
         "The 15655 MB of memory on the machine as a bar: 8881 MB used by programs, 6473 MB of page cache, and 300 MB free. "
         "The available figure is 6197 MB, because the kernel can drop clean cache pages at any moment.",
         "Where the memory of a machine goes", "Free memory is small because idle memory is used as cache.", parts)


@figure
def epoll_fdinfo_annotated():
    annotated("epoll-fdinfo-annotated", "Reading the fdinfo of an epoll fd", "Each tfd line is a registration.", [
        ("tfd:       29 events:       19 data: aaaaf18e8be0", ["tfd 29: descriptor 29 is registered", "events 19 is hexadecimal: 0x01 + 0x08 + 0x10",
                                                              "EPOLLIN + EPOLLERR + EPOLLHUP: tell me when it is readable"], "good"),
        ("tfd:       35 events:       19 data: aaaaf1953a90", ["data is the value the program stored at registration,", "here the address of its own record for descriptor 35"], "service"),
    ], "2 lines of the fdinfo of an epoll descriptor explained. tfd 29 means descriptor 29 is registered. events 19 is "
       "hexadecimal for EPOLLIN, EPOLLERR and EPOLLHUP together. data is the value the program stored at registration, "
       "here the address of its own record for the descriptor.")


@figure
def scan_vs_ready():
    idle, hot = KINDS["idle"], KINDS["good"]
    parts = [zone(32, 104, 416, 150, "select and poll: examine all 40")]

    for k in range(40):
        on = k == 27
        parts.append(box(48 + 39.2 * (k % 10), 130 + 26 * (k // 10), 30, 18, hot[1] if on else idle[1], hot[0] if on else idle[0], 4))

    parts += [text(240, 244, "40 checks to find 1 ready descriptor, on every call", "sub", "middle"),
              zone(32, 294, 416, 104, "epoll: read the ready list"),
              box(48, 322, 30, 18, hot[1], hot[0], 4), text(92, 336, "the 1 ready descriptor, put there when its data arrived", "sub"),
              text(240, 384, "1 check, whether 40 or 40000 are registered", "sub", "middle")]
    save(OUT / "scan-vs-ready.svg", WIDTH, 422,
         "With 40 descriptors of which 1 is ready, select and poll examine all 40 on every call to find it. epoll reads a "
         "ready list that already holds the 1 ready descriptor, put there when its data arrived: 1 check, however many are "
         "registered.",
         "Scanning against a ready list", "The work of 1 call when 1 descriptor of 40 is ready.", parts)


@figure
def ss_annotated():
    annotated("ss-annotated", "Reading ss", "Each line is a socket: state, queues, and 4 values.", [
        ("LISTEN 0  1   127.0.0.1:9099   0.0.0.0:*", ["a listener on port 9099, no peer yet", "0 connections wait for accept; the backlog is 1"], "store"),
        ("ESTAB  0  0   127.0.0.1:9099   127.0.0.1:51252", ["the server's end of 1 connection", "0 bytes received and unread, 0 bytes unsent"], "service"),
        ("ESTAB  0  0   127.0.0.1:51252  127.0.0.1:9099", ["the client's end of the same connection:", "the same 4 values, local and peer exchanged"], "client"),
    ], "3 lines of ss explained. The LISTEN line is a listener on port 9099 with no peer yet, 0 connections waiting for "
       "accept and a backlog of 1. The first ESTAB line is the server's end of a connection, with 0 bytes received and unread "
       "and 0 bytes unsent. The second ESTAB line is the client's end of the same connection, with the same 4 values, local "
       "and peer exchanged.")


@figure
def seq_worked():
    sent, tint = KINDS["good"]
    parts = [text(32, 108, "the client's stream, byte by byte", "tab")]

    for k, ch in enumerate("hello"):
        x = 60 + 72 * k
        parts += [box(x, 122, 64, 50, tint, sent, 6), text(x + 32, 144, ch, "name", "middle"), text(x + 32, 162, str(1001 + k), "mono", "middle")]

    parts += [wire([(240, 172), (240, 214)], label="1 segment: 5 bytes, seq 1001"),
              card(60, 214, 360, 64, "service", "The server has bytes 1001 to 1005", ["next expected: 1006"]),
              wire([(240, 278), (240, 320)], label="ACK, ack 1006"),
              card(60, 320, 360, 64, "client", "The client reads the acknowledgement", ["everything before 1006 arrived: discard the copy"]),
              lines(32, 412, ["If the segment is lost, no acknowledgement of 1006 arrives. After",
                              "a timeout the client sends bytes 1001 to 1005 again from its copy."])]
    save(OUT / "seq-worked.svg", WIDTH, 452,
         "The 5 bytes of hello numbered 1001 to 1005 in the client's stream. They travel in 1 segment with sequence number "
         "1001. The server now has bytes 1001 to 1005 and expects 1006 next, and it sends an acknowledgement with ack 1006. The "
         "client reads it as: everything before 1006 arrived, and discards its copy. If the segment is lost, no such "
         "acknowledgement arrives, and the client sends the bytes again after a timeout.",
         "Sequence numbers and acknowledgements", "How 5 bytes are sent, confirmed, and sent again if lost.", parts)


@figure
def ns_views():
    two_views("ns-views", "The same process, seen from 2 sides", "nsfacts measured both columns.", "outside, on the host", "inside",
              [("its pid", "565534", "1"), ("its user", "1000 (jetson)", "0 (root)"), ("the host name", "yahboom", "box"),
               ("may set the host name", "no: EPERM", "yes")],
              "A process in new namespaces seen from outside and from inside. Its process number is 565534 on the host and 1 "
              "inside. Its user is 1000 on the host and 0 inside. The host name is yahboom outside and box inside. It may set "
              "the host name inside and gets EPERM outside.",
              ["A namespace changes what the process is told. The process, its", "memory and its files are the same from both sides."])


@figure
def cgroup_path_tree():
    levels = [("user.slice", "all users"), ("user-1000.slice", "user 1000: memory and pids counted here"),
              ("user@1000.service", "the user's session manager"), ("app.slice", "applications"),
              ("...Terminal.slice", "the terminal program"), ("vte-spawn-....scope", "1 terminal window: this shell")]
    parts = []

    for k, (name, what) in enumerate(levels):
        x, y = 32 + 16 * k, 104 + 60 * k
        parts.append(card(x, y, 448 - x, 48, "store" if k == 1 else ("good" if k == 5 else "idle"), name, [what]))

        if k:
            parts.append(wire([(x - 8, y - 12), (x - 8, y + 24), (x, y + 24)]))

    parts.append(lines(32, 104 + 60 * len(levels) + 12, ["The path in /proc/self/cgroup is this chain of directories, written",
                                                         "with slashes. A process is counted in its own group and in every",
                                                         "group above it."]))
    save(OUT / "cgroup-path-tree.svg", WIDTH, 104 + 60 * len(levels) + 66,
         "The cgroup path of a shell drawn as nested groups: user.slice for all users, user-1000.slice for user 1000 where "
         "memory and pids are counted, user@1000.service for the session manager, app.slice for applications, a slice for the "
         "terminal program, and a scope for 1 terminal window that contains the shell.",
         "A cgroup path is a chain of groups", "Each directory in the path is a group inside the last.", parts)


@figure
def cgroup_gauges():
    parts = [
        meter(32, 130, 416, "pids.current of user-1000.slice", 1347, 40594, "tasks", "good"),
        meter(32, 200, 416, "of its memory: anonymous", 5923, 12315, "MB", "client"),
        meter(32, 270, 416, "of its memory: page cache", 5731, 12315, "MB", "model"),
        lines(32, 328, ["1347 of the 40594 tasks allowed are in use. memory.max is max,",
                        "so the 12315 MB in use has no limit. About half of it is page",
                        "cache, which the kernel can reclaim under a limit."]),
    ]
    save(OUT / "cgroup-gauges.svg", WIDTH, 390,
         "3 gauges for the group of user 1000. pids.current is 1347 of 40594 tasks allowed. Of the 12315 MB of memory in use, "
         "5923 MB is anonymous memory of programs and 5731 MB is page cache.",
         "Reading the counters of a group", "The usage of every process of user 1000 together.", parts)


@figure
def container_views():
    two_views("container-views", "The host's view and the container's", "The output of box, set beside the host's view.", "on the host", "inside the container",
              [("the shell's pid", "an ordinary pid", "1"), ("processes visible", "every process", "only its own"),
               ("the root directory", "the host's disks", "6 dirs on a tmpfs"), ("network interfaces", "all of the host's", "lo"),
               ("the user", "1000", "0"), ("the host name", "yahboom", "box")],
              "The container that box builds, seen from the host and from inside. The shell has an ordinary pid on the host and "
              "pid 1 inside. The host sees every process and the container only its own. The root directory is the host's "
              "disks outside and 6 directories inside. The network interfaces are all of the host's outside and only lo inside. "
              "The user is 1000 outside and 0 inside. The host name is yahboom outside and box inside.",
              ["Nothing is copied or emulated. The same kernel answers both", "sides, and gives the process in the container a narrower answer."])


for name in sys.argv[1:] or list(FIGURES):
    FIGURES[name]()
    print("  " + name)

print("wrote %d figure(s) to %s" % (len(sys.argv[1:]) or len(FIGURES), OUT))
