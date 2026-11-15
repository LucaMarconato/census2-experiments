#!/usr/bin/env python3
"""Time vs number of stores, from scaling.py's records (<results>/scaling/bench.jsonl).

Takes the 8-worker runs, median query_seconds per where x size x shape:
- bench.md: that table, plus one of median requests.
- bench.svg: log-log plot, x = number of stores, y = seconds. Solid lines: local disk
  (corpus_obs, open, single); dashed: floci S3 (corpus_obs, open). Past the real stores
  (<data>/zarr) the points are symlinked copies. Plain SVG, no plotting library.
"""

import math

import pandas as pd

from config import DATA, RESULTS, scrub

OUT = RESULTS / "scaling"
scrub(OUT / "bench.jsonl")
d = pd.read_json(OUT / "bench.jsonl", lines=True)
d = d[(d.status == "ok") & (d.workers == 8)]
t = d.pivot_table(index=["where", "size"], columns="shape", values="query_seconds", aggfunc="median")
r = d.pivot_table(index=["where", "size"], columns="shape", values="requests", aggfunc="median")
md = t.round(2).reset_index().to_markdown(index=False) + "\n\nRequests\n\n" + r.reset_index().to_markdown(index=False)
(OUT / "bench.md").write_text(md + "\n")
print(md)

W, H, L, B = 1600, 900, 140, 110  # canvas, left and bottom margins
sizes = sorted(d["size"].unique())
secs = t.stack().clip(lower=0.01)
xs = (min(sizes), max(max(sizes), min(sizes) * 2))
ys = (10 ** math.floor(math.log10(secs.min())), 10 ** math.ceil(math.log10(secs.max())))
X = lambda v: L + (math.log10(v) - math.log10(xs[0])) / (math.log10(xs[1]) - math.log10(xs[0])) * (W - L - 60)  # noqa: E731
Y = lambda v: H - B - (math.log10(v) - math.log10(ys[0])) / (math.log10(ys[1]) - math.log10(ys[0])) * (H - B - 80)  # noqa: E731
real = len(list((DATA / "zarr").glob("*.zarr")))
series = [("local-scaling", "corpus_obs", "#2F6FDE", ""), ("local-scaling", "open", "#E07A2F", ""),
          ("local-scaling", "single", "#4A5568", ""), ("floci-scaling", "corpus_obs", "#2F6FDE", "8 6"),
          ("floci-scaling", "open", "#E07A2F", "8 6")]  # fmt: skip
out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="Helvetica,Arial" font-size="24">',
       f'<rect width="{W}" height="{H}" fill="#FBFBF8"/>',
       '<text x="140" y="44" font-size="30" font-weight="bold">Time vs number of stores (8 workers, median)</text>']  # fmt: skip
for v in sizes:
    out.append(f'<line x1="{X(v):.0f}" y1="80" x2="{X(v):.0f}" y2="{H - B}" stroke="#E2E0D8"/>')
    out.append(f'<text x="{X(v):.0f}" y="{H - B + 34}" text-anchor="middle">{v}</text>')
v = ys[0]
while v <= ys[1] * 1.001:
    out.append(f'<line x1="{L}" y1="{Y(v):.0f}" x2="{W - 60}" y2="{Y(v):.0f}" stroke="#E2E0D8"/>')
    out.append(f'<text x="{L - 12}" y="{Y(v) + 8:.0f}" text-anchor="end">{v:g} s</text>')
    v *= 10
out.append(f'<text x="{(W + L) / 2:.0f}" y="{H - 30}" text-anchor="middle">stores (real up to {real}, symlinked copies beyond)</text>')
ly = 110
for where, shape, color, dash in series:
    if where not in t.index.get_level_values(0) or shape not in t.columns:
        continue
    pts = t.loc[where, shape].dropna()
    path = " ".join(f"{X(n):.1f},{Y(max(v, ys[0])):.1f}" for n, v in pts.items())
    out.append(f'<polyline points="{path}" fill="none" stroke="{color}" stroke-width="4" stroke-dasharray="{dash}"/>')
    for n, v in pts.items():
        out.append(f'<circle cx="{X(n):.1f}" cy="{Y(max(v, ys[0])):.1f}" r="6" fill="{color}"/>')
    label = f"{shape}, {'local disk' if where.startswith('local') else 'floci S3'}"
    out.append(f'<line x1="{L + 20}" y1="{ly}" x2="{L + 70}" y2="{ly}" stroke="{color}" stroke-width="4" stroke-dasharray="{dash}"/>')
    out.append(f'<text x="{L + 80}" y="{ly + 8}">{label}</text>')
    ly += 34
out.append("</svg>")
(OUT / "bench.svg").write_text("\n".join(out))
