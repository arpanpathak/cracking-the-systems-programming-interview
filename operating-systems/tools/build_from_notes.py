"""Builds src/chNN-*.md from chapter_notes/: the prose is the notes text,
and the figures, listings, outputs and tables of the book are inserted at
the end of the section each one belongs to."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOTES = ROOT / "chapter_notes"
ASSETS = ROOT / ".backup-original" / "src-md-claude"
SRC = ROOT / "src"

# chapter file stem -> {section key: [asset keys]}. "intro" is the text before
# the first "##" heading and "end" is the end of the chapter.
PLAN = {
    "ch01-what-is-an-os": {"p2": ["F:ch01_layers"], "end": ["T:1-1"]},
    "ch02-the-machine": {"2.1": ["F:ch02_machine"], "2.3": ["F:ch02_privilege"]},
    "ch03-processes": {
        "3.1": ["F:ch03_address_space", "L:3-1", "O:3-1", "L:3-2", "O:3-2"],
        "3.2": ["F:ch03_fork", "L:3-3", "O:3-3", "L:3-4", "O:3-4"],
    },
    "ch04-threads": {
        "4.1": ["F:ch04_threads"],
        "4.2": ["F:ch04_race_timeline", "L:4-1", "O:4-1", "L:4-2", "O:4-2", "L:4-3", "O:4-3", "L:4-4", "O:4-4"],
        "4.3": ["L:4-5", "O:4-5", "L:4-6", "O:4-6"],
    },
    "ch05-scheduling": {
        "5.1": ["F:ch05_queues"],
        "5.2": ["F:ch05_gantt", "L:5-1", "O:5-1", "L:5-2", "O:5-2"],
    },
    "ch06-synchronization": {
        "6.1": ["F:ch06_mutex", "L:6-1", "O:6-1", "L:6-2", "O:6-2"],
        "6.2": ["L:6-3", "O:6-3", "L:6-4", "O:6-4"],
        "6.3": ["F:ch06_deadlock", "L:6-5", "O:6-5", "L:6-6", "O:6-6"],
        "6.4": ["T:6-1"],
    },
    "ch07-virtual-memory": {
        "7.1": ["F:ch07_vm_paging"],
        "7.2": ["F:ch07_pagewalk"],
        "7.3": ["L:7-1", "O:7-1", "L:7-2", "O:7-2", "L:7-3", "O:7-3", "L:7-4", "O:7-4"],
    },
    "ch08-allocation": {
        "8.2": ["F:ch08_bump", "L:8-1", "O:8-1", "L:8-2", "O:8-2"],
        "8.3": ["F:ch08_freelist", "L:8-3", "O:8-3", "L:8-4", "O:8-4"],
    },
    "ch09-system-calls": {
        "9.1": ["F:ch09_trap"],
        "9.2": ["L:9-1", "O:9-1", "L:9-2", "O:9-2", "F:ch09_buffering", "L:9-3", "O:9-3", "L:9-4", "O:9-4"],
    },
    "ch10-signals": {
        "10.1": ["F:ch10_signal_lifecycle"],
        "10.2": ["L:10-1", "O:10-1", "L:10-2", "O:10-2"],
        "10.3": ["L:10-3", "O:10-3"],
    },
    "ch11-ipc": {
        "11.1": ["F:ch11_pipe", "L:11-1", "O:11-1", "L:11-2", "O:11-2"],
        "11.2": ["F:ch11_shm", "L:11-3", "O:11-3"],
        "11.3": ["L:11-4", "O:11-4"],
    },
    "ch12-filesystems": {
        "12.1": ["L:12-1", "O:12-1", "L:12-2", "O:12-2"],
        "12.2": ["F:ch12_fs_layout", "F:ch12_inode"],
        "12.3": ["L:12-3", "O:12-3", "L:12-4", "O:12-4"],
    },
    "ch13-io-event-loops": {
        "13.2": ["F:ch13_event_loop", "L:13-1", "L:13-2", "O:13-1", "O:13-2"],
        "13.3": ["L:13-3", "O:13-3"],
    },
    "ch14-networking": {
        "14.1": ["F:ch14_tcp"],
        "14.2": ["L:14-1", "O:14-1", "L:14-2", "O:14-2"],
        "14.3": ["L:14-3", "O:14-3", "L:14-4", "O:14-4"],
    },
    "ch15-daemons": {
        "15.1": ["F:ch15_daemonize"],
        "15.2": ["L:15-1", "L:15-2", "O:15-1", "O:15-2"],
    },
    "ch16-virtualization": {"16.1": ["F:ch16_vm_vs_container"], "16.2": ["F:ch16_namespaces"]},
    "ch17-multiprocessors": {
        "17.1": ["F:ch17_numa"],
        "17.2": ["F:ch17_false_sharing", "L:17-1", "O:17-1", "L:17-2", "O:17-2"],
    },
    "ch18-performance": {
        "18.1": ["F:ch18_pyramid", "L:18-1", "O:18-1", "L:18-2", "O:18-2"],
    },
}


def assets_of(text):
    """Finds every figure, listing, output and table of one book chapter."""
    found = {}

    for match in re.finditer(r'<figure>\n<img src="figures/(\w+)\.svg".*?</figure>', text, re.S):
        found[f"F:{match.group(1)}"] = match.group(0)

    for match in re.finditer(r"\*\*(Listing|Output) (\d+-\d+)\..*?\*\*\n\n```.*?```", text, re.S):
        found[f"{match.group(1)[0]}:{match.group(2)}"] = match.group(0)

    for match in re.finditer(r"\*\*Table (\d+-\d+)\..*?\*\*\n\n(?:\|.*\n)+", text):
        found[f"T:{match.group(1)}"] = match.group(0).rstrip("\n")

    return found


def prose_of(stem):
    """The notes text, with the chapter title in the book's form."""
    text = (NOTES / f"{stem}.md").read_text()
    text = re.sub(r"^# Chapter (\d+): ", r"# \1. ", text)
    text = text.replace("—", ", ").replace("$n$", "`n`")
    return text.rstrip("\n")


def build(stem, plan):
    assets = assets_of((ASSETS / f"{stem}.md").read_text())
    blocks = re.split(r"\n(?=## )", prose_of(stem))
    out = []

    for block in blocks:
        heading = re.match(r"## (\d+\.\d+)", block)
        key = heading.group(1) if heading else "intro"

        if key == "intro" and "p2" in plan:
            paragraphs = block.split("\n\n")
            extra = [assets[name] for name in plan["p2"]]
            block = "\n\n".join(paragraphs[:3] + extra + paragraphs[3:])

        extra = [assets[name] for name in plan.get(key, [])]
        out.append("\n\n".join([block.rstrip("\n")] + extra))

    out.extend(assets[name] for name in plan.get("end", []))
    used = {name for names in plan.values() for name in names}
    missing = sorted(set(assets) - used)
    (SRC / f"{stem}.md").write_text("\n\n".join(out) + "\n")
    return missing


def main():
    for stem, plan in PLAN.items():
        if not (NOTES / f"{stem}.md").exists():
            print(f"no notes yet: {stem}")
            continue
        missing = build(stem, plan)
        print(f"built {stem}" + (f"  NOT PLACED: {missing}" if missing else ""))

    preface = NOTES / "preface.md"
    if preface.exists():
        text = preface.read_text().replace("# Preface Notes", "# Preface").replace("—", ", ")
        (SRC / "preface.md").write_text(text)
        print("built preface")


if __name__ == "__main__":
    main()
