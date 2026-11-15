#!/usr/bin/env python3
"""Run the prototype benchmark matrix (census2-sdk/tools/bench) on each store set.

Per set: build its catalog (build_catalog.py, <results>/catalogs/<set>/), load the backend env,
run bench.matrix: each shape x workers x repeat in a new process (no cache carries over).
Shapes: single (get_anndata of one dataset), cell_type (get_anndata of the cell type in ~15% of
datasets), open (open every store), corpus_obs (read all obs), corpus_x (read all X, keep nothing).
Each record: catalog and query seconds, stores, cells, requests, MB read, peak RSS, status.
Writes <results>/bench.jsonl (anew); table.py makes the table of medians.

A set is <backend>-<stores>: backend local (<data>/zarr) or floci (floci/start.sh); stores all or
4GB (<subsets>/4GB.jsonl).
Paths per profile: config.py.
On S3 each store has its own bucket, s3://s-<id>/<id>.zarr.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd

from config import DATA, HERE, RESULTS, SUBSETS

TOOLS = HERE / "ext/cellxgene-census2-prototype/census2-sdk/tools"
CATALOGS = RESULTS / "catalogs"


def backend_env(backend: str) -> dict[str, str]:
    if backend == "local":
        return {}
    out = subprocess.run(
        ["sh", "-c", f". {HERE}/{backend}/env.sh && env -0"],
        capture_output=True, text=True, check=True,
    ).stdout  # fmt: skip
    return dict(kv.split("=", 1) for kv in out.split("\0") if "=" in kv)


def ids(manifest: Path) -> set[str]:
    return {json.loads(line)["dataset_version_id"] for line in manifest.open() if line.strip()}


def catalog(name: str, env: dict[str, str]) -> Path:
    """Build the catalog of a store set as results/catalogs/<name>/catalog-<N>.parquet.

    Cached: reused if present. local-all is rebuilt (build_catalog.py scans every store in
    data/zarr) when N no longer equals the number of stores there, e.g. after more conversions."""
    d = CATALOGS / name
    d.mkdir(parents=True, exist_ok=True)
    if found := sorted(d.glob("catalog-*.parquet")):
        if not (name == "local-all" and int(found[0].stem.split("-")[1]) != len(list((DATA / "zarr").glob("*.zarr")))):
            return found[0]
        found[0].unlink()  # stores were added: rebuild
    backend, stores = name.split("-")
    keep = None if stores == "all" else ids(SUBSETS / f"{stores}.jsonl")
    if backend == "local":
        prefixes = [f"{(DATA / 'zarr').resolve()}/"]
    else:
        prefixes = [f"s3://s-{i}/" for i in sorted(keep)]
    parts = []
    for k, prefix in enumerate(prefixes):
        src = d / f"source-{k}.parquet"
        subprocess.run([sys.executable, TOOLS / "build_catalog.py", prefix, src], check=True, env=env)
        parts.append(pd.read_parquet(src))
    rows = pd.concat(parts, ignore_index=True)
    if keep is not None:  # same rows, same order on every backend
        rows = rows[rows["dataset_version_id"].isin(keep)]
        rows = rows.sort_values("dataset_version_id", ignore_index=True)
    out = d / f"catalog-{len(rows)}.parquet"
    rows.to_parquet(out)
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sets", default="local-all,local-4GB,floci-4GB")
    p.add_argument("--shapes", default="single,cell_type,open,corpus_obs,corpus_x")
    p.add_argument("--workers", default="1,8")
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--out", type=Path, default=RESULTS / "bench.jsonl")
    p.add_argument("--catalogs-only", action="store_true", help="build the catalogs, run nothing")
    a = p.parse_args()

    if not a.catalogs_only:
        a.out.unlink(missing_ok=True)
    for name in a.sets.split(","):
        env = {**os.environ, **backend_env(name.split("-")[0])}
        env["PYTHONPATH"] = str(TOOLS)
        cat = catalog(name, env)
        if a.catalogs_only:
            continue
        size = cat.stem.split("-")[1]
        subprocess.run(
            [sys.executable, "-m", "bench.matrix", "--catalogs", cat.parent, "--sizes", size,
             "--shapes", a.shapes, "--workers", a.workers, "--repeats", str(a.repeats),
             "--where", name, "--out", a.out.resolve()],
            check=True, env=env, cwd=TOOLS,
        )  # fmt: skip
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
