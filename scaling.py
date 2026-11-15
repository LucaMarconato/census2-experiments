#!/usr/bin/env python3
"""Benchmark shapes against the number of stores N, on local disk (and floci for small N).

Real stores up to all of data/zarr; beyond that, the prototype's copy method (bench.catalogs):
copy k of a store is a symlink data/copies/cKK/<id>.zarr -> data/zarr/<id>.zarr, with its own
dataset_id in the catalog, so it costs no disk. The catalog (one Parquet row per store) is what the
SDK opens, so each size N gets its own: catalog-N.parquet = the first N rows of the expanded
catalog (floci: of the floci-4GB catalog). Appends to results/scaling/bench.jsonl.

    uv run python scaling.py --sizes 5,10,20,44,93,200,500,1000,2000
"""

import argparse
import importlib.util
import os
import subprocess
import sys

import pandas as pd

from bench import CATALOGS, HERE, TOOLS, backend_env, catalog

# the prototype's bench/catalogs.py, by path: this repo's bench.py takes the name `bench`
_spec = importlib.util.spec_from_file_location("proto_catalogs", TOOLS / "bench/catalogs.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
expand = _mod.expand

OUT = HERE / "results/scaling"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sizes", default="5,10,20,44,103,200,500,1000,2000")
    p.add_argument("--shapes", default="single,cell_type,open,corpus_obs")
    p.add_argument("--workers", default="8,32")
    p.add_argument("--repeats", type=int, default=2)
    p.add_argument("--floci-sizes", default="5,10,21")
    p.add_argument("--suffix", default="", help="appended to `where`, e.g. -ext")
    p.add_argument("--out", default="bench.jsonl", help="file name under results/scaling")
    a = p.parse_args()
    sizes = [int(s) for s in a.sizes.split(",")]

    # Real stores, in the order of the local-all catalog; rebuild it if stores were added.
    for f in (CATALOGS / "local-all").glob("catalog-*.parquet"):
        if int(f.stem.split("-")[1]) != len(list((HERE / "data/zarr").glob("*.zarr"))):
            f.unlink()
    src = pd.read_parquet(catalog("local-all", dict(os.environ)))
    n_copies = max(0, -(-max(sizes) // len(src)) - 1)
    copies = HERE / "data/copies"
    for k in range(1, n_copies + 1):
        d = copies / f"c{k:02d}"
        d.mkdir(parents=True, exist_ok=True)
        for uri in src["store_uri"]:
            link = d / os.path.basename(str(uri).rstrip("/"))
            if not link.exists():
                link.symlink_to(uri)
    rows = expand(src, str(copies), n_copies)
    cats = OUT / "catalogs-local"
    cats.mkdir(parents=True, exist_ok=True)
    for n in sizes:
        rows.head(n).to_parquet(cats / f"catalog-{n}.parquet")

    # floci: prefixes of the floci-4GB catalog
    fcat = pd.read_parquet(catalog("floci-4GB", {**os.environ, **backend_env("floci")}))
    fsizes = [int(s) for s in a.floci_sizes.split(",") if int(s) <= len(fcat)]
    fcats = OUT / "catalogs-floci"
    fcats.mkdir(parents=True, exist_ok=True)
    for n in fsizes:
        fcat.head(n).to_parquet(fcats / f"catalog-{n}.parquet")

    runs = [("local", cats, sizes), ("floci", fcats, fsizes)]
    for where, d, ns in runs:
        if not ns:
            continue
        env = {**os.environ, **backend_env(where), "PYTHONPATH": str(TOOLS)}
        subprocess.run(
            [sys.executable, "-m", "bench.matrix", "--catalogs", d, "--sizes", ",".join(map(str, ns)),
             "--shapes", a.shapes, "--workers", a.workers, "--repeats", str(a.repeats),
             "--where", f"{where}-scaling{a.suffix}", "--out", OUT / a.out],
            check=True, env=env, cwd=TOOLS,
        )  # fmt: skip
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
