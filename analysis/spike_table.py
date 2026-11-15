#!/usr/bin/env python3
"""Median seconds of the spike head-to-head, stores vs Iceberg table vs DuckDB: <results>/spike/bench.md."""

import pandas as pd

from config import RESULTS, scrub

src = RESULTS / "spike/bench.jsonl"
scrub(src)
df = pd.read_json(src, lines=True)
df = df[df.status == "ok"]
if "label" in df:
    df["shape"] = df["shape"].where(df["label"].isna(), df["shape"] + ":" + df["label"].astype(str))
t = df.pivot_table(index=["shape", "workers"], columns="via", values="query_seconds", aggfunc="median")
t = t[["stores", "table", "sql"]].rename(columns={"table": "iceberg", "sql": "duckdb"})
t["stores/duckdb"] = t["stores"] / t["duckdb"]
cells = df[df.via == "stores"].groupby(["shape", "workers"])["cells"].median().astype("Int64")
t.insert(0, "cells", cells)
md = t.reset_index().to_markdown(index=False, floatfmt=".2f", intfmt=",")
src.with_suffix(".md").write_text(md + "\n")
print(md)
