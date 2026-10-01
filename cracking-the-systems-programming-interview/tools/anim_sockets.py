"""The sockets chapter animations (ch20-sockets.md), drawn with `motion`.

    python3 tools/animations.py tcp-handshake bdp epoll
"""

import math

from motion import *  # noqa: F401,F403
from motion import Timeline, render
from motion_kit import Panel, layout, nth_after


# ------------------------------------------- 20.3: a connection, end to end

CL_X, SV_X = 130, 690
DESK = 236
WIRE_Y = 152
WIRE_A, WIRE_B = 232, 588          # where segments leave and arrive
MSG = "hello echo"

CLIENT = Panel("src/bin/tcp_echo_server.rs",
               [("let mut client = TcpStream::connect(address).expect(\"connect\");",
                 ".expect(\"read echo\");")],
               ["let mut client = TcpStream::connect(address)", ".write_all(b\"hello echo\")",
                ".shutdown(Shutdown::Write)", ".read_to_end(&mut echoed)"])
SERVER = Panel("src/bin/tcp_echo_server.rs",
               [("let (stream, _) = listener", ".expect(\"accept one connection\");"),
                (("loop {", nth_after("src/bin/tcp_echo_server.rs", "loop {", "fn handle_connection(")), "}")],
               ["let (stream, _) = listener", "loop {", "let read = stream.read(&mut buffer)?;",
                "if read == 0 {", "stream.write_all(&buffer[..read])?;"], separate=True)

SEG_COLORS = {"SYN": TEAL, "SYN+ACK": TEAL, "ACK": TEAL, "data": BRASS, "FIN": RUST,
              "FIN+ACK": RUST}


def segment(p, x, y, flag, detail, color, payload="", opacity=1.0):
    """One TCP segment in flight: its flags on a coloured tab, its numbers below."""
    if opacity <= 0.01:
        return
    w = max(118, text_width(payload, 12, True) + 26, text_width(detail, 10.5, True) + 22)
    h = 50 if payload else 40
    with p.group(opacity=opacity):
        p.rect(x - w / 2, y - h / 2, w, h, PAPER, color, 8, 1.8, shadow="lift")
        p.rect(x - w / 2, y - h / 2, w, 17, color, "none", 8)
        p.rect(x - w / 2, y - h / 2 + 9, w, 8, color, "none", 0)
        p.text(x, y - h / 2 + 13, flag, 11.5, PAPER, 700, "middle", mono=True)
        p.text(x, y - h / 2 + 32, detail, 10.5, INK, 600, "middle", mono=True)
        if payload:
            p.text(x, y - h / 2 + 45, '"%s"' % payload, 11, BRASS, 700, "middle", mono=True)


def byte_row(p, x, y, count, label, color=BRASS, cell=14):
    """A kernel buffer: ten byte cells, the first `count` of them holding data."""
    p.text(x, y + 12, label, 10.5, MUTED, 600)
    x0 = x + 64
    for i in range(len(MSG)):
        full = i < count
        p.rect(x0 + i * cell, y, cell - 2, 17, mix(PAPER, BRASS_LT, 1.0 if full else 0.0),
               color if full else LINE, 3, 1.1)
        if full:
            p.text(x0 + i * cell + (cell - 2) / 2, y + 13, MSG[i], 10.5, INK, 700, "middle",
                   mono=True)


