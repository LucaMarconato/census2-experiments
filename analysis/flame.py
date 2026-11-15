#!/usr/bin/env python3
"""Flamegraph SVG and hot-frame summary from py-spy raw (collapsed) stacks. No dependencies.

    python analysis/flame.py results/profiles/local-all-corpus_x-w8.txt --focus 'decode' -o zoom.svg
    python analysis/flame.py results/profiles/local-all-corpus_x-w8.txt --top 15
"""

import argparse
import html
import re
import zlib
from collections import Counter

W, ROW, FONT = 1800, 30, 18
MAX_DEPTH = 40  # rows
MIN_W = 3  # px: narrower boxes are not drawn, so rare deep stacks do not set the height
# plumbing frames that every thread has; dropping them saves rows
SKIP = re.compile(r"^(Thread\._bootstrap|Thread\._bootstrap_inner|Thread\.run|_worker|_WorkItem\.run|"
                  r"BaseEventLoop\.run_forever|BaseEventLoop\._run_once|Handle\._run|Context\.run) \(")
# leaf frames of a thread that waits: thread-pool idle, condition waits, the selector, a bare thread
IDLE = re.compile(r"^(_worker \(thread|Condition\.wait|KqueueSelector\.select|select \(|thread \(|worker thread$)")


def load(path: str, focus: str | None, idle: bool) -> Counter:
    stacks: Counter = Counter()
    for line in open(path):
        stack, _, n = line.rstrip().rpartition(" ")
        frames = stack.split(";")
        if frames and frames[0].startswith("thread ("):  # py-spy --threads root frame
            name = frames[0].split(": ", 1)[1] if ": " in frames[0] else ""
            frames[0] = name if name in ("MainThread", "zarr_io") else "worker thread"
        if not idle and frames and IDLE.match(short(frames[-1])):
            continue
        if any("<frozen importlib" in f for f in frames):  # interpreter start-up, not the query
            continue
        if focus:
            hit = next((i for i, f in enumerate(frames) if re.search(focus, f)), None)
            if hit is None:
                continue
            frames = frames[hit:]
        stacks[tuple(frames)] += int(n)
    return stacks


def short(frame: str) -> str:
    """'func (path/to/module.py:12)' -> 'func (module.py)'."""
    m = re.match(r"(.*?) \((.*?)(?::\d+)?\)$", frame)
    return f"{m.group(1)} ({m.group(2).rsplit('/', 1)[-1]})" if m else frame


def tree(stacks: Counter) -> dict:
    root: dict = {"n": 0, "kids": {}}
    for frames, n in stacks.items():
        node = root
        node["n"] += n
        for f in (short(f) for f in frames):
            if SKIP.match(f):
                continue
            node = node["kids"].setdefault(f, {"n": 0, "kids": {}})
            node["n"] += n
    return root


def color(name: str) -> str:
    h = zlib.crc32(name.split(" (")[-1].encode()) % 60
    return f"hsl({10 + h},75%,{62 + h % 12}%)"


def svg(root: dict, title: str) -> str:
    total = root["n"] or 1
    rects, depth = [], [0]

    def walk(node: dict, x: float, d: int) -> None:
        depth[0] = max(depth[0], d)
        for name, kid in sorted(node["kids"].items()):
            w = kid["n"] / total * W
            if w >= MIN_W:
                rects.append((x, d, w, name, kid["n"]))
                walk(kid, x, d + 1)
            x += w

    walk(root, 0, 0)
    rects = [r for r in rects if r[1] < MAX_DEPTH]
    depth[0] = min(depth[0], MAX_DEPTH - 1)
    h = (depth[0] + 2) * ROW + 40
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" font-family="Helvetica,Arial" font-size="{FONT}">',
           f'<rect width="{W}" height="{h}" fill="#FBFBF8"/>',
           f'<text x="8" y="26" font-size="22" font-weight="bold">{html.escape(title)}</text>']
    for x, d, w, name, n in rects:
        y = h - (d + 1) * ROW - 4
        out.append(f'<rect x="{x:.1f}" y="{y}" width="{max(w - 0.5, 0.5):.1f}" height="{ROW - 2}" fill="{color(name)}"/>')
        chars = int((w - 6) / (FONT * 0.55))
        if chars >= 4:
            label = name if len(name) <= chars else name[: chars - 1] + "…"
            out.append(f'<text x="{x + 3:.1f}" y="{y + ROW - 9}">{html.escape(label)} {100 * n / total:.0f}%</text>'
                       if len(label) + 5 <= chars else f'<text x="{x + 3:.1f}" y="{y + ROW - 9}">{html.escape(label)}</text>')
    out.append("</svg>")
    return "\n".join(out)


def top(stacks: Counter, k: int) -> str:
    total = sum(stacks.values()) or 1
    incl: Counter = Counter()
    self_: Counter = Counter()
    for frames, n in stacks.items():
        for f in {short(f) for f in frames}:
            incl[f] += n
        if frames:
            self_[short(frames[-1])] += n
    lines = [f"samples {total}", "self%  frame"]
    lines += [f"{100 * n / total:5.1f}  {f}" for f, n in self_.most_common(k)]
    lines += ["incl%  frame"] + [f"{100 * n / total:5.1f}  {f}" for f, n in incl.most_common(k)]
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("raw")
    p.add_argument("--focus", help="regex: keep the subtree from the first matching frame")
    p.add_argument("--no-idle", action="store_true", help="drop samples of waiting threads (IDLE leaves)")
    p.add_argument("--title", default=None)
    p.add_argument("--top", type=int, default=0)
    p.add_argument("-o", "--out")
    a = p.parse_args()
    stacks = load(a.raw, a.focus, not a.no_idle)
    if a.top:
        print(top(stacks, a.top))
    if a.out:
        open(a.out, "w").write(svg(tree(stacks), a.title or a.raw.rsplit("/", 1)[-1]))


if __name__ == "__main__":
    main()
