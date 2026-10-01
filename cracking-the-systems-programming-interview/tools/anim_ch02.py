"""The files chapter animation (ch02-files.md), drawn with `motion`.

    python3 tools/animations.py bufreader
"""

from motion_kit import Panel, layout
from motion import *  # noqa: F401,F403
from motion import Timeline, render

CODE = Panel("src/bin/readfile_line_by_line.rs",
             [("let reader = BufReader::new(file);", ("println!", 1))],
             ["let reader = BufReader::new(file);",
              "for (i, line) in reader.lines().enumerate() {", "let line = line?;",
              "println!(\"{}: {}\", i + 1, line);"])
FILE = "a=1\nb=2\nc=3\n"
LINES = ["a=1", "b=2", "c=3"]
BOUNDARY = 300
PROG_X, KERNEL_X = 140, 640


def bufreader():
    tl = Timeline(caption="", kind="step", code=-1.0, mode="buffered", calls=0.0, buffered=0,
                  printed=0, fly_u=0.0, fly_a=0.0, fly_label="", back_u=0.0, back_a=0.0,
                  back_label="", eof=0.0)

    def syscall(ask, got, k=1.0):
        tl.set(fly_label=ask, fly_u=0.0)
        tl.to(0.1, fly_a=1.0)
        tl.to(0.6 * k, in_out, fly_u=1.0)
        tl.to(0.1, fly_a=0.0)
        tl.set(back_label=got, back_u=0.0)
        tl.to(0.1, back_a=1.0)
        tl.to(0.6 * k, in_out, back_u=1.0)
        tl.to(0.1, back_a=0.0)
        tl.set(calls=tl._at("calls", tl.now) + 1)

    tl.chapter("BufReader")
    tl.say("The file holds 12 bytes: three lines of four bytes, each ending in a newline.")
    tl.set(code=0.0)
    tl.wait(0.6)
    tl.say("lines() asks for the first line. The buffer is empty, so BufReader makes one read "
           "system call for up to 8 KiB.")
    tl.set(code=1.0)
    syscall("read(fd, 8 KiB)", "12 bytes", 1.3)
    tl.set(buffered=12)
    tl.wait(0.4)
    tl.say("All 12 bytes arrive at once. BufReader cuts the first line out of its buffer.")
    for n in range(3):
        tl.set(code=2.0)
        tl.wait(0.4 if n else 0.8)
        tl.set(code=3.0, printed=n + 1, buffered=12 - 4 * (n + 1))
        tl.wait(0.4 if n else 0.8)
        if n == 0:
            tl.say("Lines 2 and 3 come from the same buffer. No more system calls.")
    tl.say("The buffer is empty again. One more read returns 0 bytes: end of file, and the loop "
           "ends.")
    tl.set(code=1.0)
    syscall("read(fd, 8 KiB)", "0 bytes", 0.8)
    tl.to(0.3, eof=1.0)
    tl.say("Two system calls for the whole file.", "insight")
    tl.wait(1.2)

    tl.chapter("no buffer")
    tl.say("Without a buffer, a line reader cannot know where a line ends, so it reads one byte "
           "per call.", "fail")
    tl.set(mode="bytes", calls=0.0, buffered=0, printed=0, eof=0.0, code=-1.0)
    tl.wait(0.6)
    for b in range(12):
        syscall("read(fd, 1 byte)", repr(FILE[b])[1:-1] or "\\n", 0.35 if b else 0.8)
        if b % 4 == 3:
            tl.set(printed=b // 4 + 1)
    syscall("read(fd, 1 byte)", "0 bytes", 0.35)
    tl.to(0.3, eof=1.0)
    tl.say("13 system calls for the same 12 bytes. Each one crosses into the kernel and back.",
           "fail")
    tl.wait(1.6)

    def draw(p, s, total):
        t = s.t
        title_block(p, "Reading lines with a buffer",
                    "Each read system call crosses into the kernel. BufReader makes few, large ones.")
        scoreboard(p, [("read calls", int(round(s.calls)),
                        TEAL if s.mode == "buffered" else RUST)])
        p.line(BOUNDARY + 100, 80, BOUNDARY + 100, 280, FAINT, 1.4, dash="6 5")
        p.text(BOUNDARY + 90, 94, "your program", 11, MUTED, 600, "end")
        p.text(BOUNDARY + 110, 94, "kernel", 11, MUTED, 600)
        robot(p, PROG_X, 210, TEAL, 1.0, 1.0, "main", "for line in reader.lines()")
        # the buffer
        if s.mode == "buffered":
            p.text(250, 128, "BufReader buffer, 8 KiB", 10.5, MUTED, 600)
            p.rect(250, 136, 120, 30, PAPER, TEAL, 5, 1.3)
            n = int(s.buffered)
            if n:
                p.rect(252, 138, 116 * n / 12, 26, TEAL_LT, "none", 4)
                p.text(310, 156, "%d bytes" % n, 10.5, INK, 700, "middle", mono=True)
        # the file in the page cache
        p.text(KERNEL_X - 70, 128, "log.txt in the page cache", 10.5, MUTED, 600)
        for k, line in enumerate(LINES):
            p.rect(KERNEL_X - 70, 136 + k * 28, 140, 24, STAGE, LINE, 4, 1.0)
            p.text(KERNEL_X, 153 + k * 28, line + "\\n", 11, INK, 700, "middle", mono=True)
        # output
        p.text(26, 300, "printed:", 11, MUTED, 600)
        for k in range(int(s.printed)):
            p.text(92 + k * 92, 300, "%d: %s" % (k + 1, LINES[k]), 11.5, INK, 700, mono=True)
        if s.eof > 0.01:
            chip(p, 420, 296, "end of file", TEAL, TEAL_LT, 10.5, opacity=clamp(s.eof))
        if s.fly_a > 0.01:
            x = lerp(PROG_X + 70, KERNEL_X - 80, s.fly_u)
            pill(p, x, 220, s.fly_label, NIGHT, NIGHT_LT, 10, opacity=s.fly_a, shadow=None)
        if s.back_a > 0.01:
            x = lerp(KERNEL_X - 80, PROG_X + 120, s.back_u)
            pill(p, x, 250, s.back_label, BRASS, BRASS_LT, 10, opacity=s.back_a, shadow=None)

        CODE.draw(p, 26, 322, W - 52, "readfile_line_by_line", s, t, size=11.0, lead=16.0,
                  tint=TEAL if s.mode == "buffered" else RUST)
        caption(p, tl, t, CAP)
        progress(p, tl, t, total, RAIL)

    CAP, RAIL, height = layout(322, len(CODE), 16.0)
    return tl, draw, height


def build_bufreader(only=None):
    tl, draw, height = bufreader()
    return render("ch02-bufreader.gif", tl, draw, height, only=only)


BUILDERS = {
    "bufreader": build_bufreader,
}
