"""Figures for chapter 30: the queens bitboard."""
from svgkit import *
OUT = "src/figures/"
CELL = 24


def board(f, x0, y0, queen, title, mark=None):
    f.text(x0, y0 - 10, title, 10, bold=True)
    for x in range(8):
        for y in range(8):
            fill = WHITE
            if queen is not None:
                qx, qy = queen
                on_line = x == qx or y == qy or x - y == qx - qy or x + y == qx + qy
                fill = PINK if on_line else WHITE
            f.rect(x0 + y * CELL, y0 + x * CELL, CELL, CELL, fill, BORDER, 0, width=0.8)
    if queen is not None:
        qx, qy = queen
        f.text(x0 + qy * CELL + CELL / 2, y0 + qx * CELL + 17, "Q", 13, INK, anchor="middle", bold=True)
    if mark is not None:
        mx, my = mark
        f.rect(x0 + my * CELL + 2, y0 + mx * CELL + 2, CELL - 4, CELL - 4, "none", TEAL, 3, width=2)


# 1. the 4 lines of a queen and their bits
f = Figure(760, 320)
f.text(20, 22, "A queen at (1, 2) occupies 4 lines, and each line is 1 bit", 12, bold=True)
x0, y0 = 50, 60
for y in range(8):
    f.text(x0 + y * CELL + CELL / 2, y0 - 6, str(y), 9, MUTED, anchor="middle")
for x in range(8):
    f.text(x0 - 10, y0 + x * CELL + 16, str(x), 9, MUTED, anchor="middle")
colors = {"row": "#d7ecef", "col": "#f6e7c3", "diag": PINK, "anti": GREEN}
for x in range(8):
    for y in range(8):
        fill = WHITE
        if x + y == 3:
            fill = colors["anti"]
        if x - y == -1:
            fill = colors["diag"]
        if y == 2:
            fill = colors["col"]
        if x == 1:
            fill = colors["row"]
        f.rect(x0 + y * CELL, y0 + x * CELL, CELL, CELL, fill, BORDER, 0, width=0.8)
f.text(x0 + 2 * CELL + CELL / 2, y0 + 1 * CELL + 17, "Q", 13, INK, anchor="middle", bold=True)
f.text(x0, y0 + 8 * CELL + 20, "row x runs down, column y runs across", 9, MUTED)
rows = [("rows: u8", "row x = 1", 8, 1, colors["row"]),
        ("cols: u8", "column y = 2", 8, 2, colors["col"]),
        ("diags: u16", "x + 7 - y = 6", 15, 6, colors["diag"]),
        ("anti_diags: u16", "x + y = 3", 15, 3, colors["anti"])]
for r, (name, rule, width, bit, fill) in enumerate(rows):
    y = 64 + r * 58
    f.text(290, y + 4, name, 10, mono=True, bold=True)
    f.text(420, y + 4, rule, 10, MUTED, mono=True)
    for b in range(width):
        bx = 290 + (width - 1 - b) * 28
        f.rect(bx, y + 12, 26, 22, fill if b == bit else WHITE, BORDER, 3, width=0.8)
        f.text(bx + 13, y + 28, "1" if b == bit else "0", 10, INK, mono=True, anchor="middle", bold=b == bit)
        if b in (0, bit, width - 1):
            f.text(bx + 13, y + 46, str(b), 8, MUTED, anchor="middle")
f.save(OUT + "ch30-queen-lines.svg")

# 2. moving a queen: lift, place, restore on failure
f = Figure(760, 300)
f.text(20, 22, "move_piece from (0, 0) to (2, 2): lift the queen, then place it", 12, bold=True)
board(f, 30, 60, (0, 0), "1. before: (2, 2) lies on the queen's diagonal", mark=(2, 2))
board(f, 290, 60, None, "2. after remove(from): all 4 bits cleared", mark=(2, 2))
board(f, 550, 60, (2, 2), "3. after place(to): bits of (2, 2) set")
f.arrow(230, 156, 284, 156, INK)
f.arrow(490, 156, 544, 156, INK)
f.text(20, 280, "If place(to) fails because another queen attacks (2, 2), *self = before restores board 1.", 10)
f.save(OUT + "ch30-move.svg")
print("ok")
