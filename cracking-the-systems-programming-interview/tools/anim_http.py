"""The HTTP chapter animations (ch21-http.md), drawn with `motion`.

    python3 tools/animations.py http-framing keep-alive
"""

import math

from motion import *  # noqa: F401,F403
from motion import Timeline, render


# ----------------------------------------------- 21.1: where a request ends

LINE_X, LINE_Y, LEAD = 44, 104, 24.0
CARD = (500, 88, 294, 250)

REQUESTS = {
    "length": ["POST /upload HTTP/1.1", "Host: x", "Content-Length: 5", "", "hello"],
    "chunked": ["POST /upload HTTP/1.1", "Host: x", "Transfer-Encoding: chunked", "", "5", "hello",
                "0", ""],
    "both": ["POST / HTTP/1.1", "Host: x", "Content-Length: 37", "Transfer-Encoding: chunked", "",
             "0", "", "GET /admin HTTP/1.1", "Host: x", ""],
}
# Which lines end with CRLF on the wire. The Content-Length body does not.
CRLF = {"length": 4, "chunked": 8, "both": 10}
HEAD_END = {"length": 3, "chunked": 3, "both": 4}

PARSE_BODY = [
    "if !transfer_encoding.is_empty() && !content_length.is_empty() {",
    "    return Err(ParseError::AmbiguousBodyLength);",
    "}",
    "if !transfer_encoding.is_empty() { return decode_chunked(..); }",
    "if content_length.is_empty() { return Ok(Vec::new()); }",
    "// otherwise: exactly Content-Length bytes",
]


def line_y(i):
    return LINE_Y + i * LEAD


def crlf_chip(p, x, y, color=FAINT, fill="#f1f4f7", opacity=1.0):
    p.rect(x, y - 12, 30, 16, fill, color, 4, 1, opacity=opacity)
    p.text(x + 15, y, "\\r\\n", 9, color, 700, "middle", mono=True, opacity=opacity)


