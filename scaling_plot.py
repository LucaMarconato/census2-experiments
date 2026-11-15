#!/usr/bin/env python3
"""Time vs number of stores, from scaling.py's records (results/scaling/<name>.jsonl).

Takes the 8-worker runs, median query_seconds per where x size x shape:
- <name>.md: that table, plus one of median requests.
- <name>.svg: log-log plot, x = number of stores (5 to 2,000), y = seconds. Solid lines: local
  disk (corpus_obs, open, single); dashed: floci S3 (corpus_obs, open, up to 21 stores).
  Past the real stores the points are symlinked copies. Plain SVG, no plotting library.

    uv run python scaling_plot.py bench-ext
"""

import math
import sys

import pandas as pd

name = sys.argv[1] if len(sys.argv) > 1 else "bench"  # results/scaling/<name>.jsonl -> <name>.md, .svg
d = pd.read_json(f"results/scaling/{name}.jsonl", lines=True)
d = d[(d.status == "ok") & (d.workers == 8)]
t = d.pivot_table(index=["where", "size"], columns="shape", values="query_seconds", aggfunc="median")
r = d.pivot_table(index=["where", "size"], columns="shape", values="requests", aggfunc="median")
md = t.round(2).reset_index().to_markdown(index=False) + "\n\nRequests\n\n" + r.reset_index().to_markdown(index=False)
open(f"results/scaling/{name}.md", "w").write(md + "\n")
print(md)

W, H, L, B = 1600, 900, 140, 110  # canvas, left and bottom margins
xs, ys = (5, 2000), (0.02, 200)
X = lambda v: L + (math.log10(v) - math.log10(xs[0])) / (math.log10(xs[1]) - math.log10(xs[0])) * (W - L - 60)
Y = lambda v: H - B - (math.log10(v) - math.log10(ys[0])) / (math.log10(ys[1]) - math.log10(ys[0])) * (H - B - 80)
sfx = "-ext" if name.endswith("-ext") else ""
DISK = ", external USB SSD" if sfx else ", internal SSD"
REAL = 103 if sfx else 93
series = [("local-scaling", "corpus_obs", "#2F6FDE", ""), ("local-scaling", "open", "#E07A2F", ""),
          ("local-scaling", "single", "#4A5568", ""), ("floci-scaling", "corpus_obs", "#2F6FDE", "8 6"),
          ("floci-scaling", "open", "#E07A2F", "8 6")]  # fmt: skip
out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="Helvetica,Arial" font-size="24">',
       f'<rect width="{W}" height="{H}" fill="#FBFBF8"/>',
       f'<text x="140" y="44" font-size="30" font-weight="bold">Time vs number of stores (8 workers, median){DISK}</text>']  # fmt: skip
for v in (5, 10, 20, 50, 100, 200, 500, 1000, 2000):
    out.append(f'<line x1="{X(v):.0f}" y1="80" x2="{X(v):.0f}" y2="{H - B}" stroke="#E2E0D8"/>')
    out.append(f'<text x="{X(v):.0f}" y="{H - B + 34}" text-anchor="middle">{v}</text>')
for v in (0.1, 1, 10, 100):
    out.append(f'<line x1="{L}" y1="{Y(v):.0f}" x2="{W - 60}" y2="{Y(v):.0f}" stroke="#E2E0D8"/>')
    out.append(f'<text x="{L - 12}" y="{Y(v) + 8:.0f}" text-anchor="end">{v:g} s</text>')
out.append(f'<text x="{(W + L) / 2:.0f}" y="{H - 30}" text-anchor="middle">stores (real up to {REAL}, symlinked copies beyond)</text>')
ly = 110
series = [(w + sfx, sh, c, da) for w, sh, c, da in series]
for where, shape, color, dash in series:
    if (where, shape) not in [(w, s) for w in t.index.get_level_values(0) for s in t.columns]:
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
open(f"results/scaling/{name}.svg", "w").write("\n".join(out))
