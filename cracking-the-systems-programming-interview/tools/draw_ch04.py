"""Figures for chapter 4: iterators and references."""
from svgkit import *
OUT = "src/figures/"

# iterator as a cursor
f = Figure(700, 190)
f.text(20, 22, "let mut it = [10, 20, 30].iter();   each call to it.next() moves a cursor one element", 12, mono=True)
for r, (pos, ret) in enumerate([(0, "Some(&10)"), (1, "Some(&20)"), (2, "Some(&30)"), (3, "None")]):
    y = 40 + r * 36
    for i, v in enumerate(["10", "20", "30"]):
        f.cell(40 + i * 50, y, 50, 28, v, GREEN if i == pos else PALE, size=11)
    if pos < 3:
        f.text(40 + pos * 50 + 25, y - 2, "▼", 9, TEAL, anchor="middle")
    else:
        f.text(200, y + 18, "▼ past the end", 9, TEAL)
    f.text(330, y + 18, f"call {r + 1}: it.next() returns {ret}", 11, mono=True)
f.save(OUT + "iter-cursor.svg")

# three ways to iterate
f = Figure(720, 190)
f.text(20, 22, "Three ways to walk a Vec<String> named names", 12, bold=True)
rows = [("names.iter()", "&String", "borrows each element; names is unchanged and still usable", GREEN),
        ("names.iter_mut()", "&mut String", "borrows each element mutably; you can change them in place", CREAM),
        ("names.into_iter()", "String", "moves each element out; names is used up and cannot be used after", PINK)]
for r, (call, item, note, fill) in enumerate(rows):
    y = 40 + r * 46
    f.cell(20, y, 170, 32, call, fill, size=11)
    f.cell(200, y, 110, 32, item, PALE, size=11)
    f.text(320, y + 20, note, 11)
f.text(200, 36, "each item is a", 10, MUTED)
f.text(20, 182, "A for loop over &names calls iter(); over &mut names, iter_mut(); over names, into_iter().", 11)
f.save(OUT + "iter-kinds.svg")

# pipeline
f = Figure(720, 200)
f.text(20, 22, "slice.iter().filter(|&&x| x % 2 == 0).map(|&x| x * 10).collect()   on [10, 15, 20]", 11, mono=True)
cols = [("iter()", ["&10", "&15", "&20"]), ("filter", ["&10", "(dropped)", "&20"]), ("map", ["100", "", "200"]), ("collect", ["vec![100, 200]"])]
for c, (name, vals) in enumerate(cols):
    x = 20 + c * 175
    f.cell(x, 40, 150, 28, name, CREAM, size=11)
    for r, v in enumerate(vals):
        if v:
            f.cell(x, 80 + r * 32, 150, 26, v, GREY if v == "(dropped)" else PALE, size=11, color=MUTED if v == "(dropped)" else INK)
    if c < 3:
        f.arrow(x + 152, 54, x + 173, 54, TEAL)
f.text(20, 190, "Nothing runs until collect() asks for items. Then each item flows through every stage before the next one starts.", 11)
f.save(OUT + "iter-pipeline.svg")

# reference to a reference
f = Figure(700, 170)
f.text(20, 22, "Inside filter's closure, the argument is a reference to an item, and the item is itself a reference", 11)
f.cell(20, 60, 150, 34, "slice element 10", GREEN, size=11)
f.text(20, 112, "i32 in the slice", 10, MUTED)
f.cell(250, 60, 120, 34, "&i32", PALE, size=11)
f.text(250, 112, "the item from iter()", 10, MUTED)
f.cell(450, 60, 120, 34, "&&i32", CREAM, size=11)
f.text(450, 112, "what filter passes", 10, MUTED)
f.arrow(250, 77, 172, 77, TEAL); f.arrow(450, 77, 372, 77, TEAL)
f.text(20, 146, "The pattern |&&x| removes both layers, so x is the i32. In map, |&x| removes the one layer.", 11, mono=True)
f.save(OUT + "iter-refref.svg")

# dangling reference rejected
f = Figure(720, 190)
f.text(20, 22, "Why a reference must not outlive its data", 12, bold=True)
f.text(20, 46, "let r;", 11, mono=True)
f.text(20, 64, "{", 11, mono=True)
f.text(40, 82, "let s = String::from(\"hi\");", 11, mono=True)
f.text(40, 100, "r = &s;", 11, mono=True)
f.text(20, 118, "}                // s is dropped here; its heap text is freed", 11, mono=True)
f.text(20, 136, "println!(\"{r}\");   // r would point to freed memory", 11, mono=True)
f.rect(390, 60, 320, 56, PINK, RUST)
f.text(400, 80, "error[E0597]: `s` does not live long enough", 10, RUST, mono=True)
f.text(400, 100, "borrowed value does not live long enough", 10, RUST, mono=True)
f.text(20, 170, "The compiler compares how long r is used with how long s lives, and rejects the program before it runs.", 11)
f.save(OUT + "iter-dangling.svg")
print("ok")