def http_framing():
    tl = Timeline(req="length", req_a=1.0, scan=-1.0, scan_a=0.0, head=0.0,
                  f_line=0.0, f_headers=0.0, ruler=0.0, chunk_step=0.0,
                  proxy=0.0, backend=0.0, smuggled=0.0, verdict=0.0, code=-1.0,
                  hot_cl=0.0, hot_te=0.0)

    def show(kind):
        tl.to(0.4, req_a=0.0, head=0.0, f_line=0.0, f_headers=0.0, ruler=0.0,
              chunk_step=0.0, proxy=0.0, backend=0.0, smuggled=0.0, hot_cl=0.0, hot_te=0.0,
              code=-1.0)
        tl.set(req=kind, scan=-1.0)
        tl.to(0.4, req_a=1.0)

    def find_head(kind, slow):
        tl.set(scan=0.0)
        tl.to(0.3, scan_a=1.0)
        tl.to((2.4 if slow else 1.2), in_out, scan=float(HEAD_END[kind]))
        tl.to(0.4, back, head=1.0)
        tl.to(0.3, scan_a=0.0)

    tl.chapter("the head")
    tl.say("A request arrives as bytes. Every line of the head ends with \\r\\n.")
    tl.wait(1.0)
    tl.say("The parser slides a four-byte window until it sees \\r\\n\\r\\n: a blank line. That "
           "is where the head ends.")
    find_head("length", True)
    tl.say("The first line gives the method, the target, and the version. Each other line is a "
           "header.")
    tl.to(0.6, f_line=1.0)
    tl.to(0.8, f_headers=1.0)
    tl.wait(0.6)

    tl.chapter("Content-Length")
    tl.say("This head says Content-Length: 5, so the body is the next 5 bytes.")
    tl.to(0.4, hot_cl=1.0, code=5.0)
    tl.to(2.0, linear, ruler=5.0)
    tl.say("Whatever follows those 5 bytes belongs to the next request.", "insight")
    tl.wait(1.0)

    tl.chapter("chunked")
    show("chunked")
    find_head("chunked", False)
    tl.to(0.5, f_line=1.0, f_headers=1.0)
    tl.say("Transfer-Encoding: chunked sends the body in pieces. Each piece starts with its size, "
           "in hex.")
    tl.to(0.4, hot_te=1.0, code=3.0)
    tl.to(0.8, chunk_step=1.0)
    tl.say("Size 5: take the next 5 bytes. Then read the next size line.")
    tl.to(0.8, chunk_step=2.0)
    tl.wait(0.6)
    tl.to(0.8, chunk_step=3.0)
    tl.say("Size 0 ends the body. The body carries its own end marker.", "insight")
    tl.wait(1.0)

    tl.chapter("both")
    show("both")
    find_head("both", False)
    tl.to(0.5, f_line=1.0, f_headers=1.0)
    tl.say("This head has both headers. They describe the same bytes in two different ways.",
           "fail")
    tl.to(0.5, hot_cl=1.0, hot_te=1.0)
    tl.wait(0.8)
    tl.say("A proxy that reads Content-Length: 37 sees one request, with a 37-byte body.", "fail")
    tl.to(0.7, back, proxy=1.0)
    tl.say("A back-end that reads chunks stops at size 0, and finds a second request after it: "
           "GET /admin.", "fail")
    tl.to(0.7, back, backend=1.0)
    tl.to(0.7, back, smuggled=1.0)
    tl.wait(0.6)
    tl.say("That hidden request skipped every check the proxy made. This is request smuggling.",
           "fail")
    tl.wait(0.8)
    tl.say("The parser refuses the message outright: 400 Bad Request, and the connection "
           "closes.", "insight")
    tl.to(0.3, code=0.0)
    tl.to(0.6, back, verdict=1.0)
    tl.wait(1.4)

    def draw(p, s, total):
        t = s.t
        title_block(p, "Where does an HTTP request end?",
                    "The head ends at a blank line. The head then says where the body ends.")
        lines = REQUESTS[s.req]
        crlf = CRLF[s.req]
        head_end = HEAD_END[s.req]

        with p.group(opacity=s.req_a):
            # the request, line by line, with its line ends visible
            p.text(LINE_X - 18, LINE_Y - 22, "bytes on the wire", 11, MUTED, 600)
            for i, text in enumerate(lines):
                y = line_y(i)
                in_body = i > head_end
                color = INK
                if s.req == "both" and i > head_end + 2 and s.smuggled > 0.5:
                    color = RUST
                weight = 700 if (s.hot_cl > 0.5 and text.startswith("Content-Length")) or \
                    (s.hot_te > 0.5 and text.startswith("Transfer-Encoding")) else 400
                hot = (s.hot_cl > 0.5 and text.startswith("Content-Length")) or \
                      (s.hot_te > 0.5 and text.startswith("Transfer-Encoding"))
                if hot:
                    p.rect(LINE_X - 6, y - 16, text_width(text, 13.5, True) + 12, 22,
                           RUST_LT if s.req == "both" else BRASS_LT, "none", 4)
                p.text(LINE_X, y, text, 13.5, color if not in_body or s.head > 0.5 else INK, weight,
                       mono=True)
                if i < crlf:
                    x = LINE_X + text_width(text, 13.5, True) + (8 if text else 0)
                    near = s.scan_a > 0.01 and abs(s.scan - i) < 0.5
                    crlf_chip(p, x, y, BRASS if near else FAINT, BRASS_LT if near else "#f1f4f7")
            # the sliding window
            if s.scan_a > 0.01:
                k = min(int(round(s.scan)), len(lines) - 1)
                y = lerp(line_y(math.floor(s.scan)), line_y(min(math.floor(s.scan) + 1,
                                                                len(lines) - 1)), s.scan % 1.0)
                x = LINE_X + text_width(lines[k], 13.5, True) + (8 if lines[k] else 0)
                p.rect(x - 4, y - 16, 38, 22, "none", BRASS, 5, 2.2, opacity=s.scan_a)
                p.text(x + 44, y - 1, "windows(4)", 10.5, BRASS, 700, mono=True, opacity=s.scan_a)
            # the end of the head
            if s.head > 0.01:
                y = line_y(head_end) + 9
                p.line(LINE_X - 8, y, 470, y, BRASS, 2.2, dash="6 4", opacity=s.head)
                p.text(470, y - 5, "head ends", 11, BRASS, 700, "end", opacity=s.head)

            # Content-Length: a ruler over exactly five bytes
            if s.req == "length" and s.ruler > 0.01:
                y = line_y(4) + 12
                n = int(math.floor(s.ruler + 0.001))
                for i in range(5):
                    x = LINE_X + i * text_width("h", 13.5, True)
                    done = i < n
                    p.rect(x, y, text_width("h", 13.5, True) - 1.5, 5, TEAL if done else LINE,
                           "none", 2)
                p.text(LINE_X + 5 * text_width("h", 13.5, True) + 10, y + 6,
                       "%d of 5 bytes" % n, 11, TEAL, 700)

            # chunked: the cursor visits size, data, size
            if s.req == "chunked" and s.chunk_step > 0.01:
                steps = [(4, "size 5, in hex"), (5, "take 5 bytes"), (6, "size 0: the body ends")]
                k = min(int(math.ceil(s.chunk_step - 0.001)) - 1, 2)
                for j in range(k + 1):
                    row, label = steps[j]
                    y = line_y(row)
                    x = 330
                    current = j == k
                    col = TEAL if current else FAINT
                    p.path("M %s %s L %s %s" % (f2(x - 10), f2(y - 4), f2(x - 60), f2(y - 4)), "none",
                           col, 1.6)
                    p.text(x, y, label, 11.5, col, 700 if current else 400)

            # both: two readers bracket the same bytes differently
            if s.req == "both":
                first, last = head_end + 1, len(lines) - 1
                if s.proxy > 0.01:
                    x = 12
                    with p.group(opacity=clamp(s.proxy)):
                        p.path("M %s %s L %s %s L %s %s L %s %s" % (
                            f2(x + 14), f2(line_y(first) - 14), f2(x), f2(line_y(first) - 14),
                            f2(x), f2(line_y(last) + 6), f2(x + 14), f2(line_y(last) + 6)),
                               "none", NIGHT, 2.4)
                        p.text(LINE_X + 60, line_y(first + 1) + 4, "proxy: all 37 bytes are body",
                               11, NIGHT, 700)
                if s.backend > 0.01:
                    x = 330
                    with p.group(opacity=clamp(s.backend)):
                        p.path("M %s %s L %s %s L %s %s L %s %s" % (
                            f2(x - 14), f2(line_y(first) - 14), f2(x), f2(line_y(first) - 14),
                            f2(x), f2(line_y(first + 1) + 6), f2(x - 14), f2(line_y(first + 1) + 6)),
                               "none", TEAL, 2.4)
                        p.text(x + 10, line_y(first) + 4, "back-end: body ends at 0", 11, TEAL, 700)
                if s.smuggled > 0.01:
                    x = 330
                    with p.group(opacity=clamp(s.smuggled)):
                        p.path("M %s %s L %s %s L %s %s L %s %s" % (
                            f2(x - 14), f2(line_y(first + 2) - 14), f2(x), f2(line_y(first + 2) - 14),
                            f2(x), f2(line_y(last) + 6), f2(x - 14), f2(line_y(last) + 6)),
                               "none", RUST, 2.4)
                        p.text(x + 10, line_y(first + 3), "back-end: a second request!", 11, RUST,
                               700)

        # the parsed request
        x, y, w, h = CARD
        p.rect(x, y, w, h, PAPER, mix(LINE, RUST, s.verdict), 12, 1.6, shadow="shadow")
        p.text(x + 14, y + 22, "what the parser found", 11, MUTED, 600)
        if s.f_line > 0.01:
            parts = lines[0].split(" ")
            with p.group(opacity=clamp(s.f_line), dx=(1 - clamp(s.f_line)) * -20):
                for i, (name, value) in enumerate(zip(("method", "target", "version"), parts)):
                    p.text(x + 14, y + 50 + i * 22, name, 11.5, MUTED, 400, mono=True)
                    p.text(x + 92, y + 50 + i * 22, value, 12.5, INK, 700, mono=True)
        if s.f_headers > 0.01:
            headers = [l for l in lines[1:head_end] if l]
            with p.group(opacity=clamp(s.f_headers), dx=(1 - clamp(s.f_headers)) * -20):
                p.line(x + 14, y + 112, x + w - 14, y + 112, LINE, 1)
                for i, text in enumerate(headers):
                    name, value = text.split(": ", 1)
                    hot = (name == "Content-Length" and s.hot_cl > 0.5) or \
                          (name == "Transfer-Encoding" and s.hot_te > 0.5)
                    col = (RUST if s.req == "both" else BRASS) if hot else INK
                    p.text(x + 14, y + 134 + i * 22, name, 11.5, col if hot else MUTED,
                           700 if hot else 400, mono=True)
                    p.text(x + 176, y + 134 + i * 22, value, 12, col, 700, mono=True)
        if s.verdict > 0.01:
            with p.group(opacity=clamp(s.verdict), scale=lerp(1.3, 1.0, clamp(s.verdict)),
                         cx=x + w / 2, cy=y + h - 34):
                p.rect(x + 20, y + h - 56, w - 40, 44, RUST_LT, RUST, 8, 2.2)
                p.text(x + w / 2, y + h - 38, "400 Bad Request", 14, RUST, 700, "middle", mono=True)
                p.text(x + w / 2, y + h - 20, "Connection: close", 11.5, RUST, 600, "middle",
                       mono=True)

        code_panel(p, 26, 354, W - 52, "parse_body decides", PARSE_BODY, s.code, size=10.8,
                   lead=15.5, tint=RUST if s.req == "both" else TEAL,
                   reveal=s.timeline.reached("code", t))
        caption(p, tl, t, 494)
        progress(p, tl, t, total, 580)

    return tl, draw, 614


