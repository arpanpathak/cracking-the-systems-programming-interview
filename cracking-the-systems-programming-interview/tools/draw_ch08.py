"""Figures for chapter 8: ownership and pointer types."""
from svgkit import *
OUT = "src/figures/"

# move
f = Figure(700, 190)
f.text(20, 22, "let a = String::from(\"hi\");  let b = a;", 12, mono=True)
f.text(20, 50, "before the move", 11, MUTED)
f.cell(20, 60, 60, 28, "a", PALE, size=11); f.cell(80, 60, 150, 28, "ptr | len 2 | cap 2", GREEN, size=10)
f.cell(300, 60, 60, 28, "\"hi\"", CREAM, size=11); f.arrow(230, 74, 298, 74, TEAL)
f.text(380, 80, "heap", 10, MUTED)
f.text(20, 120, "after the move", 11, MUTED)
f.cell(20, 130, 60, 28, "a", GREY, size=11, color=MUTED); f.cell(80, 130, 150, 28, "(cannot be used)", GREY, size=10, color=MUTED, dash=True)
f.cell(20, 160, 60, 28, "b", PALE, size=11); f.cell(80, 160, 150, 28, "ptr | len 2 | cap 2", GREEN, size=10)
f.cell(300, 160, 60, 28, "\"hi\"", CREAM, size=11); f.arrow(230, 174, 298, 174, TEAL)
f.text(380, 150, "The three header fields are copied into b. The text is not.", 11)
f.text(380, 168, "Only b may free the text, so a becomes unusable.", 11)
f.save(OUT + "own-move.svg")

# recursive type size
f = Figure(720, 170)
f.text(20, 22, "Why a recursive enum needs Box", 12, bold=True)
f.text(20, 48, "enum Expr { Lit(i64), Add(Expr, Expr) }", 11, mono=True, fill=RUST)
for d in range(4):
    w = 300 - d * 70
    f.rect(20 + d * 35, 58 + d * 10, w, 80 - d * 20, PINK if d == 0 else "none", RUST, 4, dash=d > 0)
f.text(40, 152, "an Add holds two Exprs, each of which may hold two more: no finite size", 10, RUST)
f.text(390, 48, "enum Expr { Lit(i64), Add(Box<Expr>, Box<Expr>) }", 11, mono=True, fill=TEAL)
f.cell(390, 64, 110, 30, "Box (8 bytes)", GREEN, size=10); f.cell(500, 64, 110, 30, "Box (8 bytes)", GREEN, size=10)
f.cell(420, 118, 70, 26, "Expr", PALE, size=10); f.cell(560, 118, 70, 26, "Expr", PALE, size=10)
f.arrow(445, 94, 450, 118, TEAL); f.arrow(555, 94, 590, 118, TEAL)
f.text(390, 162, "each child lives in its own heap block; an Add holds two pointers", 10, TEAL)
f.save(OUT + "own-box-recursive.svg")

# RefCell states
f = Figure(720, 170)
f.text(20, 22, "What a RefCell tracks at run time", 12, bold=True)
f.cell(20, 60, 170, 40, "not borrowed", PALE, size=11)
f.cell(270, 30, 190, 40, "n shared borrows", GREEN, size=11)
f.cell(270, 100, 190, 40, "1 mutable borrow", CREAM, size=11)
f.arrow(190, 72, 268, 52, TEAL); f.text(200, 50, "borrow()", 10, TEAL, mono=True)
f.arrow(190, 88, 268, 118, TEAL); f.text(190, 128, "borrow_mut()", 10, TEAL, mono=True)
f.text(480, 48, "another borrow(): allowed", 10, TEAL)
f.text(480, 66, "borrow_mut(): panics", 10, RUST)
f.text(480, 118, "any other borrow: panics", 10, RUST)
f.text(20, 162, "Each guard (Ref or RefMut) moves the cell back toward \"not borrowed\" when it is dropped.", 11)
f.save(OUT + "own-refcell.svg")

# Rc cycle
f = Figure(720, 190)
f.text(20, 22, "Two strong pointers in a cycle never reach zero", 12, bold=True)
f.cell(40, 60, 150, 40, "parent (strong 2)", PINK, size=11); f.cell(40, 130, 150, 40, "child (strong 2)", PINK, size=11)
f.arrow(80, 100, 80, 128, RUST); f.text(20, 118, "Rc", 10, RUST)
f.arrow(150, 130, 150, 102, RUST); f.text(158, 118, "Rc", 10, RUST)
f.text(40, 186, "dropping your handles leaves each count at 1: leaked", 10, RUST)
f.cell(420, 60, 150, 40, "parent (strong 1)", GREEN, size=11); f.cell(420, 130, 150, 40, "child (strong 1)", GREEN, size=11)
f.arrow(460, 100, 460, 128, TEAL); f.text(430, 118, "Rc", 10, TEAL)
f.arrow(530, 130, 530, 102, TEAL, dash=True); f.text(538, 118, "Weak", 10, TEAL)
f.text(420, 186, "the Weak link does not count: dropping the parent frees both", 10, TEAL)
f.save(OUT + "own-cycle.svg")
print("ok")
