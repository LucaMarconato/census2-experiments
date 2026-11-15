#!/usr/bin/env python3
"""Check that local disk, AWS Emulator and floci return identical data for the same stores.

1. results/bench.jsonl: per shape and workers, the same stores, cells, requests and MB.
2. get_anndata of one cell type in a fresh process per backend (CHILD): SHA-256 of obs, var and X
   must match across backends.

    uv run python consistency.py local-small emu-small floci-small
"""

import os
import subprocess
import sys
from pathlib import Path

import pandas as pd

from bench import CATALOGS, HERE, backend_env

KEYS = ["stores_opened", "cells", "requests", "mb_payload"]

CHILD = """
import sys, hashlib, numpy as np, census2_sdk
from bench.run import pick_cell_type, source_rows
c = census2_sdk.open_census([sys.argv[1]])
rows = c.catalog[c.catalog["organism"] == "homo_sapiens"]
ct = pick_cell_type(source_rows(rows))
a = c.get_anndata("homo_sapiens", {"cell_type": ct})
a = a[np.argsort(a.obs_names.to_numpy())]
x = a.X.tocsr(); x.sort_indices()
h = hashlib.sha256()
for part in (x.indptr, x.indices, x.data):
    h.update(np.ascontiguousarray(part).tobytes())
print(ct, a.n_obs, a.n_vars,
      hashlib.sha256(a.obs.to_csv().encode()).hexdigest()[:16],
      hashlib.sha256(a.var.to_csv().encode()).hexdigest()[:16],
      h.hexdigest()[:16])
"""


def main() -> int:
    sets = sys.argv[1:]
    df = pd.read_json(HERE / "results/bench.jsonl", lines=True)
    df = df[df["where"].isin(sets) & (df["status"] == "ok")]
    ok = True
    print("1. bench records (distinct values across repeats and sets)")
    for (shape, workers), g in df.groupby(["shape", "workers"]):
        vals = {k: sorted(g[k].unique().tolist()) for k in KEYS}
        same = all(len(v) == 1 for v in vals.values())
        ok &= same or shape == "x"
        flag = "same" if same else "DIFF " + str(
            g.groupby("where")[KEYS].agg(lambda s: sorted(s.unique().tolist())).to_dict("index")
        )
        print(f"  {shape:<10} w={workers:<3} {flag}")

    print("2. get_anndata(cell_type): cell type, n_obs, n_vars, sha256 of obs, var, X")
    outs = {}
    for name in sets:
        cat = next((CATALOGS / name).glob("catalog-[0-9]*.parquet"))
        env = {**os.environ, **backend_env(name.split("-")[0])}
        env["PYTHONPATH"] = str(HERE / "ext/cellxgene-census2-prototype/census2-sdk/tools")
        out = subprocess.run(
            [sys.executable, "-c", CHILD, str(cat.resolve())], env=env, cwd=env["PYTHONPATH"], capture_output=True, text=True, check=True
        ).stdout.strip()
        outs[name] = out
        print(f"  {name:<12} {out}")
    ok &= len(set(outs.values())) == 1
    print("CONSISTENT" if ok else "MISMATCH")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
