#!/usr/bin/env python3
"""The book's system diagrams, written to src/figures/ as SVG.

    python3 tools/draw_figures.py                  # every figure
    python3 tools/draw_figures.py lease-roles      # some of them

Each function draws one figure with `figkit`, the drawing kit of the Thor
Thunder Tigress book. figkit refuses to write a figure in which a label is
wider than its box or a wire runs at an angle, so a figure that is written has
passed both checks.
"""
import sys
from pathlib import Path

from figkit import (CARD, EDGE, INK, KINDS, MUTED, card, cylinder, legend, save, sheet, tag, text,
                    width_of, wire, zone)

OUT = Path(__file__).resolve().parent.parent / "src" / "figures"
FIGURES = {}


def figure(draw):
    """Registers `draw` under its name, with underscores written as hyphens."""
    FIGURES[draw.__name__.replace("_", "-")] = draw
    return draw


def lines(x, y, rows, cls="note", anchor="start", lead=17):
    """Plain lines of text, one under the other."""
    return "\n".join(text(x, y + lead * row, body, cls, anchor) for row, body in enumerate(rows))


def box(x, y, w, h, fill, stroke=EDGE, rx=8, width=1.3, dash=None):
    """A plain rectangle, for the pictures figkit has no part for."""
    dashed = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'  <rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}"'
            f' stroke="{stroke}" stroke-width="{width}"{dashed}/>')


@figure
def gpu_request():
    parts = [
        sheet(32, 112, 236, 150, "client", "A POD", [
            ("", "resources:"), ("", "  limits:"), ("strong", "    nvidia.com/gpu: 1")],
            footer=["asks for one unit of GPU"]),
        card(338, 152, 250, 70, "service", "Scheduler", ["picks a machine that", "advertises a free unit"], glyph="search"),
        wire([(268, 187), (338, 187)]),

        zone(660, 104, 436, 316, "a machine with a GPU"),
        card(684, 152, 388, 70, "service", "kubelet", ["the Kubernetes agent on the machine;", "starts the pod's containers"], glyph="gear"),
        wire([(588, 187), (684, 187)], label="pod"),
        card(684, 250, 184, 70, "outside", "Device plugin", ["counts the GPUs"], glyph="nvidia"),
        card(888, 250, 184, 70, "outside", "GPU runtime", ["opens the GPU", "to a container"], glyph="nvidia"),
        wire([(776, 250), (776, 222)]),
        wire([(980, 222), (980, 250)]),
        card(684, 346, 388, 56, "model", "The GPU", ["device files and the driver's libraries"], glyph="chip"),
        wire([(980, 320), (980, 346)]),
        lines(32, 300, ["The device plugin reports the count, so the", "machine advertises nvidia.com/gpu.",
                        "", "The container runtime adds the GPU's device", "files and driver libraries to the container",
                        "just before it starts."]),
    ]
    save(OUT / "gpu-request.svg", 1128, 444,
         "A pod whose limits ask for nvidia.com/gpu: 1 goes to the scheduler, which picks a machine that "
         "advertises a free unit. On that machine the kubelet starts the pod's containers. The device "
         "plugin counts the GPUs and reports the count to the kubelet. The GPU-aware container runtime "
         "adds the GPU's device files and driver libraries to the container.",
         "From a request for one GPU to a container that can use it",
         "Two pieces from the GPU vendor sit beside the kubelet: the device plugin and the container runtime.", parts)


@figure
def informer_pipeline():
    parts = [
        card(32, 120, 230, 64, "service", "API server", ["numbers every write"], glyph="gear"),
        cylinder(62, 250, 170, 92, "store", "etcd", ["objects, by revision"]),
        wire([(120, 184), (120, 250)]),

        zone(350, 96, 668, 256, "the controller's process"),
        card(380, 120, 230, 64, "service", "Reflector", ["list, then watch"], glyph="swap"),
        wire([(262, 152), (380, 152)], label="events"),
        cylinder(730, 106, 170, 92, "store", "Cache", ["a copy of every object"]),
        wire([(610, 152), (730, 152)], label="1 apply"),
        card(380, 262, 230, 64, "store", "Work queue", ["names of changed objects"], glyph="stack"),
        wire([(495, 184), (495, 262)], label="2 add name"),
        card(730, 262, 258, 64, "service", "Controller", ["reconcile(name)"], glyph="gear"),
        wire([(610, 294), (730, 294)], label="Get"),
        wire([(815, 262), (815, 198)], label="read"),
        wire([(900, 326), (900, 400), (200, 400), (200, 184)],
             label="write the status with the version that was read"),
    ]
    save(OUT / "informer-pipeline.svg", 1050, 440,
         "The API server numbers every write and stores objects in etcd. Inside the controller's process, "
         "the reflector lists and then watches, applies each event to the cache first, and then adds the "
         "object's name to the work queue. The controller gets a name from the queue, reads the object from "
         "the cache, and writes the status back to the API server with the version it read.",
         "The parts of the model, and the order in which a change passes through them",
         "The reflector updates the cache before it queues the name, so a worker reads the new state.", parts)


@figure
def gpujob_controller():
    parts = [
        sheet(32, 112, 226, 190, "client", "GPUJOB train", [
            ("", "spec:"), ("", "  image: gpu-check:1"), ("strong", "  gpus: 1"),
            ("dim", "status:"), ("dim", "  phase: Running"), ("dim", "  observedGeneration: 1")],
            footer=["kubectl apply"]),
        card(338, 120, 260, 70, "service", "API server", ["serves gpujobs.gpucloud.dev", "once the CRD is installed"], glyph="gear"),
        wire([(258, 155), (338, 155)]),
        card(338, 300, 260, 70, "service", "gpujob-controller", ["queues a job when the job", "or the pod it owns changes"], glyph="gear"),
        wire([(420, 190), (420, 300)], label="watch"),
        wire([(540, 300), (540, 190)], label="/status"),

        sheet(690, 112, 226, 150, "service", "POD train", [
            ("", "ownerReferences:"), ("", "  GpuJob/train"), ("strong", "nvidia.com/gpu: 1")],
            footer=["applied on every reconcile"]),
        wire([(598, 335), (640, 335), (640, 187), (690, 187)], label="apply", on=1),
        card(690, 300, 226, 70, "service", "Scheduler, kubelet", ["place the pod and", "start its container"]),
        wire([(803, 262), (803, 300)]),
        card(956, 300, 150, 70, "model", "GPU", ["gpu-check", "adds two vectors"]),
        wire([(916, 335), (956, 335)]),
        lines(956, 140, ["The pod's owner", "reference names", "the job, so a pod", "event queues", "its job."]),
    ]
    save(OUT / "gpujob-controller.svg", 1138, 410,
         "A GpuJob named train, with image gpu-check:1 and gpus 1, is applied with kubectl to the API "
         "server, which serves the gpujobs.gpucloud.dev kind once the CRD is installed. The "
         "gpujob-controller watches jobs and the pods they own. On each reconcile it applies a pod named "
         "train, whose owner reference names the job and whose limits ask for nvidia.com/gpu: 1, and it "
         "writes the job's phase through the status subresource. The scheduler and the kubelet place and "
         "start the pod, and its program runs on the GPU.",
         "One GpuJob, the pod the controller keeps for it, and the two writes of a reconcile",
         "The controller applies the pod and writes the job's status. Every other arrow is Kubernetes at work.", parts)