def tcp_handshake():
    tl = Timeline(caption="", kind="step",
                  cl_state="CLOSED", sv_state="LISTEN", cl_awake=1.0, sv_awake=0.0,
                  cl_code=-1.0, sv_code=0.0, seg_u=0.0, seg_a=0.0, seg_flag="SYN",
                  seg_detail="", seg_dir=1, seg_payload="",
                  kernel_focus=0.0, queue_a=0.0, queue_u=0.0,
                  sv_recv=0.0, cl_recv=0.0, read_a=0.0, read_label="read -> 10",
                  echoed_a=0.0, bug=0.0, verdict=0.0, clock="")

    def say(text, kind="step"):
        tl.say(text, kind)

    def send(flag, detail, direction, payload="", dur=1.5):
        tl.set(seg_u=0.0, seg_flag=flag, seg_detail=detail, seg_dir=direction,
               seg_payload=payload)
        tl.to(0.25, seg_a=1.0)
        tl.to(dur, in_out, seg_u=1.0)
        tl.to(0.2, seg_a=0.0)

    def flash_read(label, color_kind="data"):
        tl.set(read_label=label)
        tl.to(0.3, back, read_a=1.0)

    # ---- listening
    tl.chapter("listen")
    say("The server called bind and listen. Its thread is blocked in accept, asleep until a "
        "connection is ready.")
    tl.wait(3.6)

    # ---- the handshake
    tl.chapter("handshake")
    say("The client calls connect. Its kernel sends SYN with a starting sequence number, "
        "1000, and connect blocks.")
    tl.to(0.4, cl_code=0.0)
    tl.set(cl_state="SYN-SENT")
    tl.also(0.6, cl_awake=0.0)
    send("SYN", "seq 1000", 1)
    say("The server's kernel answers SYN+ACK: its own number 5000, and ack 1001. The server "
        "thread is still asleep.")
    tl.set(sv_state="SYN-RCVD")
    tl.to(0.4, kernel_focus=1.0)
    tl.wait(0.6)
    send("SYN+ACK", "seq 5000  ack 1001", -1)
    say("The client's kernel replies ACK 5001, and connect returns. The client is connected.")
    tl.set(cl_state="ESTABLISHED")
    tl.to(0.6, back, cl_awake=1.0)
    send("ACK", "ack 5001", 1)
    say("The finished connection waits in the accept queue. accept takes it, and the server "
        "thread wakes.")
    tl.set(sv_state="ESTABLISHED")
    tl.to(0.5, back, queue_a=1.0, kernel_focus=0.0)
    tl.wait(0.8)
    tl.to(1.0, in_out, queue_u=1.0)
    tl.also(0.6, back, sv_awake=1.0)
    tl.to(0.3, queue_a=0.0)
    say("accept returns only connections whose handshake the kernel has completed.", "insight")
    tl.wait(3.2)

    # ---- the echo
    tl.chapter("echo")
    say("The server loops into read and blocks. The client's write_all sends 10 bytes as one "
        "segment, seq 1001.")
    tl.to(0.4, sv_code=2.0)
    tl.also(0.6, sv_awake=0.0)
    tl.to(0.4, cl_code=1.0)
    send("data", "seq 1001  10 bytes", 1, MSG)
    tl.to(0.8, sv_recv=10.0)
    say("read returns 10, every byte that has arrived. TCP keeps no message boundaries: it "
        "could have been 4, then 6.")
    tl.to(0.5, back, sv_awake=1.0)
    flash_read("read -> 10")
    tl.to(0.7, sv_recv=0.0)
    tl.wait(1.2)
    say("write_all sends the same 10 bytes back. The segment also acknowledges the client's "
        "bytes: ack 1011.")
    tl.to(0.3, read_a=0.0)
    tl.to(0.4, sv_code=4.0)
    send("data", "seq 5001  ack 1011", -1, MSG)
    tl.to(0.8, cl_recv=10.0)
    say("The echo sits in the client's receive buffer. The server loops back to read and "
        "blocks again.")
    tl.to(0.4, sv_code=2.0)
    tl.to(0.6, sv_awake=0.0)
    tl.wait(1.6)

    # ---- the close
    tl.chapter("close")
    say("shutdown(Write) sends FIN: the client will send no more bytes. It can still read, "
        "so read_to_end blocks.")
    tl.to(0.4, cl_code=2.0)
    tl.set(cl_state="FIN-WAIT")
    send("FIN", "seq 1011", 1)
    tl.to(0.4, cl_code=3.0)
    tl.also(0.6, cl_awake=0.0)
    tl.set(sv_state="CLOSE-WAIT")
    say("The server's read returns 0. That is the FIN, an orderly close, so the handler "
        "returns and drops the stream.")
    tl.to(0.5, back, sv_awake=1.0)
    flash_read("read -> 0")
    tl.to(0.4, sv_code=3.0)
    tl.wait(1.4)
    say("Dropping the stream sends the server's own FIN.")
    tl.to(0.3, read_a=0.0)
    tl.set(sv_state="LAST-ACK")
    tl.to(0.4, sv_code=-1.0, sv_awake=0.0)
    send("FIN+ACK", "seq 5011  ack 1012", -1)
    say("read_to_end sees that FIN and returns the 10 echoed bytes. The client's last ACK "
        "closes the server side.")
    tl.set(cl_state="TIME-WAIT")
    tl.to(0.5, back, cl_awake=1.0, echoed_a=1.0, cl_recv=0.0)
    send("ACK", "ack 5012", 1, dur=1.2)
    tl.set(sv_state="CLOSED")
    say("Each direction closes separately. FIN means this side sends no more bytes; it can still read.", "insight")
    tl.wait(3.4)

    # ---- the hang: no shutdown
    tl.chapter("no FIN")
    tl.to(0.9, cl_state="ESTABLISHED", sv_state="ESTABLISHED", echoed_a=0.0, cl_recv=10.0,
          bug=1.0, cl_code=1.0, sv_code=2.0, sv_awake=0.0)
    say("Now delete the shutdown line, and run the test again up to the echo.", "fail")
    tl.wait(2.6)
    say("The client goes straight to read_to_end, which waits for the server to close. The "
        "server waits in read.", "fail")
    tl.to(0.4, cl_code=3.0)
    tl.to(0.6, cl_awake=0.0)
    tl.wait(1.6)
    say("No FIN is ever sent, so neither read returns. The test hangs, with no error.",
        "fail")
    tl.to(0.4, verdict=1.0)
    for label in ("1 s", "10 s", "1 min", "forever"):
        tl.set(clock=label)
        tl.wait(0.9)
    tl.wait(1.8)

    def draw(p, s, total):
        t = s.t
        title_block(p, "A TCP connection, from connect to close",
                    "The echo server's test, one segment at a time. Sequence numbers count "
                    "bytes.")

        # the wire
        p.rect(WIRE_A - 18, WIRE_Y - 3, WIRE_B - WIRE_A + 36, 6, "#e6ebf0", "none", 3)
        for x in (WIRE_A - 22, WIRE_B + 22):
            p.circle(x, WIRE_Y, 6, PAPER, FAINT, 1.6)
        p.text((WIRE_A + WIRE_B) / 2, WIRE_Y + 92, "the network", 11, FAINT, 600, "middle")

        # the two ends
        for x, name, sub, awake, state in ((CL_X, "client", "the test", s.cl_awake, s.cl_state),
                                           (SV_X, "server", "handle_connection", s.sv_awake,
                                            s.sv_state)):
            robot(p, x, DESK, TEAL if name == "server" else "#3b7dd8", awake, awake, name, sub,
                  look=0.8 if name == "client" else -0.8)
            zzz(p, x + 44, DESK - 108, t, 1 - awake)
            good = state in ("ESTABLISHED",)
            closing = state in ("FIN-WAIT", "CLOSE-WAIT", "LAST-ACK", "TIME-WAIT", "CLOSED")
            col = TEAL if good else (RUST if closing else MUTED)
            chip(p, x, 96, state, col, mix(PAPER, TEAL_LT if good else RUST_LT if closing
                                           else STAGE, 1.0), 12)

        # kernels
        kx = [(26, CL_X), (574, SV_X)]
        for (x, _), side in zip(kx, ("client", "server")):
            focus_on = side == "server" and s.kernel_focus > 0.01
            p.rect(x, 294, 220, 64, "#fbfcfd", mix(LINE, BRASS, s.kernel_focus if focus_on
                                                   else 0.0), 8, 1.3)
            if focus_on and s.kernel_focus > 0.5:
                p.text(x + 10, 309, "the server's kernel does the handshake", 10.5, BRASS, 700)
            else:
                p.text(x + 10, 309, "%s kernel" % side, 10.5, MUTED, 600)
        byte_row(p, 36, 330, int(round(s.cl_recv)), "recv buffer")
        byte_row(p, 584, 330, int(round(s.sv_recv)), "recv buffer")
        if s.kernel_focus <= 0.5:
            p.text(700, 309, "accept queue", 10.5, MUTED, 600)
            p.rect(772, 298, 16, 14, "none", LINE, 3, 1.1, dash="2 2")
        if s.queue_a > 0.01:
            qx = lerp(780, SV_X - 34, s.queue_u)
            qy = lerp(305, DESK - 64, s.queue_u)
            with p.group(opacity=clamp(s.queue_a)):
                chip(p, qx, qy, "conn", TEAL, TEAL_LT, 10.5)

        # the segment in flight
        if s.seg_a > 0.01:
            a, b = (WIRE_A, WIRE_B) if s.seg_dir > 0 else (WIRE_B, WIRE_A)
            x = lerp(a, b, s.seg_u)
            segment(p, x, WIRE_Y - 34 if s.seg_dir > 0 else WIRE_Y + 4 + 30, s.seg_flag,
                    s.seg_detail, SEG_COLORS[s.seg_flag], s.seg_payload, s.seg_a)
            p.line(x, WIRE_Y - 6, x, WIRE_Y + 6, SEG_COLORS[s.seg_flag], 3, opacity=s.seg_a)

        # what the reads returned
        if s.read_a > 0.01:
            zero = s.read_label.endswith("0") and not s.read_label.endswith("10")
            pill(p, SV_X - 130, WIRE_Y + 48, s.read_label, RUST if zero else BRASS,
                 RUST_LT if zero else BRASS_LT, 12.5, opacity=clamp(s.read_a), shadow=None)
        if s.echoed_a > 0.01:
            pill(p, CL_X + 150, WIRE_Y + 48, 'echoed = "%s"' % MSG, TEAL, TEAL_LT, 12,
                 opacity=clamp(s.echoed_a), shadow=None)
        if s.verdict > 0.01:
            with p.group(opacity=s.verdict):
                chip(p, (WIRE_A + WIRE_B) / 2, WIRE_Y - 40, "both blocked: " + (s.clock or ""),
                     RUST, RUST_LT, 13)

        CLIENT.draw(p, 26, 372, 390, "client (the test)", s, t, track="cl_code",
                    strike=2.0 if s.bug > 0.5 else None, size=10.2, lead=13.6, tint="#3b7dd8")
        SERVER.draw(p, 428, 372, 366, "server: accept, then handle_connection", s, t,
                    track="sv_code", size=10.2, lead=13.6)
        caption(p, tl, t, CAP)
        progress(p, tl, t, total, RAIL)

    CAP, RAIL, height = layout(372, max(len(CLIENT), len(SERVER)), 13.6)
    return tl, draw, height


