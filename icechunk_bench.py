#!/usr/bin/env python3
"""Icechunk vs plain Zarr stores: the same AnnData-Zarr stores, read the same way.

build: copy the stores of a manifest, key by key, into one Icechunk repo (one group per
dataset), commit, and tag the commit as a release. Storage is local (<data>/icechunk) or
floci (s3://icechunk/census2 on 127.0.0.1:4566, dummy creds). No account, no network.
A build replaces any earlier repo.
bench: open / corpus_obs / corpus_x / single over the repo, over the plain stores, and over
one parent Zarr store with consolidated metadata (parent_zarr.py),
one new process per run. Writes --out (default <results>/icechunk/bench-<where>.jsonl), anew unless --append.

    python icechunk_bench.py build --where local
    python icechunk_bench.py bench --where local --shapes open,corpus_obs,corpus_x
"""

import argparse
import json
import os
import resource
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from config import DATA, HERE, RESULTS, SUBSETS

TAG = "release"


def storage(where: str):
    import icechunk as ic

    if where == "local":
        return ic.local_filesystem_storage(str(DATA / "icechunk"))
    return ic.s3_storage(
        bucket="icechunk", prefix="census2", endpoint_url=os.environ.get("AWS_ENDPOINT_URL", "http://127.0.0.1:4566"),
        allow_http=True, region="us-east-1", force_path_style=True,
        access_key_id="test", secret_access_key="test",
    )  # fmt: skip


def ids(manifest: Path) -> list[str]:
    return [json.loads(line)["dataset_version_id"] for line in manifest.open() if line.strip()]


def build(where: str, manifest: Path) -> None:
    import icechunk as ic
    import zarr
    from zarr.core.buffer import cpu
    from zarr.core.sync import sync

    if where == "floci":
        sh = f". {HERE}/floci/env.sh && (aws s3 mb s3://icechunk || true) && aws s3 rm --quiet --recursive s3://icechunk/census2"
        subprocess.run(["sh", "-c", sh], check=True)
    else:
        shutil.rmtree(DATA / "icechunk", ignore_errors=True)
    repo = ic.Repository.create(storage(where))
    session = repo.writable_session("main")
    store = session.store
    zarr.open_group(store, mode="w")  # the root group
    t0, nbytes = time.monotonic(), 0
    for dvid in ids(manifest):
        root = DATA / "zarr" / f"{dvid}.zarr"
        # metadata first, parents before children: Icechunk needs the node before its chunks
        files = sorted((p for p in root.rglob("*") if p.is_file()),
                       key=lambda p: (p.name != "zarr.json", len(p.parts), str(p)))  # fmt: skip
        for f in files:
            data = f.read_bytes()
            nbytes += len(data)
            sync(store.set(f"{dvid}/{f.relative_to(root).as_posix()}", cpu.Buffer.from_bytes(data)))
    snap = session.commit(f"stores of {manifest.name}")
    repo.create_tag(TAG, snap)
    print(json.dumps({"where": where, "stores": len(ids(manifest)), "gib": round(nbytes / 2**30, 2),
                      "build_seconds": round(time.monotonic() - t0, 1), "snapshot": snap}))  # fmt: skip


