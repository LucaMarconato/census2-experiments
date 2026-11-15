#!/usr/bin/env python3
"""Separate stores vs parent store vs Icechunk (copied chunks, and virtual references): <results>/icechunk/bench.md.

Per place (local, floci, floci +N ms) and shape: median seconds of the timed runs (open + query) and
the requests of the counted run: HTTP requests on floci (counted by the proxy), zarr-level reads on
local disk. Each cell: separate stores / parent store / Icechunk / Icechunk virtual.
"""

import pandas as pd

from config import RESULTS

D = RESULTS / "icechunk"
df = pd.concat(pd.read_json(f, lines=True) for f in sorted(D.glob("bench-*.jsonl")))
df["place"] = df["where"] + df["delay_ms"].map(lambda d: f" +{d:g} ms" if d else "")
df["seconds"] = df["open_seconds"] + df["query_seconds"]
df["requests"] = df["http_requests"] if "http_requests" in df else float("nan")
df["requests"] = df["requests"].fillna(df["zarr_reads"])
key, order = ["place", "shape"], ["zarr", "parent", "icechunk", "virtual"]
secs = df[~df.counted].pivot_table(index=key, columns="backend", values="seconds", aggfunc="median", sort=False)
reqs = df[df.counted].pivot_table(index=key, columns="backend", values="requests", aggfunc="median", sort=False)
t = pd.DataFrame({
    "requests": reqs[order].apply(lambda r: " / ".join(f"{v:,.0f}" for v in r), axis=1),
    "seconds": secs[order].apply(lambda r: " / ".join(f"{v:.3f}" for v in r), axis=1),
    "fastest": secs[order].idxmin(axis=1).replace({"zarr": "separate"}),
}).reset_index()
md = "Each cell: separate stores / parent store / Icechunk / Icechunk virtual\n\n" + t.to_markdown(index=False)
(D / "bench.md").write_text(md + "\n")
print(md)
