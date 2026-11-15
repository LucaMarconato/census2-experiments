#!/usr/bin/env python3
"""Summarize results/bench.jsonl as a markdown table of medians (results/bench.md)."""

import sys
from pathlib import Path

import pandas as pd

src = Path(sys.argv[1] if len(sys.argv) > 1 else "results/bench.jsonl")
df = pd.read_json(src, lines=True)
ok = df[df["status"] == "ok"]
t = (
    ok.groupby(["where", "shape", "workers"], sort=False)
    .agg(
        stores=("stores_opened", "median"),
        cells=("cells", "median"),
        seconds=("query_seconds", "median"),
        requests=("requests", "median"),
        mb=("mb_payload", "median"),
        rss_mb=("peak_rss_mb", "median"),
        runs=("status", "size"),
    )
    .reset_index()
    .astype({"stores": int, "cells": int, "requests": int})
)
md = t.rename(columns={"shape": "query"}).to_markdown(index=False, floatfmt=".2f", intfmt=",")
if bad := len(df) - len(ok):
    md += f"\n\n{bad} runs not ok: " + ", ".join(df.loc[df.status != "ok", "status"].unique())
out = src.with_suffix(".md")
out.write_text(md + "\n")
print(md)