@figure
def gpu_anatomy():
    green, tint = KINDS["model"]
    parts = [zone(32, 104, 700, 300, "the Orin's GPU, as gpu_info reports it")]
    for k in range(8):
        x, y = 56 + (k % 4) * 166, 132 + (k // 4) * 84
        parts += [box(x, y, 150, 68, CARD, EDGE, 10),
                  text(x + 12, y + 20, "SM %d" % k, "pill", fill=green)]
        parts += [box(x + 12 + col * 11, y + 28 + row * 11, 8, 8, tint, green, 2, 0.8)
                  for row in range(3) for col in range(8)]
        parts.append(box(x + 106, y + 28, 32, 30, KINDS["store"][1], KINDS["store"][0], 4, 0.9))
    parts += [
        box(56, 306, 652, 30, KINDS["store"][1], KINDS["store"][0], 8),
        text(382, 326, "L2 cache, 2,048 KiB, shared by all eight SMs", "pill", "middle", KINDS["store"][0]),
        box(56, 348, 652, 38, KINDS["client"][1], KINDS["client"][0], 8),
        text(382, 372, "device memory: the board's 15.3 GiB of LPDDR5, shared with the CPU", "pill", "middle", KINDS["client"][0]),

        card(772, 120, 260, 64, "model", "One SM", ["128 CUDA cores, Tensor Cores"], glyph="chip"),
        lines(784, 208, ["holds 1,536 threads at once,", "in warps of 32", "",
                         "65,536 registers", "", "164 KiB of shared memory", "and L1 cache (the amber block)"]),
        card(772, 340, 260, 64, "outside", "2 copy engines", ["move data while kernels run"], glyph="swap"),
    ]
    save(OUT / "gpu-anatomy.svg", 1064, 428,
         "The GPU of the Jetson Orin NX drawn from the output of gpu_info: eight streaming multiprocessors, "
         "each with 128 CUDA cores, room for 1,536 resident threads, 65,536 registers and 164 KiB of shared "
         "memory and L1 cache. All eight share a 2,048 KiB L2 cache. Device memory is the board's 15.3 GiB "
         "of LPDDR5, which the CPU also uses. Two copy engines move data while kernels run.",
         "What one nvidia.com/gpu unit contains on our cluster",
         "Eight streaming multiprocessors, one L2 cache, and memory that the CPU uses too.", parts)


@figure
def gpu_sharing():
    pods = [("A", KINDS["client"][0]), ("B", KINDS["store"][0]), ("C", KINDS["outside"][0])]
    panels = [
        ("Whole GPU", "one pod holds the device", ("yes", "yes")),
        ("Time-slicing", "pods take turns on all SMs", ("no", "no")),
        ("MPS", "kernels run side by side", ("by limits", "partly")),
        ("MIG", "hardware partitions", ("yes", "yes")),
    ]
    parts = []
    for k, (name, sub, (memory, faults)) in enumerate(panels):
        x = 32 + k * 262
        gx, gy, gw, gh = x + 34, 150, 196, 132
        parts += [text(x, 112, name, "name"), text(x, 130, sub, "sub"),
                  box(gx, gy, gw, gh, "#F1F4F7", EDGE, 6),
                  text(gx - 8, gy + gh / 2 + 4, "SMs", "note", "end"),
                  text(gx + gw / 2, gy + gh + 18, "time", "note", "middle")]
        if k == 0:
            cells = [(0, 0, gw, gh, 0)]
        elif k == 1:
            cells = [(col * gw / 6, 0, gw / 6, gh, col % 3) for col in range(6)]
        elif k == 2:
            cells = [(0, 0, gw, gh * 0.5, 0), (0, gh * 0.5, gw, gh * 0.3, 1), (0, gh * 0.8, gw, gh * 0.2, 2)]
        else:
            cells = [(0, 0, gw, gh * 3 / 7, 0), (0, gh * 3 / 7, gw, gh * 2 / 7, 1), (0, gh * 5 / 7, gw, gh * 2 / 7, 2)]
        for cx, cy, cw, ch, who in cells:
            label, colour = pods[who]
            inset = 4 if k == 3 else 1.5
            parts += [f'  <rect x="{gx + cx + inset:.1f}" y="{gy + cy + inset:.1f}" width="{cw - 2 * inset:.1f}"'
                      f' height="{ch - 2 * inset:.1f}" rx="{5 if k == 3 else 3}" fill="{colour}" fill-opacity="0.82"/>',
                      text(gx + cx + cw / 2, gy + cy + ch / 2 + 4, label, "pill", "middle", "#FFFFFF")]
        if k == 2:
            parts += [f'  <path class="wire idle" d="M{gx},{gy + gh * share:.1f} H{gx + gw}"/>' for share in (0.5, 0.8)]
        if k == 3:
            parts += [f'  <path d="M{gx},{gy + gh * share:.1f} H{gx + gw}" stroke="{INK}" stroke-width="3"/>' for share in (3 / 7, 5 / 7)]
        for row, (what, answer) in enumerate((("memory isolated", memory), ("faults isolated", faults))):
            kind = {"yes": "good", "no": "danger"}.get(answer, "store")
            parts += [text(x, 332 + row * 26, what, "note"), tag(x + 230, 319 + row * 26, answer, kind, anchor="end")]
    parts.append(lines(32, 400, ["Each picture is one GPU: its SMs from top to bottom, and time from left to right. "
                                 "A colour is the pod whose kernels run there.",
                                 "MPS divides by limits that an administrator sets (dotted). "
                                 "MIG divides by hardware, memory and cache included (solid)."]))
    save(OUT / "gpu-sharing.svg", 1090, 440,
         "Four pictures of one GPU, with its SMs on the vertical axis and time on the horizontal axis. Whole "
         "GPU: pod A fills the picture; memory and faults are isolated. Time-slicing: pods A, B and C take "
         "turns in vertical stripes, each stripe covering every SM; neither memory nor faults are isolated. "
         "MPS: A, B and C run at the same time in horizontal bands separated by dotted lines; memory is "
         "isolated by limits and faults partly. MIG: A, B and C run in horizontal bands separated by solid "
         "walls; memory and faults are isolated.",
         "Four ways to hand out one GPU", "Whole, by turns, side by side, or cut into hardware partitions.", parts)


@figure
def liveness_registry():
    parts = [
        card(48, 136, 240, 64, "idle", "host 9999", ["one heartbeat a second"]),
        card(40, 128, 240, 64, "idle", "host 1", ["one heartbeat a second"]),
        card(32, 120, 240, 64, "client", "host 0", ["one heartbeat a second"], glyph="chip"),
        card(420, 112, 290, 80, "service", "Registry", ["last-seen time of every host,", "in memory; a sweep each second"], glyph="clock"),
        wire([(288, 152), (420, 152)], label="heartbeats"),
        cylinder(850, 106, 170, 92, "store", "Database", ["one state per host"]),
        wire([(710, 152), (850, 152)], label="changes"),
        text(354, 216, "599,956 in 60 s", "pill", "middle", MUTED),
        text(780, 216, "4 writes in 60 s", "pill", "middle", KINDS["store"][0]),

        card(120, 290, 190, 64, "good", "Up", ["heartbeats arrive"]),
        card(440, 290, 190, 64, "store", "Suspect", ["no new work placed"]),
        card(760, 290, 190, 64, "danger", "Dead", ["jobs restart elsewhere"]),
        wire([(310, 322), (440, 322)], label="3 s silent"),
        wire([(630, 322), (760, 322)], label="10 s silent"),
        wire([(535, 354), (535, 392), (215, 392), (215, 354)], label="a heartbeat"),
        wire([(855, 354), (855, 414), (165, 414), (165, 354)], label="a heartbeat"),
    ]
    save(OUT / "liveness-registry.svg", 1052, 446,
         "Ten thousand hosts each send one heartbeat a second to the registry, which keeps every host's "
         "last-seen time in memory and sweeps once a second. In the 60-second run it handles 599,956 "
         "heartbeats and writes to the database four times, once per change of state. A host is Up while "
         "heartbeats arrive, Suspect after 3 seconds of silence, and Dead after 10. A heartbeat from a "
         "Suspect or a Dead host returns it to Up.",
         "Heartbeats stay in memory; only a change of state reaches the database",
         "The sweep moves a silent host to the right. A heartbeat brings it back to Up.", parts)


@figure
def lease_roles():
    parts = [
        card(32, 120, 230, 60, "client", "leaseagent gpu-host-a", ["Go, client-go"]),
        card(32, 204, 230, 60, "client", "leaseagent gpu-host-b", ["Rust, kube-rs"]),
        card(32, 288, 230, 60, "client", "leaseagent gpu-host-c", ["Go, client-go"]),

        zone(360, 104, 310, 262, "API server, namespace fleet"),
        sheet(384, 132, 262, 212, "store", "LEASE gpu-host-b", [
            ("", "holderIdentity: gpu-host-b"), ("", "leaseDurationSeconds: 6"),
            ("strong", "renewTime: 01:31:24.5"), ("dim", "acquireTime: 01:31:16.5")],
            footer=["one Lease for each host;", "renewTime is the host's own clock"]),
        wire([(262, 150), (310, 150), (310, 222), (384, 222)], arrow=False),
        wire([(262, 318), (310, 318), (310, 250), (384, 250)], arrow=False),
        wire([(262, 236), (384, 236)], label="apply, 2 s"),

        card(770, 132, 290, 76, "service", "leasewatch", ["Go: informer cache and lister,", "read once a second"], glyph="eye"),
        card(770, 264, 290, 76, "service", "leasewatch", ["Rust: watcher stream and a store,", "read once a second"], glyph="eye"),
        wire([(670, 170), (770, 170)], label="watch"),
        wire([(670, 302), (770, 302)], label="watch"),
        lines(32, 402, ["A watcher notes its own clock when it sees renewTime change, and reports the host as expired when six "
                        "seconds pass on that clock with no change."]),
    ]
    save(OUT / "lease-roles.svg", 1092, 426,
         "Three lease agents, gpu-host-a and gpu-host-c written in Go and gpu-host-b written in Rust, each "
         "apply their own Lease in the fleet namespace every two seconds. The Lease for gpu-host-b holds "
         "holderIdentity gpu-host-b, leaseDurationSeconds 6, a renewTime written with the host's clock, and "
         "an acquireTime. Two watchers, one in Go with an informer cache and one in Rust with a watcher "
         "stream into a store, watch the Leases and check them once a second against their own clocks.",
         "Agents renew, watchers observe, and the Lease is the contract between them",
         "A Go watcher reads a Lease that a Rust agent wrote, and the other way round.", parts)


@figure
def gpu_container_path():
    parts = [
        sheet(32, 108, 220, 132, "client", "POD", [("", "limits:"), ("strong", "  nvidia.com/gpu: 1")],
              footer=["scheduled to this node"]),
        card(330, 120, 250, 70, "service", "kubelet", ["picks a free device ID,", "then builds the container"], glyph="gear"),
        wire([(252, 155), (330, 155)]),
        card(700, 120, 300, 70, "outside", "NVIDIA device plugin", ["gRPC on a Unix socket:", "Register, ListAndWatch, Allocate"], glyph="nvidia"),
        wire([(580, 140), (700, 140)], label="Allocate"),
        wire([(700, 172), (580, 172)], label="env var"),
        text(850, 212, "NVIDIA_VISIBLE_DEVICES=<device>", "mono", "middle"),

        card(330, 270, 250, 70, "service", "containerd", ["writes the OCI runtime", "specification"], glyph="doc"),
        wire([(455, 190), (455, 270)]),
        card(700, 270, 300, 86, "outside", "nvidia-container-runtime", ["sees the variable, reads the CSV", "lists, adds the device files and", "library mounts they name"], glyph="nvidia"),
        wire([(580, 305), (700, 305)], label="spec"),
        card(700, 420, 300, 60, "service", "runc", ["creates the container as written"], glyph="terminal"),
        wire([(850, 356), (850, 420)], label="edited spec"),
        card(330, 420, 250, 60, "model", "Container with a GPU", ["/dev/nvhost-gpu, libcuda.so"], glyph="chip"),
        wire([(700, 450), (580, 450)]),
        sheet(32, 300, 220, 180, "store", "CSV LISTS", [("", "dev, /dev/nvhost-gpu"), ("", "dev, /dev/nvmap"),
                                                     ("", "lib, .../libcuda.so.1.1"), ("", "sym, .../libcuda.so.1")],
              footer=["40 device lines,", "285 driver lines"]),
    ]
    save(OUT / "gpu-container-path.svg", 1032, 510,
         "A pod with a limit of nvidia.com/gpu: 1 reaches the kubelet on its node. The kubelet picks a free "
         "device ID and calls Allocate on the NVIDIA device plugin, which answers with the environment "
         "variable NVIDIA_VISIBLE_DEVICES. containerd writes the OCI runtime specification with that "
         "variable and hands it to nvidia-container-runtime. The runtime sees the variable, reads the CSV "
         "lists of device files, libraries and symbolic links, adds them to the specification, and calls "
         "runc with the edited document. runc creates a container that has /dev/nvhost-gpu and libcuda.so.",
         "The path of a GPU request on a Jetson node",
         "The device plugin sets one environment variable, and the runtime acts on it.", parts)


@figure
def fleet_map():
    parts = [
        zone(32, 104, 572, 300, "shelf: five Jetson AGX Thor"),
        card(52, 132, 532, 56, "outside", "25 GbE switch", ["one lane of 25 GbE to each Thor"], glyph="swap"),
    ]
    for k in range(5):
        x = 52 + k * 109
        parts += [card(x, 250, 96, 64, "model", "thor-%d" % (k + 1), ["128 GB"]),
                  wire([(x + 48, 250), (x + 48, 188)], arrow=False)]
    parts += [
        lines(52, 346, ["each: 14 cores, one GPU, 128 GB shared by CPU and GPU,", "273 GB/s of memory bandwidth, 40 to 130 W"]),
        zone(636, 104, 280, 300, "desk: two DGX Sparks"),
        card(656, 132, 240, 64, "model", "spark-1", ["20 cores, 128 GB"], glyph="nvidia"),
        card(656, 262, 240, 64, "model", "spark-2", ["20 cores, 128 GB"], glyph="nvidia"),
        wire([(776, 196), (776, 262)], label="200 GbE", arrow=False),
        lines(656, 356, ["each: 273 GB/s, about 170 W"]),
        zone(948, 104, 160, 300, "bench"),
        card(964, 132, 128, 96, "client", "orin-nx-1", ["8 cores", "16 GB", "10 to 40 W"]),
        lines(964, 262, ["102 GB/s,", "1 GbE.", "", "Every example", "so far ran", "here."]),
    ]
    save(OUT / "fleet-map.svg", 1140, 428,
         "Eight machines in three groups. Five Jetson AGX Thor developer kits, thor-1 to thor-5, connect to one "
         "25 GbE switch. Two DGX Sparks, spark-1 and spark-2, are joined by a 200 GbE cable. One Jetson Orin NX, "
         "orin-nx-1, stands alone.",
         "The fleet used in the rest of the book",
         "Eight machines, each with one GPU that shares memory with its CPU, connected in three groups.", parts)


@figure
def health_pipeline():
    parts = [
        zone(32, 104, 330, 290, "a GPU machine"),
        card(52, 132, 290, 60, "model", "GPU and driver", ["reports an error"], glyph="chip"),
        card(52, 222, 290, 60, "outside", "Device plugin", ["marks the GPU unhealthy"], glyph="nvidia"),
        card(52, 312, 290, 60, "service", "kubelet", ["offers one GPU fewer"], glyph="gear"),
        wire([(120, 192), (120, 222)]), wire([(120, 282), (120, 312)]),
        card(440, 312, 240, 60, "service", "Scheduler", ["places no pod on that GPU"]),
        wire([(342, 342), (440, 342)], label="seconds"),
        card(440, 130, 240, 64, "service", "Health service", ["counts the reports"], glyph="search"),
        wire([(342, 162), (440, 162)], label="report"),
        card(780, 130, 300, 64, "service", "Remediation controller", ["moves one machine one step"], glyph="gear"),
        wire([(680, 162), (780, 162)], label="verdict"),
        card(780, 312, 300, 60, "danger", "Kubernetes API", ["cordon, evict, repair, burn-in"], glyph="stack"),
        wire([(930, 194), (930, 312)], label="acts"),
        wire([(930, 372), (930, 430), (197, 430), (197, 394)], label="changes reach the machine through the kubelet"),
        text(560, 232, "the slow path: a decision about the whole machine", "note", "middle"),
        text(560, 292, "the fast path: no new work on a broken GPU", "note", "middle"),
    ]
    save(OUT / "health-pipeline.svg", 1112, 462,
         "A GPU machine reports an error. On the fast path the device plugin marks the GPU unhealthy, the kubelet "
         "offers one GPU fewer, and the scheduler stops placing pods on it. On the slow path the report reaches a "
         "health service that counts by job, machine and link and sends a verdict to a remediation controller, "
         "which acts through the Kubernetes API.",
         "One report, two paths", "Signals travel up from the machine. Decisions travel back down through the Kubernetes API.", parts)


@figure
def node_lifecycle():
    states = [("good", "Healthy", ["schedulable"]), ("idle", "Cordoned", ["no new pods"]),
              ("store", "Draining", ["jobs checkpoint", "and leave"]), ("client", "Remediating", ["one repair", "action runs"]),
              ("outside", "Validating", ["burn-in test"]), ("danger", "Quarantined", ["a person", "takes over"])]
    parts = []
    for k, (kind, name, sub) in enumerate(states):
        x = 32 + k * 184
        parts.append(card(x, 150, 160, 70, kind, name, sub))
        if k:
            parts.append(wire([(x - 24, 185), (x, 185)]))
    parts += [
        wire([(848, 220), (848, 296), (112, 296), (112, 220)], label="burn-in passed"),
        wire([(808, 150), (808, 110), (664, 110), (664, 150)], label="failed"),
        lines(216, 244, ["waits here while the", "disruption budget is spent"]),
        lines(952, 244, ["after a failure on", "the last rung"]),
        lines(32, 340, ["The ladder of repair actions: reset the GPU, then reboot, then reimage. Each failed burn-in climbs one rung.",
                        "Draining, Remediating, Validating and Quarantined each hold one slot of the disruption budget."]),
    ]
    save(OUT / "node-lifecycle.svg", 1144, 384,
         "Six states: Healthy, Cordoned, Draining, Remediating, Validating and Quarantined. A machine waits in "
         "Cordoned while the disruption budget is spent. A passed burn-in returns it from Validating to Healthy. "
         "A failed burn-in returns it to Remediating for the next action, and after the last action it is "
         "Quarantined.",
         "The lifecycle of a machine under repair", "Cordon at once, drain when the budget allows, repair one rung at a time, and validate before returning.", parts)


@figure
def fencing():
    red = KINDS["danger"][0]
    parts = [
        text(32, 150, "thor-1", "name"), text(32, 168, "epoch 1", "sub"),
        text(32, 262, "thor-2", "name"), text(32, 280, "epoch 2", "sub"),
        f'  <path class="wire idle" d="M120,156 H1010"/>', f'  <path class="wire idle" d="M120,268 H1010"/>',
        card(130, 126, 180, 60, "good", "save step 1000", ["epoch 1: stored"]),
        box(340, 128, 370, 56, KINDS["idle"][1], KINDS["idle"][0], 10, 1.3, "6 5"),
        text(525, 152, "link lost; the job keeps training", "note", "middle"),
        text(525, 170, "the Lease expires", "note", "middle"),
        card(770, 126, 230, 60, "danger", "save step 1500", ["epoch 1: refused by the store"]),
        card(400, 238, 180, 60, "service", "resume from 1000", ["assigned with epoch 2"]),
        card(600, 238, 180, 60, "good", "save step 2000", ["epoch 2: stored"]),
        text(32, 356, "store", "name"), text(32, 374, "highest epoch", "sub"),
        box(130, 340, 560, 34, KINDS["good"][1], KINDS["good"][0], 8),
        text(410, 362, "1", "pill", "middle", KINDS["good"][0]),
        box(690, 340, 320, 34, KINDS["service"][1], KINDS["service"][0], 8),
        text(850, 362, "2: a write with epoch 1 is refused", "pill", "middle", KINDS["service"][0]),
        wire([(690, 298), (690, 340)]),
        f'  <path class="wire danger" d="M885,186 V340" marker-end="url(#head-danger)"/>',
        text(895, 300, "refused", "pill", fill=red),
    ]
    save(OUT / "fencing.svg", 1042, 400,
         "A timeline with two lanes. thor-1 holds epoch 1 and saves step 1000, then loses its link and keeps "
         "training. thor-2 is assigned the job with epoch 2, resumes from step 1000, and saves step 2000. When "
         "thor-1's link returns it tries to save step 1500 with epoch 1, and the store, which has accepted epoch "
         "2, refuses the write.",
         "Fencing: the store refuses a writer that has been replaced",
         "Each assignment carries a higher epoch, and the store remembers the highest one it has accepted.", parts)


@figure
def node_join():
    parts = [
        sheet(32, 112, 262, 176, "client", "NEW MACHINE thor-3", [
            ("", "kubelet"), ("strong", "bootstrap token"), ("strong", "hash of the CA key")],
            footer=["its private key is made here", "and stays here"]),
        card(440, 126, 250, 74, "service", "API server", ["accepts the token for", "one kind of request"], glyph="gear"),
        card(830, 126, 250, 74, "service", "Signer", ["approves and signs", "requests for node names"], glyph="key"),
        wire([(294, 146), (440, 146)], label="1 check, 2 ask"),
        wire([(690, 163), (830, 163)], label="3 sign"),
        wire([(440, 182), (294, 182)], label="4 certificate"),
        card(440, 300, 250, 70, "store", "Node and Lease", ["made with the certificate"], glyph="doc"),
        wire([(163, 288), (163, 335), (440, 335)], label="5 register"),
        lines(740, 306, ["1  The kubelet checks the server against the hash.",
                         "2  It shows the token and asks for a certificate",
                         "    named system:node:thor-3.",
                         "3, 4  The request is signed and returned.",
                         "5  Every later request uses the certificate."]),
    ]
    save(OUT / "node-join.svg", 1112, 404,
         "A new machine, thor-3, holds a bootstrap token and the hash of the cluster's CA key. Its kubelet checks "
         "the API server against the hash, shows the token, and asks for a certificate named system:node:thor-3. "
         "A signer in the control plane approves and signs the request, the kubelet fetches the certificate, and "
         "with it creates its Node object and its Lease.",
         "How a machine joins a cluster", "A token that expires is traded for a certificate that names one node.", parts)


@figure
def lost_reply():
    parts = []
    rows = [(110, "WITHOUT A CLIENT TOKEN", "create a Thor", "m-06 created", "danger",
             "The account holds m-03 and m-06. The controller owns m-06, and m-03 runs with no owner."),
            (300, "WITH THE SLOT NAME AS THE TOKEN", "create a Thor, token thor-3", "m-03, already there", "good",
             "The account holds m-03, and the controller owns it.")]
    for y, heading, ask, answer, kind, result in rows:
        parts += [
            text(32, y - 10, heading, "tab"),
            card(32, y, 200, 116, "service", "Controller", ["filling slot thor-3"]),
            card(800, y, 220, 116, "outside", "Provider", ["quota: five Thors"]),
            wire([(232, y + 18), (800, y + 18)], label=ask),
            wire([(800, y + 44), (232, y + 44)], "danger", label="m-03 created; the reply is lost"),
            wire([(232, y + 72), (800, y + 72)], label=ask + ", again"),
            wire([(800, y + 98), (232, y + 98)], label=answer),
            text(32, y + 140, result, "note", fill=KINDS[kind][0]),
        ]
    save(OUT / "lost-reply.svg", 1052, 466,
         "Two sequences between a controller and a provider. Without a token, the first create makes machine m-03 "
         "and its reply is lost; the retry makes a second machine, m-06, and m-03 runs with no owner. With the "
         "slot name thor-3 as a client token, the retry returns m-03 and creates nothing.",
         "A create call whose reply is lost", "The controller cannot tell a lost request from a lost reply, so its retry has to be safe in both cases.", parts)


@figure
def vm_in_pod():
    parts = [
        sheet(32, 112, 236, 160, "client", "VIRTUALMACHINE web", [
            ("", "cpu: 4 cores"), ("", "memory: 16Gi"), ("", "disks and devices")], footer=["kubectl apply"]),
        card(338, 120, 250, 64, "service", "API server", ["stores the VM objects"], glyph="gear"),
        wire([(268, 152), (338, 152)]),
        card(338, 262, 250, 64, "service", "virt-controller", ["creates a pod for each VM"], glyph="gear"),
        wire([(463, 184), (463, 262)], label="watch"),
        zone(668, 104, 420, 306, "a node"),
        card(688, 130, 380, 56, "service", "virt-handler", ["on every node; starts and watches VMs"], glyph="eye"),
        card(688, 212, 380, 60, "client", "Pod virt-launcher-web", ["a QEMU process: the guest's memory, CPUs"], glyph="chip"),
        card(688, 284, 380, 50, "outside", "Guest kernel and programs", ["run on the host's CPU cores"]),
        card(688, 346, 380, 48, "model", "KVM, in the host kernel", ["reached through /dev/kvm"]),
        wire([(878, 186), (878, 212)]),
        wire([(588, 294), (630, 294), (630, 242), (688, 242)]),
    ]
    save(OUT / "vm-in-pod.svg", 1120, 434,
         "A VirtualMachine object named web is applied to the API server. The virt-controller watches it and "
         "creates a pod named virt-launcher-web. On the node, virt-handler starts the VM inside the pod: a QEMU "
         "process holds the guest's memory and CPUs, and the guest's kernel and programs run on the host's CPU "
         "cores through KVM in the host kernel.",
         "A virtual machine on Kubernetes is a pod whose process is the VM",
         "KubeVirt adds the objects and the controllers. The scheduler sees an ordinary pod.", parts)


@figure
def pre_copy():
    blue, red = KINDS["client"][0], KINDS["danger"][0]
    rounds = [(100.0, "round 1", "8.0 s, VM running", blue), (32.0, "round 2", "2.6 s, VM running", blue),
              (10.24, "round 3", "0.8 s, VM running", blue), (3.28, "round 4", "0.26 s, VM paused", red)]
    base, scale = 340, 2.0
    parts = [f'  <path class="wire idle" d="M100,{base} H960"/>']
    for k, (gb, name, time, colour) in enumerate(rounds):
        x, h = 130 + k * 210, max(gb * scale, 6)
        parts += [box(x, base - h, 130, h, colour, colour, 6, 0),
                  text(x + 65, base - h - 10, ("%g GB" % gb), "name", "middle"),
                  text(x + 65, base + 22, name, "pill", "middle", colour),
                  text(x + 65, base + 40, time, "note", "middle")]
        if k:
            parts.append(text(x - 40, base - 60, "× 0.32", "pill", "middle", MUTED))
    parts += [f'  <path class="wire danger" d="M740,{base - 7.5} H960" />',
              text(960, base - 66, "the dashed line is 3.75 GB:", "note", "end", red),
              text(960, base - 50, "what a pause of 0.3 s can carry", "note", "end", red)]
    save(OUT / "pre-copy.svg", 1000, 404,
         "Four bars for the migration of a 100 GB VM that dirties 4 GB per second over a link of 12.5 GB per "
         "second. Round 1 sends 100 GB in 8.0 seconds, round 2 sends 32 GB in 2.6 seconds, round 3 sends "
         "10.24 GB in 0.8 seconds, and in round 4 the VM is paused while the last 3.28 GB are sent in 0.26 "
         "seconds. Each bar is 0.32 times the one before.",
         "Pre-copy: a 100 GB VM over four bonded 25 GbE lanes",
         "Each round sends what the VM dirtied during the round before. The VM is paused for the last one only.", parts)


@figure
def allreduce_shapes():
    import math
    green, grey, red = KINDS["service"], KINDS["idle"], KINDS["danger"]

    def spots(cx, cy, r):
        return [(cx + r * math.cos(math.radians(-90 + 72 * k)), cy + r * math.sin(math.radians(-90 + 72 * k))) for k in range(5)]

    def node(x, y, label, kind):
        return [box(x - 44, y - 18, 88, 36, kind[1], kind[0], 10, 1.4), text(x, y + 5, label, "pill", "middle", kind[0])]

    parts = [text(250, 112, "A COORDINATOR", "tab", "middle"), text(780, 112, "A RING", "tab", "middle")]
    star = spots(250, 290, 140)
    for x, y in star:
        parts.append(f'  <path class="wire" d="M{x:.1f},{y:.1f} L250,290"/>')
    for k, (x, y) in enumerate(star):
        parts += node(x, y, "thor-%d" % (k + 1), grey)
    parts += node(250, 290, "coordinator", red)
    parts += [text(250, 468, "the coordinator's link: 5 gradients in, 5 out", "note", "middle", red[0]),
              text(250, 486, "every other link: 1 in, 1 out", "note", "middle")]

    ring = spots(780, 290, 140)
    for k, (x, y) in enumerate(ring):
        nx, ny = ring[(k + 1) % 5]
        dx, dy = nx - x, ny - y
        length = math.hypot(dx, dy)
        ax, ay = x + dx / length * 52, y + dy / length * 30
        bx, by = nx - dx / length * 52, ny - dy / length * 30
        parts.append(f'  <path class="wire" d="M{ax:.1f},{ay:.1f} L{bx:.1f},{by:.1f}" marker-end="url(#head)"/>')
    for k, (x, y) in enumerate(ring):
        parts += node(x, y, "thor-%d" % (k + 1), green)
    parts += [text(780, 286, "8 exchanges,", "note", "middle"), text(780, 304, "one chunk each", "note", "middle"),
              text(780, 468, "every link: 1.6 gradients, in one direction", "note", "middle", green[0]),
              text(780, 486, "no link carries more than another", "note", "middle")]
    save(OUT / "allreduce-shapes.svg", 1040, 510,
         "Two layouts of five workers. On the left every worker is connected to one coordinator, whose link "
         "carries five gradients in each direction. On the right the five workers form a ring and each sends "
         "chunks to its right-hand neighbour, so every link carries 1.6 gradients.",
         "Two ways to add five gradients", "A coordinator concentrates the traffic on one link. A ring spreads it evenly.", parts)


MACHINES = ["orin-nx-1", "spark-1", "spark-2", "thor-1", "thor-2", "thor-3", "thor-4", "thor-5"]


def machine_row(x, y, owners, colours):
    """Eight machine boxes in name order, each tinted by the job that holds it."""
    parts = []
    for k, name in enumerate(MACHINES):
        owner = owners[k]
        accent, tint = colours.get(owner, KINDS["idle"])
        bx = x + k * 112
        parts += [box(bx, y, 100, 50, tint, accent, 9, 1.4),
                  text(bx + 50, y + 21, name, "pill", "middle", INK),
                  text(bx + 50, y + 38, owner or "free", "pill", "middle", accent)]
    return parts


@figure
def gang_deadlock():
    colours = {"train-a": KINDS["client"], "train-b": KINDS["store"]}
    parts = [text(32, 112, "ONE POD AT A TIME", "tab")]
    parts += machine_row(32, 124, ["train-a", "train-b", "train-a", "train-b", "train-a", "train-b", "train-a", "train-b"], colours)
    parts += [text(32, 200, "train-a holds 4 of 5. train-b holds 4 of 5. Eight GPUs are held and no job runs.", "note",
                   fill=KINDS["danger"][0]),
              text(32, 258, "ONE JOB AT A TIME", "tab")]
    parts += machine_row(32, 270, ["", "", "", "train-a", "train-a", "train-a", "train-a", "train-a"], colours)
    parts += [text(32, 346, "train-a holds 5 of 5 and runs. train-b holds nothing and waits; three GPUs stay free.", "note",
                   fill=KINDS["good"][0])]
    save(OUT / "gang-deadlock.svg", 952, 372,
         "Two rows of the fleet's eight machines. In the first row, placed one pod at a time, train-a and train-b "
         "hold four machines each in alternation; each needs five and no job runs. In the second row, placed one "
         "job at a time, train-a holds the five Thors and runs, and the Orin NX and the two Sparks are free while "
         "train-b waits.",
         "Two jobs of five workers on eight GPUs", "A job with four of its five workers does no work and keeps four GPUs from everyone else.", parts)


@figure
def fleet_topology():
    parts = [
        card(32, 110, 1076, 56, "idle", "House network, 1 GbE", ["reaches every machine; the only path between domains: 0.125 GB/s"], glyph="swap"),
        zone(32, 232, 572, 190, "domain shelf"),
        card(52, 258, 532, 52, "outside", "25 GbE switch", ["3.125 GB/s between any two Thors"], glyph="swap"),
        zone(636, 232, 280, 190, "domain desk"),
        card(656, 258, 240, 52, "outside", "200 GbE cable", ["25 GB/s"], glyph="swap"),
        zone(948, 232, 160, 190, "domain bench"),
        wire([(318, 232), (318, 166)], arrow=False), wire([(776, 232), (776, 166)], arrow=False),
        wire([(1090, 232), (1090, 166)], arrow=False),
    ]
    for k in range(5):
        x = 52 + k * 109
        parts += [card(x, 344, 96, 56, "model", "thor-%d" % (k + 1), ["1 GPU"]), wire([(x + 48, 344), (x + 48, 310)], arrow=False)]
    for k in range(2):
        x = 656 + k * 126
        parts += [card(x, 344, 114, 56, "model", "spark-%d" % (k + 1), ["1 GPU"]), wire([(x + 57, 344), (x + 57, 310)], arrow=False)]
    parts += [card(964, 300, 128, 60, "client", "orin-nx-1", ["1 GPU"])]
    save(OUT / "fleet-topology.svg", 1140, 446,
         "A tree of links. The 1 GbE house network at the top reaches every machine and is the only path between "
         "domains. Below it, the shelf domain holds five Thors on a 25 GbE switch, the desk domain holds two "
         "Sparks on a 200 GbE cable, and the bench domain holds the Orin NX.",
         "The fleet as a tree of links", "Two machines exchange data at the speed of the lowest link they have in common.", parts)


@figure
def gcounter():
    red = KINDS["danger"][0]
    moments = [("each records its own reports", [("300  0  0", "300"), ("0  120  0", "120"), ("0  0  40", "40")], False),
               ("the bench is cut off; shelf and desk merge, and reports keep arriving",
                [("360  120  0", "480"), ("300  120  0", "420"), ("0  0  65", "65")], True),
               ("the network heals; rows are exchanged in any order",
                [("360  120  65", "545"), ("360  120  65", "545"), ("360  120  65", "545")], False)]
    parts = [text(250 + k * 270, 112, name, "name", "middle") for k, name in enumerate(("shelf", "desk", "bench"))]
    for row, (label, cells, cut) in enumerate(moments):
        y = 132 + row * 96
        parts.append(text(32, y + 64, label, "note"))
        for k, (vector, value) in enumerate(cells):
            x = 140 + k * 270
            kind = KINDS["good"] if row == 2 else KINDS["service"]
            parts += [box(x, y, 220, 44, kind[1], kind[0], 9, 1.4),
                      text(x + 16, y + 28, vector, "mono strong"),
                      text(x + 204, y + 28, "= " + value, "pill", "end", kind[0])]
        if cut:
            parts += [f'  <path class="wire danger" d="M655,{y - 8} V{y + 52}"/>', text(662, y - 2, "no route", "pill", fill=red)]
    save(OUT / "gcounter.svg", 950, 424,
         "Three replicas at three moments. First each holds only its own reports: 300, 120 and 40. During a "
         "partition that cuts off the bench, the shelf holds 360, 120, 0, the desk 300, 120, 0 and the bench "
         "0, 0, 65. After the network heals all three hold 360, 120, 65, which sums to 545.",
         "Three grow-only counters through a partition",
         "A row has one entry per replica: shelf, desk, bench. A merge keeps the larger value of each entry.", parts)


@figure
def quota_shares():
    def shares(y, layout, note, colour):
        parts = []
        for k, (owner, used) in enumerate(layout):
            accent, tint = KINDS["client"] if owner == "shelf" else KINDS["store"]
            x = 140 + k * 92
            parts += [box(x, y, 80, 50, accent if used else tint, accent, 9, 1.4),
                      text(x + 40, y + 22, owner, "pill", "middle", "#FFFFFF" if used else accent),
                      text(x + 40, y + 39, "in use" if used else "free", "pill", "middle", "#FFFFFF" if used else accent)]
        parts.append(text(710, y + 30, note, "note", fill=colour))
        return parts

    parts = [text(32, 150, "apart", "name")]
    parts += shares(120, [("shelf", 1), ("shelf", 1), ("shelf", 1), ("shelf", 0), ("desk", 1), ("desk", 0)],
                    "a 2-GPU job fits in neither share", KINDS["danger"][0])
    parts += [text(32, 250, "in contact", "name")]
    parts += shares(220, [("shelf", 1), ("shelf", 1), ("shelf", 1), ("shelf", 1), ("shelf", 1), ("desk", 1)],
                    "desk gave one to shelf; the job runs", KINDS["good"][0])
    parts.append(lines(32, 310, ["Each box is one GPU of a quota of six. A replica admits jobs only into boxes it owns, "
                                 "so the six are not exceeded while the replicas are apart."]))
    save(OUT / "quota-shares.svg", 1010, 336,
         "A quota of six GPUs as six boxes. While the replicas are apart, the shelf owns four boxes with three in "
         "use and the desk owns two with one in use, and a two-GPU job fits in neither share. In contact, the "
         "desk gives one free box to the shelf, which then owns five, all in use, and the desk owns one, in use.",
         "A quota divided into shares", "Shares add up to the quota. A replica with unused share can pass some to one that has run out.", parts)


@figure
def artifact_chunks():
    blue, amber, green = KINDS["client"], KINDS["store"], KINDS["service"]
    parts = [
        card(32, 120, 150, 56, "client", "tag llm:v1", ["can be moved"]),
        card(32, 300, 150, 56, "store", "tag llm:v2", ["can be moved"]),
        sheet(250, 104, 200, 100, "client", "MANIFEST of v1", [("", "8 lines: a digest"), ("", "and a size each")]),
        sheet(250, 284, 200, 100, "store", "MANIFEST of v2", [("", "8 lines: a digest"), ("", "and a size each")]),
        wire([(182, 148), (250, 148)]), wire([(182, 328), (250, 328)]),
    ]
    for k in range(10):
        kind = green if k < 6 else (blue if k < 8 else amber)
        owner = "both" if k < 6 else ("v1 only" if k < 8 else "v2 only")
        x = 520 + (k % 5) * 100
        y = 150 if k < 5 else 250
        if k >= 6:
            x, y = 520 + (k - 6) * 100 + (0 if k < 8 else 100), 350
        if k == 5:
            x, y = 520, 250
        parts += [box(x, y, 88, 50, kind[1], kind[0], 9, 1.4), text(x + 44, y + 22, "chunk", "pill", "middle", INK),
                  text(x + 44, y + 39, owner, "pill", "middle", kind[0])]
    parts += [
        wire([(450, 148), (485, 148), (485, 175), (520, 175)]),
        wire([(450, 328), (485, 328), (485, 275), (520, 275)]),
        lines(640, 262, ["six chunks, stored once,", "listed by both manifests"]),
        text(520, 126, "BLOBS, EACH NAMED BY THE SHA-256 OF ITS BYTES", "tab"),
    ]
    save(OUT / "artifact-chunks.svg", 1040, 426,
         "Two tags, llm:v1 and llm:v2, each point at a manifest that lists eight chunks. Six chunks are listed by "
         "both manifests and stored once. Two chunks belong only to version 1 and two only to version 2, so the "
         "store holds ten chunks and two manifests.",
         "Two versions of a model in a content-addressed store", "A tag points at a manifest, and a manifest lists chunks by digest.", parts)


@figure
def cli_anatomy():
    parts = [
        sheet(32, 120, 230, 96, "client", "COMMAND LINE", [("strong", "gpuctl nodes -o json")], footer=["typed, or run by a script"]),
        card(340, 126, 220, 84, "service", "run(args)", ["chooses the command,", "returns the status"], glyph="terminal"),
        wire([(262, 168), (340, 168)]),
        sheet(340, 280, 220, 96, "store", "KUBECONFIG", [("", "server address"), ("", "credentials")]),
        wire([(450, 280), (450, 210)]),
        card(660, 300, 230, 64, "service", "API server", ["one list of Node objects"], glyph="gear"),
        wire([(520, 210), (520, 250), (775, 250), (775, 300)], label="list nodes"),
        card(660, 104, 320, 52, "good", "Standard output", ["the result, and nothing else"]),
        card(660, 166, 320, 52, "store", "Standard error", ["messages for a person"]),
        wire([(560, 150), (610, 150), (610, 130), (660, 130)]),
        wire([(560, 186), (610, 186), (610, 192), (660, 192)]),
        card(32, 290, 230, 76, "outside", "Exit status", ["0 success, 1 the command", "failed, 2 wrong command line"]),
        wire([(340, 196), (300, 196), (300, 328), (262, 328)]),
    ]
    save(OUT / "cli-anatomy.svg", 1012, 404,
         "The command line gpuctl nodes -o json enters the function run, which reads the kubeconfig for the "
         "server address and credentials and asks the API server for the list of nodes. It writes the result to "
         "standard output, messages to standard error, and returns an exit status of 0, 1 or 2.",
         "One command through gpuctl", "Arguments go in. The result, the messages, and the status come out on three separate channels.", parts)


@figure
def cross_build():
    parts = [
        card(32, 190, 250, 84, "client", "One source tree", ["on the Jetson:", "Linux, arm64"], glyph="doc"),
        card(380, 198, 200, 68, "service", "Compiler", ["one target per run"], glyph="gear"),
        wire([(282, 232), (380, 232)]),
    ]
    targets = [("Linux, arm64", "ELF", "model"), ("Linux, amd64", "ELF", "model"),
               ("macOS, arm64", "Mach-O", "outside"), ("Windows, amd64", "PE", "store")]
    for k, (system, fmt, kind) in enumerate(targets):
        y = 104 + k * 76
        parts += [card(700, y, 300, 60, kind, system, ["file format: " + fmt], glyph="terminal"),
                  wire([(580, 232), (640, 232), (640, y + 30), (700, y + 30)])]
    save(OUT / "cross-build.svg", 1032, 430,
         "One source tree on the Jetson, a Linux arm64 machine, is compiled into four executables: ELF for Linux "
         "on arm64, ELF for Linux on amd64, Mach-O for macOS on arm64, and PE for Windows on amd64.",
         "One source, four binaries", "Each operating system loads its own file format, and each processor runs its own machine code.", parts)


for name in sys.argv[1:] or list(FIGURES):
    FIGURES[name]()
    print("  " + name)
print("wrote %d figure(s) to %s" % (len(sys.argv[1:]) or len(FIGURES), OUT))