# ------------------------------------ 20.2: the bandwidth-delay product

RTT = 4.0                 # one round trip, in animation seconds
SLOTS16 = 16              # packets the link holds in one round trip: the product
GAP = RTT / SLOTS16       # the link sends one packet every GAP seconds at full rate
PIPE_A, PIPE_B = 176, 644
FWD_Y, BACK_Y = 156, 204


def schedule(window, horizon):
    """Send times for a sender limited to `window` unacknowledged packets."""
    sends = []
    t = 0.0
    while t < horizon:
        i = len(sends)
        t = 0.0 if i == 0 else sends[-1] + GAP
        if i >= window:
            t = max(t, sends[i - window] + RTT)
        sends.append(t)
    return sends


def bdp():
    tl = Timeline(caption="", kind="step", window=4, t0=0.0, pipe_a=1.0, numbers=0.0)

    def say(text, kind="step"):
        tl.say(text, kind)

    def phase(window, label):
        tl.to(0.4, pipe_a=0.0)
        tl.chapter(label)
        tl.set(window=window, t0=tl.now)
        tl.to(0.3, pipe_a=1.0)

    tl.set(t0=-0.01)
    tl.chapter("window 4")
    say("The link carries one packet per tick, and a round trip takes 16 ticks. The sender "
        "may have 4 packets unacknowledged.")
    tl.wait(1.6)
    say("It sends 4 back to back. Then the window is full, and it must stop.")
    tl.wait(2.4)
    say("Nothing new can leave until an ACK returns, so most of the link is idle.")
    tl.wait(3.4)
    say("Each ACK frees one slot, and one more packet leaves. 4 packets per round trip: the "
        "link is busy a quarter of the time.", "insight")
    tl.wait(5.0)

    phase(16, "window 16")
    say("Now the window equals the bandwidth-delay product: 16 packets.")
    tl.wait(3.8)
    say("The first ACK returns as the 16th packet leaves, so the sender never stops.")
    tl.wait(3.0)
    say("The link is always busy, and the throughput is four times higher on the same link.",
        "insight")
    tl.wait(5.0)

    phase(1, "real numbers")
    say("On a 1 GB/s link with a 100 ms round trip, the product is 100 MB in flight.", "fail")
    tl.to(0.5, numbers=1.0)
    tl.wait(3.0)
    say("A 64 KB window fills 0.064% of that pipe. Throughput is window / RTT, 640 KB/s, no "
        "matter how fast the link is.", "fail")
    tl.wait(6.0)

    def draw(p, s, total):
        t = s.t
        title_block(p, "A small window leaves a long link idle",
                    "In-flight bytes are capped by the window. Filling the link takes "
                    "bandwidth x round-trip time.")
        window = int(s.window)
        local = t - s.t0
        planned = schedule(window, local + RTT)
        sends = [x for x in planned if x <= local]
        upcoming = [x for x in planned if x > local]
        in_flight = [x for x in sends if local - x < RTT]
        acked = len(sends) - len(in_flight)

        # the two actors
        robot(p, 84, 252, "#3b7dd8", 1.0, 1.0, "sender", "window = %d" % window, look=0.8)
        robot(p, 736, 252, TEAL, 1.0, 1.0, "receiver", "ACKs each packet", look=-0.8)
        # Blocked means the next packet is held back by the window, not by the link.
        blocked = bool(upcoming) and bool(sends) and upcoming[0] - sends[-1] > GAP * 1.05 \
            and local - sends[-1] > GAP * 0.5
        if blocked:
            chip(p, 92, 322, "window full: waiting", RUST, RUST_LT, 11.5)

        # the link: a data lane and an ACK lane
        for y, label in ((FWD_Y, "data"), (BACK_Y, "ACKs")):
            p.rect(PIPE_A - 10, y - 15, PIPE_B - PIPE_A + 20, 30, "#f1f4f7", LINE, 15, 1.2)
            p.text(PIPE_A - 18, y + 4, label, 10.5, MUTED, 600, "end")
        p.text((PIPE_A + PIPE_B) / 2, BACK_Y + 34, "one way = half a round trip", 10.5,
               FAINT, 600, "middle")

        with p.group(opacity=s.pipe_a):
            for i, sent in enumerate(sends):
                age = local - sent
                if age < RTT / 2:
                    x = lerp(PIPE_A + 12, PIPE_B - 12, age / (RTT / 2))
                    p.rect(x - 11, FWD_Y - 9, 22, 18, BRASS, "none", 4)
                    p.text(x, FWD_Y + 4.5, str(i % 100), 9.5, PAPER, 700, "middle", mono=True)
                elif age < RTT:
                    x = lerp(PIPE_B - 12, PIPE_A + 12, (age - RTT / 2) / (RTT / 2))
                    p.rect(x - 8, BACK_Y - 6, 16, 12, TEAL, "none", 3)

        # the gauge: the sixteen packets the link could hold
        gx, gy, cw = 250, 100, 20
        p.text(gx - 10, gy + 12, "in flight", 11, MUTED, 600, "end")
        for i in range(SLOTS16):
            full = i < len(in_flight)
            inside = i < window
            p.rect(gx + i * cw, gy, cw - 3, 16, BRASS if full else PAPER,
                   BRASS if inside else LINE, 3, 1.2, dash=None if inside else "2 2")
        p.text(gx + SLOTS16 * cw + 6, gy + 12, "%d / %d" % (len(in_flight), SLOTS16), 11.5,
               INK, 700, mono=True)

        busy = min(window, SLOTS16) / float(SLOTS16)
        scoreboard(p, [("link busy", "%d%%" % round(busy * 100), TEAL if busy > 0.99 else RUST),
                       ("per round trip", "%d packet%s" % (min(window, SLOTS16),
                                                         "" if window == 1 else "s"), INK)], y=348)
        p.text(26, 348, "effective window = min(receive window, congestion window)", 11.5,
               MUTED, 400, mono=True)

        if s.numbers > 0.01:
            with p.group(opacity=s.numbers):
                p.rect(236, 286, 348, 44, SCREEN, "none", 8)
                p.text(410, 304, "1 GB/s x 100 ms = 100,000,000 B in flight", 11.5, "#e8eef3", 600,
                       "middle", mono=True)
                p.text(410, 321, "64,000 B / 100 ms = 640 KB/s", 11.5, "#f3c38a", 700, "middle",
                       mono=True)

        caption(p, tl, t, 366)
        progress(p, tl, t, total, 452)

    return tl, draw, 486


