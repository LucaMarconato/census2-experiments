#!/usr/bin/env python3
"""Median seconds of the spike head-to-head, stores vs Iceberg table vs DuckDB (results/spike/bench-<N>.md)."""

import sys

import pandas as pd

src = sys.argv[1] if len(sys.argv) > 1 else "results/spike/bench-44.jsonl"
df = pd.read_json(src, lines=True)
df = df[df.status == "ok"]
df["shape"] = df["shape"].where(df["label"].isna(), df["shape"] + ":" + df["label"].astype(str))
t = df.pivot_table(index=["shape", "workers"], columns="via", values="query_seconds", aggfunc="median")
t = t[["stores", "table", "sql"]].rename(columns={"table": "iceberg", "sql": "duckdb"})
t["stores/duckdb"] = t["stores"] / t["duckdb"]
cells = df[df.via == "stores"].groupby(["shape", "workers"])["cells"].median().astype("Int64")
t.insert(0, "cells", cells)
md = t.reset_index().to_markdown(index=False, floatfmt=".2f", intfmt=",")
open(src.replace(".jsonl", ".md"), "w").write(md + "\n")
print(md)
