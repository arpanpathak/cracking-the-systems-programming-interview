"""The types chapter animation (ch07-types.md), drawn with `motion`.

    python3 tools/animations.py parse-trace
"""

from motion_kit import Panel, layout
from motion import *  # noqa: F401,F403
from motion import Timeline, render

PARSE = Panel("src/problems/adt_idioms.rs",
              [("let mut parts = line.split_whitespace();", ".ok_or(CommandError::Empty)?;"),
               ("match verb {", None),
               ("\"create\" => {", ("other => Err(CommandError::UnknownVerb", 1))],
              ["let mut parts = line.split_whitespace();",
               ".ok_or(CommandError::Empty)?;",
               "let name = argument(&mut parts, \"name\")?.to_string();",
               "let raw = argument(&mut parts, \"gpu count\")?;",
               (".map_err(|_| CommandError::InvalidGpuCount(raw.to_string()))?;", 0),
               "let gpus = GpuCount::new(value)",
               "Ok(Self::Create { name, gpus })"])
STAGE_X = [120, 270, 420, 570, 720]
STAGE_NAMES = ["split", "verb", "name", "parse u32", "GpuCount::new"]
LANE = 186


def parse_trace():
    tl = Timeline(caption="", kind="step", code=-1.0, line="", tokens="", at=-1, passed=-1,
                  failed=-1, result="", result_kind="", value="")

    def stage(k, code, value="", dur=0.6):
        tl.set(at=k, code=float(code), value=value)
        tl.wait(dur)
        tl.set(passed=k)

    def fail(k, code, result, value=""):
        tl.set(at=k, code=float(code), value=value)
        tl.wait(0.6)
        tl.set(failed=k, result=result, result_kind="err")

    def reset(line, tokens):
        tl.set(line=line, tokens=tokens, at=-1, passed=-1, failed=-1, result="", result_kind="",
               value="", code=-1.0)

    tl.chapter("valid")
    reset("create triton 4", "create|triton|4")
    tl.say("parse(\"create triton 4\"). split_whitespace turns the line into an iterator of words.")
    stage(0, 0, "3 words", 0.8)
    tl.say("next() gives the verb. ok_or turns a missing word into CommandError::Empty.")
    stage(1, 1, "\"create\"")
    tl.say("argument takes the next word as the name, and the one after it as the raw count.")
    stage(2, 2, "\"triton\"")
    tl.set(code=3.0)
    tl.wait(0.5)
    tl.say("\"4\" parses as a u32. GpuCount::new checks it against 1..=64 and accepts it.")
    stage(3, 4, "4")
    stage(4, 5, "GpuCount(4)")
    tl.set(code=6.0, result="Ok(Create { name: \"triton\", gpus: GpuCount(4) })", result_kind="ok")
    tl.say("Every stage passed, so parse returns the command. Each ? returned nothing early.",
           "insight")
    tl.wait(1.2)

    tl.chapter("empty")
    tl.say("An empty line has no words. The first next() returns None.", "fail")
    reset("", "")
    tl.set(code=0.0)
    tl.wait(0.4)
    tl.set(passed=0)
    fail(1, 1, "Err(CommandError::Empty)")
    tl.say("ok_or makes it Err(Empty), and ? returns it at once. No later stage runs.", "fail")
    tl.wait(1.0)

    tl.chapter("not a number")
    tl.say("\"create triton many\" passes the verb and the name.", "fail")
    reset("create triton many", "create|triton|many")
    stage(0, 0, "3 words", 0.4)
    stage(1, 1, "\"create\"", 0.4)
    stage(2, 2, "\"triton\"", 0.4)
    tl.say("\"many\" is not a u32. map_err replaces the parse error with InvalidGpuCount, "
           "carrying the text typed.", "fail")
    fail(3, 4, "Err(InvalidGpuCount(\"many\"))")
    tl.wait(1.0)

    tl.chapter("out of range")
    tl.say("\"create triton 0\" is a valid u32, so it gets one stage further.", "fail")
    reset("create triton 0", "create|triton|0")
    stage(0, 0, "3 words", 0.3)
    stage(1, 1, "\"create\"", 0.3)
    stage(2, 2, "\"triton\"", 0.3)
    stage(3, 4, "0", 0.4)
    tl.say("GpuCount::new rejects 0, outside 1..=64. No GpuCount below 1 can ever be built.",
           "fail")
    fail(4, 5, "Err(InvalidGpuCount(\"0\"))")
    tl.wait(1.6)

    def draw(p, s, total):
        t = s.t
        title_block(p, "Command::parse, one stage at a time",
                    "Each stage either passes its value on or returns a typed error with ?.")
        p.text(26, 92, "line:", 12, MUTED, 600)
        chip(p, 70, 92, "\"%s\"" % s.line, INK, STAGE, 12, anchor="start")
        words = [w for w in s.tokens.split("|") if w]
        for k, w in enumerate(words):
            chip(p, 330 + k * 92, 92, w, TEAL, TEAL_LT, 11)
        p.line(STAGE_X[0], LANE, STAGE_X[-1], LANE, LINE, 2)
        for k, (x, name) in enumerate(zip(STAGE_X, STAGE_NAMES)):
            if k <= int(s.passed):
                fill, edge = TEAL_LT, TEAL
            elif k == int(s.failed):
                fill, edge = RUST_LT, RUST
            elif k == int(s.at):
                fill, edge = BRASS_LT, BRASS
            else:
                fill, edge = STAGE, LINE
            p.rect(x - 62, LANE - 26, 124, 52, fill, edge, 8, 1.5)
            p.text(x, LANE + 5, name, 11.5, INK, 700, "middle", mono=True)
        if int(s.at) >= 0 and s.value:
            chip(p, STAGE_X[int(s.at)], LANE + 46, s.value, BRASS, BRASS_LT, 10.5)
        if s.result:
            ok = s.result_kind == "ok"
            chip(p, W / 2, LANE + 88, s.result, TEAL if ok else RUST, TEAL_LT if ok else RUST_LT,
                 12)

        PARSE.draw(p, 26, 300, W - 52, "Command::parse", s, t, size=10.2, lead=13.6,
                   tint=RUST if int(s.failed) >= 0 else TEAL)
        caption(p, tl, t, CAP)
        progress(p, tl, t, total, RAIL)

    CAP, RAIL, height = layout(300, len(PARSE), 13.6)
    return tl, draw, height


def build_parse_trace(only=None):
    tl, draw, height = parse_trace()
    return render("ch07-parse-trace.gif", tl, draw, height, only=only)


BUILDERS = {
    "parse-trace": build_parse_trace,
}