# ----------------------------------------------------- 20.4: the epoll loop

LOOP_X, LOOP_DESK = 104, 236
ROWS = {3: 110, 5: 164, 6: 218}     # fd -> row centre
PANEL_X = 236
LIGHT_X = 520
OUT_X, OUT_W = 598, 150
OUT_CAP = 12.0                        # KB the out bar can show

EVENT_LOOP = Panel("src/bin/epoll_echo.rs",
                   [("while !shutdown.load(Ordering::Relaxed) {", None),
                    ("let ready = unsafe {", "};"),
                    ("for event in &events[..ready as usize] {",
                     ("update_interest(epfd, fd, &mut connections)?;", 3))],
                   ["while !shutdown.load(Ordering::Relaxed) {", "libc::epoll_wait(",
                    "for event in &events[..ready as usize] {",
                    "accept_ready(epfd, listen_fd, &mut connections)?;",
                    "if readable && !read_into(fd, &mut connections)? {",
                    "flush(fd, &mut connections)?;",
                    "update_interest(epfd, fd, &mut connections)?;"])


def socket_row(p, fd, s, alpha=1.0):
    """One registered fd: its jack, its interest set, its readiness light, its out buffer."""
    if alpha <= 0.01:
        return
    y = ROWS[fd]
    with p.group(opacity=alpha, dx=(1 - alpha) * 30):
        focus_on = clamp(1 - abs(s.focus - fd) * 2) if s.focus > 0 else 0.0
        p.rect(PANEL_X, y - 22, W - 26 - PANEL_X, 44, mix(PAPER, BRASS_LT, focus_on),
               mix(LINE, BRASS, focus_on), 10, 1.3 + focus_on)
        # the jack
        p.rect(PANEL_X + 12, y - 13, 26, 26, SCREEN, "none", 6)
        p.rect(PANEL_X + 19, y - 5, 12, 10, "#0e151c", "none", 2)
        p.text(PANEL_X + 48, y - 2, "fd %d" % fd, 13, INK, 700, mono=True)
        p.text(PANEL_X + 48, y + 13, "listener" if fd == 3 else "client", 10.5, MUTED)
        # interest set
        interest = s["interest%d" % fd]
        out_on = "OUT" in interest
        chip(p, 400, y, interest, BRASS if out_on else TEAL, BRASS_LT if out_on else TEAL_LT,
             11)
        # readiness light
        light = s["light%d" % fd]
        if light > 0.01:
            p.circle(LIGHT_X, y, 15, GLOW, opacity=0.4 * light, filter="blur")
        p.circle(LIGHT_X, y, 7, mix("#cfd8e0", "#3cc9a4", light), mix(FAINT, TEAL, light), 1.4)
        label = s["kind%d" % fd] if light > 0.5 else "not ready"
        p.text(LIGHT_X + 14, y + (0 if s.ignored > 0.5 and fd in (3, 5) else 4), label, 11, TEAL if light > 0.5 else FAINT,
               700 if light > 0.5 else 400)
        if fd == 3:
            q = int(round(s.q3))
            if q:
                p.text(OUT_X, y + 4, "queued:", 11, MUTED)
                for i in range(q):
                    chip(p, OUT_X + 76 + i * 48, y, "conn", TEAL, TEAL_LT, 10)
        else:
            kb = s["out%d" % fd]
            p.text(OUT_X, y - 7, "out", 10.5, MUTED, 600, mono=True)
            p.rect(OUT_X + 28, y - 16, OUT_W - 28, 12, "#eef2f5", LINE, 3, 1)
            if kb > 0.05:
                p.rect(OUT_X + 28, y - 16, (OUT_W - 28) * clamp(kb / OUT_CAP), 12,
                       RUST if out_on else BRASS, "none", 3)
            p.text(OUT_X + 28, y + 12, "%.0f KB pending" % kb if kb >= 0.5 else "empty", 10.5,
                   RUST if kb >= 0.5 else FAINT, 600)