def _counting():
    """The prototype's CountingStore and its counter (bench/run.py), loaded by path."""
    import importlib.util

    tools = HERE / "ext/cellxgene-census2-prototype/census2-sdk/tools"
    spec = importlib.util.spec_from_file_location("proto_run", tools / "bench/run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.CountingStore, mod.COUNTER


def base_store(backend: str, where: str, dvid: str | None = None):
    """The zarr Store of a backend: one store per dataset (zarr), or one for all (parent, icechunk)."""
    import zarr

    if backend == "icechunk":
        import icechunk as ic

        return ic.Repository.open(storage(where)).readonly_session(tag=TAG).store
    if where == "local":
        path = DATA / ("parent.zarr" if backend == "parent" else f"zarr/{dvid}.zarr")
        return zarr.storage.LocalStore(str(path), read_only=True)
    import obstore.store

    url = "s3://parent/" if backend == "parent" else f"s3://s-{dvid}/{dvid}.zarr"
    return zarr.storage.ObjectStore(obstore.store.from_url(url), read_only=True)


def run(backend: str, where: str, shape: str, workers: int, manifest: Path, count: bool = False) -> dict:
    """One run. With `count`, wrap the store to count reads (slower: a timed run does not count)."""
    import zarr
    from anndata.io import read_elem

    Counting, counter = _counting()
    wrap = Counting if count else (lambda s: s)
    t0 = time.monotonic()
    root = None
    if backend == "icechunk":
        root = wrap(base_store(backend, where))  # open each dataset by path: root[id] is slow here
    if backend == "parent":  # consolidated metadata of the whole tree in the root zarr.json
        root = zarr.open_group(wrap(base_store(backend, where)), mode="r")
    opened = counter.requests
    stores = ids(manifest)
    t1 = time.monotonic()

    def one(dvid: str) -> int:
        if backend == "icechunk":
            g = zarr.open_group(root, path=dvid, mode="r")
        elif backend == "parent":
            g = root[dvid]
        else:
            g = zarr.open_group(wrap(base_store(backend, where, dvid)), mode="r")
        if shape == "open":
            return 0
        if shape == "corpus_obs":
            return len(read_elem(g["obs"]))
        if shape == "count_cell_type":  # an obs filter: no pushdown, so read the column and test it
            col = read_elem(g["obs"]["cell_type"])
            return int((col == "neutrophil").sum())
        x = g["X"]
        rows = x["indptr"].shape[0] - 1
        for name in ("indptr", "indices", "data"):
            a = x[name]
            step = (a.shards or a.chunks)[0]
            for start in range(0, a.shape[0], step):
                a[start : start + step]
        return rows

    pick = stores[:1] if shape == "single" else stores
    with ThreadPoolExecutor(workers) as pool:
        cells = sum(pool.map(one, pick))
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20
    return {"backend": backend, "where": where, "shape": shape, "workers": workers,
            "stores": len(pick), "cells": cells, "open_seconds": round(t1 - t0, 3),
            "query_seconds": round(time.monotonic() - t1, 3), "peak_rss_mb": round(peak, 1),
            **({"requests_open": opened, "requests": counter.requests, "mb": round(counter.nbytes / 2**20, 2)} if count else {}),
            "zarr": zarr.__version__, "status": "ok"}  # fmt: skip


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("cmd", choices=["build", "bench", "one"])
    p.add_argument("--where", default="local", choices=["local", "floci"])
    p.add_argument("--manifest", type=Path, default=SUBSETS / "4GB.jsonl")
    p.add_argument("--shapes", default="open,count_cell_type,corpus_obs")
    p.add_argument("--workers", default="8")
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--backend", default="icechunk")
    p.add_argument("--backends", default="zarr,parent,icechunk", help="for bench")
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--append", action="store_true", help="keep the records already in --out")
    p.add_argument("--endpoint", default=None, help="override the floci endpoint")
    p.add_argument("--label", default="", help="a free label stored in each record")
    p.add_argument("--count", action="store_true", help="count reads (one extra run per cell in bench)")
    a = p.parse_args()
    if a.where == "floci":
        env = subprocess.run(["sh", "-c", f". {HERE}/floci/env.sh && env -0"], capture_output=True, text=True).stdout
        os.environ.update(kv.split("=", 1) for kv in env.split("\0") if "=" in kv)
        if a.endpoint:  # e.g. latency_proxy.py in front of floci
            os.environ["AWS_ENDPOINT_URL"] = a.endpoint
    if a.cmd == "build":
        build(a.where, a.manifest)
    elif a.cmd == "one":
        print(json.dumps(run(a.backend, a.where, a.shapes, int(a.workers), a.manifest, a.count)))
    else:
        a.out = a.out or RESULTS / f"icechunk/bench-{a.where}.jsonl"
        a.out.parent.mkdir(parents=True, exist_ok=True)
        if not a.append:
            a.out.unlink(missing_ok=True)
        for shape in a.shapes.split(","):
            for w in a.workers.split(","):
                for backend in a.backends.split(","):
                    for r in range(a.repeats + 1):
                        cmd = [sys.executable, __file__, "one", "--backend", backend, "--where", a.where,
                               "--shapes", shape, "--workers", w, "--manifest", str(a.manifest)]  # fmt: skip
                        if a.endpoint:
                            cmd += ["--endpoint", a.endpoint]
                        if r == a.repeats:  # the last run counts reads; it is not timed
                            cmd.append("--count")
                        rec = json.loads(subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.splitlines()[-1])
                        rec["repeat"] = r
                        rec["counted"] = r == a.repeats
                        rec["label"] = a.label
                        with a.out.open("a") as fh:
                            fh.write(json.dumps(rec) + "\n")
                        print(shape, w, backend, r, rec["query_seconds"], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