# ------------------------------------------------ 21.2: the keep-alive loop

CL_X, SV_X, DESK = 96, 724, 226
WIRE_A, WIRE_B, WIRE_Y = 176, 646, 150
BUF = (250, 196, 320, 44)

LOOP = [
    "loop {",
    "    match parse_request(&buffer, limits) {",
    "        Ok(request) => { route, write the response; clear or close }",
    "        Err(ParseError::Incomplete) => { read more into buffer }",
    "        Err(error) => { write 400, then close }",
    "    }",
    "}",
]


def keep_alive():
    tl = Timeline(piece_u=0.0, piece_a=0.0, piece="", buffer="", result="", result_a=0.0,
                  route_a=0.0, route_in="", route_out="", resp_u=0.0, resp_a=0.0, resp="",
                  code=-1.0, requests=0, closed=0.0, sv_awake=0.0)

    def send(text, dur=1.4):
        tl.set(piece=text, piece_u=0.0)
        tl.to(0.2, piece_a=1.0)
        tl.to(dur, in_out, piece_u=1.0)
        tl.set(buffer=tl._at("buffer", tl.now) + text)
        tl.to(0.2, piece_a=0.0)

    def parse(result):
        tl.set(result=result)
        tl.to(0.4, back, result_a=1.0)

    def respond(text, dur=1.4):
        tl.set(resp=text, resp_u=0.0)
        tl.to(0.2, resp_a=1.0)
        tl.to(dur, in_out, resp_u=1.0)
        tl.to(0.2, resp_a=0.0)

    tl.chapter("two reads")
    tl.say("One connection. The server keeps a buffer of every byte it has read so far.")
    tl.wait(0.8)
    tl.say("The first read brings only part of a request. TCP delivers bytes, not messages.")
    tl.to(0.4, sv_awake=1.0)
    send("GET /healthz HTTP/1.1\\r\\nHo")
    tl.say("The parser finds no blank line yet, so it returns Incomplete, and the loop reads "
           "again.")
    tl.to(0.3, code=1.0)
    parse("Incomplete")
    tl.to(0.3, code=3.0)
    tl.wait(0.8)
    tl.say("The second read completes the head. The loop parses the whole buffer again.")
    tl.to(0.3, result_a=0.0)
    send("st: x\\r\\n\\r\\n")
    tl.to(0.3, code=1.0)
    parse("Ok(GET /healthz)")
    tl.set(requests=1)

    tl.chapter("route")
    tl.say("route is a pure function: a request goes in, a status and a body come out.")
    tl.to(0.3, code=2.0)
    tl.set(route_in="GET /healthz", route_out="(200, \"ok\")")
    tl.to(0.6, back, route_a=1.0)
    tl.wait(0.8)
    tl.say("The response goes back with Connection: keep-alive. The buffer is cleared, and the "
           "connection stays open.")
    respond("200 OK  keep-alive")
    tl.to(0.5, buffer="", result_a=0.0, route_a=0.0)
    tl.wait(0.6)

    tl.chapter("keep-alive")
    tl.say("The next request reuses the same connection, with no new handshake.")
    tl.to(0.3, code=1.0)
    send("POST /v1/gpu-workloads ...\\r\\n\\r\\n{..}", 1.2)
    parse("Ok(POST ...)")
    tl.set(requests=2)
    tl.to(0.3, code=2.0)
    tl.set(route_in="POST /v1/gpu-workloads", route_out="(201, {\"id\":..})")
    tl.to(0.5, back, route_a=1.0)
    respond("201 Created  keep-alive", 1.2)
    tl.to(0.5, buffer="", result_a=0.0, route_a=0.0)

    tl.chapter("framing error")
    tl.say("A third request carries both Content-Length and Transfer-Encoding.", "fail")
    tl.to(0.3, code=1.0)
    send("POST / ... Content-Length + chunked", 1.2)
    parse("Err(AmbiguousBodyLength)")
    tl.to(0.3, code=4.0)
    tl.say("The server cannot know where the next request would start, so it answers 400 and "
           "closes.", "fail")
    respond("400 Bad Request  close", 1.2)
    tl.to(0.6, closed=1.0, sv_awake=0.0)
    tl.say("The loop reads and parses until a request is complete. A framing error ends the connection.", "insight")
    tl.wait(1.0)

    def draw(p, s, total):
        t = s.t
        title_block(p, "One connection, many requests: the keep-alive loop",
                    "handle_connection reads bytes, asks the parser, and answers.")
        scoreboard(p, [("requests served", int(s.requests), TEAL)])
        robot(p, CL_X, DESK, "#3b7dd8", 1.0, 1.0, "client", "curl", look=0.8)
        robot(p, SV_X, DESK, TEAL, s.sv_awake, s.sv_awake, "server", "handle_connection",
              look=-0.8)

        # the connection
        cut = s.closed
        p.rect(WIRE_A, WIRE_Y - 3, WIRE_B - WIRE_A, 6, mix("#e6ebf0", RUST_LT, cut), "none", 3)
        if cut > 0.01:
            mx = (WIRE_A + WIRE_B) / 2
            with p.group(opacity=cut):
                p.rect(mx - 30, WIRE_Y - 8, 60, 16, PAPER, "none", 0)
                chip(p, mx, WIRE_Y, "closed", RUST, RUST_LT, 11)
        if s.piece_a > 0.01:
            x = lerp(WIRE_A + 90, WIRE_B - 90, s.piece_u)
            pill(p, x, WIRE_Y - 28, s.piece.replace("\\r\\n", " ↵ "), BRASS, BRASS_LT, 11,
                 opacity=s.piece_a)
        if s.resp_a > 0.01:
            x = lerp(WIRE_B - 90, WIRE_A + 90, s.resp_u)
            bad = s.resp.startswith("4")
            pill(p, x, WIRE_Y + 28, s.resp, RUST if bad else TEAL, RUST_LT if bad else TEAL_LT, 11,
                 opacity=s.resp_a)

        # the server's buffer, and what the parser said about it
        bx, by, bw, bh = BUF
        p.text(bx, by - 8, "buffer (every byte read so far)", 11, MUTED, 600)
        p.rect(bx, by, bw, bh, "#fbfcfd", LINE, 8, 1.3)
        text = s.buffer.replace("\\r\\n", " ↵ ")
        if len(text) > 40:
            text = "…" + text[-39:]
        p.text(bx + 12, by + 27, text or "(empty)", 11.5, INK if text else FAINT, 600, mono=True)
        if s.result_a > 0.01:
            bad = s.result.startswith("Err")
            ok = s.result.startswith("Ok")
            col = RUST if bad else (TEAL if ok else BRASS)
            pill(p, bx + bw / 2, by + bh + 26, "parse_request -> " + s.result, col,
                 RUST_LT if bad else (TEAL_LT if ok else BRASS_LT), 11.5, opacity=clamp(s.result_a),
                 shadow=None)

        # route: a box with a request going in and a tuple coming out
        if s.route_a > 0.01:
            with p.group(opacity=clamp(s.route_a)):
                rx, ry = 410, 100
                p.rect(rx - 70, ry - 20, 140, 40, SCREEN, "none", 8)
                p.text(rx, ry + 5, "route(&request)", 12, "#e8eef3", 700, "middle", mono=True)
                p.text(rx - 80, ry + 5, s.route_in, 11, MUTED, 600, "end", mono=True)
                p.text(rx + 80, ry + 5, "→ " + s.route_out, 11, TEAL, 700, mono=True)

        code_panel(p, 26, 318, W - 52, "handle_connection", LOOP, s.code, size=10.8, lead=15.5,
                   reveal=s.timeline.reached("code", t))
        caption(p, tl, t, 480)
        progress(p, tl, t, total, 566)

    return tl, draw, 600


def build_http_framing(only=None):
    tl, draw, height = http_framing()
    return render("ch21-http-framing.gif", tl, draw, height, only=only)


def build_keep_alive(only=None):
    tl, draw, height = keep_alive()
    return render("ch21-keep-alive.gif", tl, draw, height, only=only, extra_colors=("#3b7dd8",))


BUILDERS = {
    "http-framing": build_http_framing,
    "keep-alive": build_keep_alive,
}

if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    if args and args[0] == "frames":
        for path in BUILDERS[args[1]](only=[float(a) for a in args[2:]]):
            print(path)
    else:
        for name in args or BUILDERS:
            print(BUILDERS[name]())