def epoll():
    tl = Timeline(caption="", kind="step", awake=0.0, code=1.0, focus=0.0,
                  interest3="IN", interest5="IN", interest6="IN",
                  light3=0.0, light5=0.0, light6=0.0,
                  kind3="readable", kind5="readable", kind6="readable",
                  q3=0.0, row5=0.0, row6=0.0, out5=0.0, out6=0.0,
                  tag_u=0.0, tag_a=0.0, tag_label="", tag_fd=3, events="",
                  eagain_a=0.0, eagain_fd=3, arr_u=0.0, arr_a=0.0, arr_fd=5, arr_label="",
                  stuck=0.0, clock="", ignored=0.0)

    def say(text, kind="step"):
        tl.say(text, kind)

    def arrive(fd, label, dur=0.9):
        tl.set(arr_fd=fd, arr_label=label, arr_u=0.0)
        tl.to(0.2, arr_a=1.0)
        tl.to(dur, in_out, arr_u=1.0)
        tl.to(0.15, arr_a=0.0)

    def hand_over(fd, label):
        """epoll_wait returns: an event tag flies from the socket to the thread."""
        tl.set(tag_fd=fd, tag_label=label, tag_u=0.0)
        tl.to(0.2, tag_a=1.0)
        tl.to(0.8, in_out, tag_u=1.0)
        tl.to(0.15, tag_a=0.0)

    def eagain(fd):
        tl.set(eagain_fd=fd)
        tl.to(0.3, back, eagain_a=1.0)
        tl.wait(0.8)
        tl.to(0.3, eagain_a=0.0)

    tl.chapter("wait")
    say("The loop registered the listener, fd 3, for EPOLLIN, and sleeps in epoll_wait. It "
        "uses no CPU while nothing is ready.")
    tl.wait(3.6)

    tl.chapter("accept")
    say("Two clients connect. The kernel queues both, and marks the listener readable.")
    tl.to(0.6, q3=1.0)
    tl.to(0.6, q3=2.0, light3=1.0)
    tl.wait(0.4)
    say("epoll_wait returns one event: fd 3 is readable. The thread wakes.")
    hand_over(3, "fd 3 IN")
    tl.set(events="fd 3 IN")
    tl.to(0.6, back, awake=1.0, code=3.0, focus=3.0)
    say("accept_ready calls accept4 until EAGAIN. Two connections become fd 5 and fd 6, "
        "registered for EPOLLIN.")
    tl.to(0.7, back, row5=1.0, q3=1.0)
    tl.to(0.7, back, row6=1.0, q3=0.0, light3=0.0)
    eagain(3)
    tl.to(0.5, code=1.0, focus=0.0, events="")
    tl.to(0.6, awake=0.0)

    tl.chapter("read")
    say("Both clients send. fd 5 sends 1 KB, and fd 6 sends 12 KB. Both become readable.")
    arrive(5, "1 KB")
    tl.to(0.3, light5=1.0)
    arrive(6, "12 KB")
    tl.to(0.3, light6=1.0)
    say("epoll_wait returns both events in one batch, and the thread handles them in order.")
    hand_over(5, "fd 5 IN")
    tl.set(events="fd 5 IN")
    hand_over(6, "fd 6 IN")
    tl.set(events="fd 5 IN, fd 6 IN")
    tl.to(0.6, back, awake=1.0, code=4.0, focus=5.0)
    say("fd 5: read until EAGAIN puts 1 KB in out, and flush writes all of it.")
    tl.to(0.5, out5=1.0, light5=0.0)
    tl.wait(0.5)
    tl.to(0.6, out5=0.0)
    tl.to(0.3, code=6.0)
    tl.wait(0.8)
    say("fd 6: read puts 12 KB in out. flush writes 8 KB, then write returns EAGAIN: the "
        "client is not reading.")
    tl.to(0.5, code=4.0, focus=6.0)
    tl.to(0.6, out6=12.0, light6=0.0)
    tl.wait(0.4)
    tl.to(0.9, out6=4.0)
    eagain(6)
    say("The last 4 KB stays in out, and update_interest adds EPOLLOUT. The thread moves on.")
    tl.to(0.4, code=6.0)
    tl.to(0.5, back, interest6="IN|OUT")
    tl.wait(1.4)
    tl.to(0.5, code=1.0, focus=0.0, events="")
    tl.to(0.6, awake=0.0)
    say("The slow client costs memory in its out buffer. The thread keeps serving the other sockets.",
        "insight")
    tl.wait(3.4)

    tl.chapter("writable")
    say("fd 6's client reads, so its socket has room again. epoll reports fd 6 writable.")
    tl.set(kind6="writable")
    tl.to(0.5, light6=1.0)
    hand_over(6, "fd 6 OUT")
    tl.set(events="fd 6 OUT")
    tl.to(0.6, back, awake=1.0, code=5.0, focus=6.0)
    say("flush writes the last 4 KB. out is empty, so update_interest turns EPOLLOUT off.")
    tl.to(0.8, out6=0.0, light6=0.0)
    tl.to(0.3, code=6.0)
    tl.to(0.5, back, interest6="IN")
    tl.wait(1.2)
    tl.to(0.5, code=1.0, focus=0.0, events="")
    tl.to(0.6, awake=0.0)
    tl.wait(0.8)

    tl.chapter("blocking fd")
    say("Now suppose fd 6 were a blocking socket, and its client stopped reading again.",
        "fail")
    tl.set(kind6="readable")
    arrive(6, "12 KB")
    tl.to(0.3, light6=1.0)
    hand_over(6, "fd 6 IN")
    tl.to(0.6, back, awake=1.0, code=4.0, focus=6.0, out6=12.0, light6=0.0)
    tl.to(0.9, out6=4.0)
    say("write blocks with 4 KB left, and the only thread stops inside it.", "fail")
    tl.to(0.4, stuck=1.0)
    tl.wait(1.0)
    say("fd 5 sends again and a new client connects. Both are ready, and nobody serves them.",
        "fail")
    arrive(5, "1 KB", dur=0.7)
    tl.to(0.3, light5=1.0)
    tl.to(0.5, q3=1.0, light3=1.0, ignored=1.0)
    for label in ("1 s", "10 s", "1 min"):
        tl.set(clock=label)
        tl.wait(0.9)
    say("On a non-blocking socket, write returns EAGAIN instead, and the loop moves on.",
        "fail")
    tl.wait(3.4)

    def draw(p, s, total):
        t = s.t
        title_block(p, "One thread, many sockets: the epoll loop",
                    "The thread sleeps in epoll_wait. The kernel wakes it with a list of "
                    "sockets that are ready.")
        robot(p, LOOP_X, LOOP_DESK, TEAL, s.awake, s.awake, "event loop", "one thread",
              look=0.9)
        zzz(p, LOOP_X + 44, LOOP_DESK - 108, t, 1 - s.awake)
        if s.stuck > 0.01:
            with p.group(opacity=s.stuck):
                chip(p, LOOP_X, LOOP_DESK - 150, "stuck in write(fd 6)", RUST, RUST_LT, 11.5)
                if s.clock:
                    p.text(LOOP_X, LOOP_DESK + 72, "waiting " + s.clock, 12, RUST, 700,
                           "middle", mono=True)

        p.text(PANEL_X, 76, "registered with epoll", 11, MUTED, 600)
        p.text(400, 76, "interest", 11, MUTED, 600, "middle")
        p.text(LIGHT_X - 8, 76, "ready?", 11, MUTED, 600)
        socket_row(p, 3, s)
        socket_row(p, 5, s, clamp(s.row5))
        socket_row(p, 6, s, clamp(s.row6))
        if s.ignored > 0.01:
            with p.group(opacity=s.ignored):
                for fd in (3, 5):
                    p.text(LIGHT_X + 14, ROWS[fd] + 18, "ignored", 10, RUST, 700)

        # data arriving from the network, into a socket
        if s.arr_a > 0.01:
            y = ROWS[s.arr_fd]
            x = lerp(W - 10, LIGHT_X + 110, s.arr_u)
            pill(p, x, y + 30, s.arr_label, BRASS, BRASS_LT, 11, opacity=s.arr_a, shadow=None)
        # an event handed to the thread
        if s.tag_a > 0.01:
            a = (LIGHT_X - 20, ROWS[s.tag_fd])
            b = (LOOP_X + 40, LOOP_DESK - 150)
            x, y = bezier(a, ((a[0] + b[0]) / 2, 40), b, s.tag_u)
            pill(p, x, y, s.tag_label, TEAL, PAPER, 11.5, opacity=s.tag_a)
        if s.eagain_a > 0.01:
            pill(p, LIGHT_X - 40, ROWS[s.eagain_fd] - 30, "EAGAIN", RUST, RUST_LT, 11,
                 opacity=clamp(s.eagain_a), shadow=None)
        if s.stuck < 0.5:
            p.text(26, 322, "events:", 11.5, MUTED, 600)
        if s.events:
            p.text(84, 322, "[" + s.events + "]", 11.5, TEAL, 700, mono=True)

        EVENT_LOOP.draw(p, 26, 336, W - 52, "event_loop", s, t, size=10.0, lead=12.6)
        caption(p, tl, t, CAP)
        progress(p, tl, t, total, RAIL)

    CAP, RAIL, height = layout(336, len(EVENT_LOOP), 12.6)
    return tl, draw, height


def build_tcp_handshake(only=None):
    tl, draw, height = tcp_handshake()
    return render("ch20-tcp-handshake.gif", tl, draw, height, only=only,
                  extra_colors=("#3b7dd8",))


def build_bdp(only=None):
    tl, draw, height = bdp()
    return render("ch20-bdp.gif", tl, draw, height, only=only, extra_colors=("#3b7dd8",))


def build_epoll(only=None):
    tl, draw, height = epoll()
    return render("ch20-epoll.gif", tl, draw, height, only=only, extra_colors=("#3cc9a4",))


BUILDERS = {
    "tcp-handshake": build_tcp_handshake,
    "bdp": build_bdp,
    "epoll": build_epoll,
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
