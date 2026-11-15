#!/usr/bin/env python3
"""Icechunk vs plain Zarr stores: the same AnnData-Zarr stores, read the same way.

build: two Icechunk repos over the stores of a manifest, one group per dataset, each committed
and tagged as a release. `icechunk` copies every chunk into the repo. `virtual` copies only the
metadata and points each chunk at the file of the plain store (a virtual reference): no data is
duplicated, so it is the cheap way to put Icechunk over existing stores. Storage is local
(<data>/icechunk, <data>/icechunk-virtual) or floci (s3://icechunk/census2, census2-virtual on
127.0.0.1:4566, dummy creds). No account, no network. A build replaces any earlier repo.
bench: the shapes over the two repos (icechunk, virtual), over the plain stores (zarr), and over one
parent Zarr store with consolidated metadata (parent, parent_zarr.py), all read with plain zarr +
anndata, one new process per run. Shapes: open (every dataset's group), count_cell_type (read one obs column and
count a value), corpus_obs (all obs), corpus_x (all X, shard by shard).
Per shape, backend and delay: --repeats timed runs, then one counted run, not timed. On floci the
counted run goes through latency_proxy.py, which counts the HTTP requests: the true storage round
trips (Icechunk serves metadata from its snapshot, so zarr-level reads overstate it). --delays-ms
adds that delay per request to every run (the proxy on :4567 in front of floci).
Writes --out (default <results>/icechunk/bench-<where>.jsonl, or bench-latency.jsonl with delays),
anew unless --append.

    python benchmarks/icechunk_bench.py build --where local
    python benchmarks/icechunk_bench.py bench --where floci --delays-ms 10,50
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
PROXY_PORT = 4567


S3 = {"region": "us-east-1", "allow_http": True, "force_path_style": True}
KEYS = {"access_key_id": "test", "secret_access_key": "test"}  # dummy: floci accepts any


def endpoint() -> str:
    return os.environ.get("AWS_ENDPOINT_URL", "http://127.0.0.1:4566")


def storage(where: str, virtual: bool = False):
    import icechunk as ic

    if where == "local":
        return ic.local_filesystem_storage(str(DATA / ("icechunk-virtual" if virtual else "icechunk")))
    prefix = "census2-virtual" if virtual else "census2"
    return ic.s3_storage(bucket="icechunk", prefix=prefix, endpoint_url=endpoint(), **S3, **KEYS)


def container(where: str):
    """Where the virtual chunks live, the plain stores: (url prefix, repo config, credentials).

    The config is passed at every open too, so the chunk reads use the endpoint of this run (the proxy)."""
    import icechunk as ic

    if where == "local":
        root = (DATA / "zarr").resolve()
        prefix, store, cred = f"file://{root}/", ic.local_filesystem_store(str(root)), ic.Credentials.LocalFileSystemAccess()
    else:
        prefix, store = "s3://stores/", ic.s3_store(endpoint_url=endpoint(), s3_compatible=True, **S3)
        cred = ic.s3_credentials(**KEYS)
    config = ic.RepositoryConfig.default()
    config.set_virtual_chunk_container(ic.VirtualChunkContainer(prefix, store))
    return prefix, config, ic.containers_credentials({prefix: cred})


def ids(manifest: Path) -> list[str]:
    return [json.loads(line)["dataset_version_id"] for line in manifest.open() if line.strip()]


def build(where: str, manifest: Path, virtual: bool) -> None:
    import icechunk as ic
    import zarr
    from zarr.core.buffer import cpu
    from zarr.core.sync import sync

    if where == "floci":
        at = "census2-virtual" if virtual else "census2"
        sh = f". {HERE}/floci/env.sh && (aws s3 mb s3://icechunk || true) && aws s3 rm --quiet --recursive s3://icechunk/{at}/"
        subprocess.run(["sh", "-c", sh], check=True)
    else:
        shutil.rmtree(DATA / ("icechunk-virtual" if virtual else "icechunk"), ignore_errors=True)
    prefix, config, creds = container(where) if virtual else (None, None, None)
    repo = ic.Repository.create(storage(where, virtual), config, authorize_virtual_chunk_access=creds)
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
            rel = f.relative_to(root).as_posix()
            if virtual and f.name != "zarr.json":  # a chunk (a whole shard file): reference it, do not copy
                store.set_virtual_ref(f"{dvid}/{rel}", f"{prefix}{dvid}.zarr/{rel}", offset=0, length=f.stat().st_size)
                continue
            data = f.read_bytes()
            nbytes += len(data)
            sync(store.set(f"{dvid}/{rel}", cpu.Buffer.from_bytes(data)))
    snap = session.commit(f"stores of {manifest.name}")
    repo.create_tag(TAG, snap)
    print(json.dumps({"repo": "virtual" if virtual else "icechunk", "where": where, "stores": len(ids(manifest)),
                      "copied_gib": round(nbytes / 2**30, 3), "build_seconds": round(time.monotonic() - t0, 1), "snapshot": snap}))  # fmt: skip


def _counting():
    """The prototype's CountingStore and its counter (bench/run.py), loaded by path."""
    import importlib.util

    tools = HERE / "ext/cellxgene-census2-prototype/census2-sdk/tools"
    spec = importlib.util.spec_from_file_location("proto_run", tools / "bench/run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.CountingStore, mod.COUNTER


def base_store(backend: str, where: str, dvid: str | None = None):
    """The zarr Store of a backend: one store per dataset (zarr), or one for all (parent, icechunk, virtual)."""
    import zarr

    if backend == "icechunk":
        import icechunk as ic

        return ic.Repository.open(storage(where)).readonly_session(tag=TAG).store
    if backend == "virtual":
        import icechunk as ic

        _, config, creds = container(where)
        repo = ic.Repository.open(storage(where, virtual=True), config, authorize_virtual_chunk_access=creds)
        return repo.readonly_session(tag=TAG).store
    if where == "local":
        path = DATA / ("parent.zarr" if backend == "parent" else f"zarr/{dvid}.zarr")
        return zarr.storage.LocalStore(str(path), read_only=True)
    import obstore.store

    url = "s3://parent/" if backend == "parent" else f"s3://stores/{dvid}.zarr"
    return zarr.storage.ObjectStore(obstore.store.from_url(url), read_only=True)


def run(backend: str, where: str, shape: str, workers: int, manifest: Path, count: bool = False) -> dict:
    """One run. With `count`, wrap the store to count zarr-level reads (slower: a timed run does not count).

    zarr_format=3 on every open: without it zarr also probes three Zarr v2 keys per group."""
    import zarr
    from anndata.io import read_elem

    Counting, counter = _counting()
    wrap = Counting if count else (lambda s: s)
    t0 = time.monotonic()
    root = None
    if backend in ("icechunk", "virtual"):
        root = wrap(base_store(backend, where))  # open each dataset by path: root[id] is slow here
    if backend == "parent":  # consolidated metadata of the whole tree in the root zarr.json
        root = zarr.open_group(wrap(base_store(backend, where)), mode="r", zarr_format=3)
    opened = counter.requests
    stores = ids(manifest)
    t1 = time.monotonic()

    def one(dvid: str) -> int:
        if backend in ("icechunk", "virtual"):
            g = zarr.open_group(root, path=dvid, mode="r", zarr_format=3)
        elif backend == "parent":
            g = root[dvid]
        else:
            g = zarr.open_group(wrap(base_store(backend, where, dvid)), mode="r", zarr_format=3)
        if shape == "open":
            return 0
        if shape == "corpus_obs":
            return len(read_elem(g["obs"]))
        if shape == "count_cell_type":  # an obs filter: no pushdown, so read the column and test it
            col = read_elem(g["obs"]["cell_type"])
            return int((col == "neutrophil").sum())
        if shape != "corpus_x":
            raise SystemExit(f"unknown shape {shape!r}")
        x = g["X"]
        rows = x["indptr"].shape[0] - 1
        for name in ("indptr", "indices", "data"):
            a = x[name]
            step = (a.shards or a.chunks)[0]
            for start in range(0, a.shape[0], step):
                a[start : start + step]
        return rows

    with ThreadPoolExecutor(workers) as pool:
        cells = sum(pool.map(one, stores))
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20
    return {"backend": backend, "where": where, "shape": shape, "workers": workers,
            "stores": len(stores), "cells": cells, "open_seconds": round(t1 - t0, 3),
            "query_seconds": round(time.monotonic() - t1, 3), "peak_rss_mb": round(peak, 1),
            **({"zarr_reads_open": opened, "zarr_reads": counter.requests, "mb": round(counter.nbytes / 2**20, 2)} if count else {}),
            "zarr": zarr.__version__, "status": "ok"}  # fmt: skip


def proxy(delay_ms: float, count_file: Path) -> subprocess.Popen:
    """latency_proxy.py on PROXY_PORT in front of floci."""
    target = os.environ["AWS_ENDPOINT_URL"].rsplit(":", 1)[1]
    p = subprocess.Popen([sys.executable, str(Path(__file__).with_name("latency_proxy.py")), "--listen", str(PROXY_PORT),
                          "--target", target, "--delay-ms", str(delay_ms), "--count-file", str(count_file)])  # fmt: skip
    time.sleep(1)  # the proxy starts in the background: give it time to listen before a run connects
    return p


def bench(a: argparse.Namespace) -> None:
    delays = [float(d) for d in a.delays_ms.split(",")]
    out = a.out or RESULTS / f"icechunk/bench-{'latency' if any(delays) else a.where}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    if not a.append:
        out.unlink(missing_ok=True)
    count_file = out.with_suffix(".requests")  # the proxy keeps its running total of requests here

    def seen() -> int:
        return int(count_file.read_text()) if count_file.exists() else 0

    for delay in delays:
        if delay and a.where != "floci":
            raise SystemExit("--delays-ms needs --where floci")
        count_file.unlink(missing_ok=True)
        px = proxy(delay, count_file) if a.where == "floci" else None
        via = ["--endpoint", f"http://127.0.0.1:{PROXY_PORT}"]
        try:
            for shape in a.shapes.split(","):
                for w in a.workers.split(","):
                    for backend in a.backends.split(","):
                        for r in range(a.repeats + 1):
                            counted = r == a.repeats  # the last run counts; it is not timed
                            cmd = [sys.executable, __file__, "one", "--backend", backend, "--where", a.where,
                                   "--shapes", shape, "--workers", w, "--manifest", str(a.manifest)]  # fmt: skip
                            if px and (delay or counted):
                                cmd += via
                            if counted:
                                cmd.append("--count")
                            before = seen()
                            rec = json.loads(subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.splitlines()[-1])
                            rec |= {"repeat": r, "counted": counted, "delay_ms": delay}
                            if px and counted:
                                rec["http_requests"] = seen() - before
                            with out.open("a") as fh:
                                fh.write(json.dumps(rec) + "\n")
                            print(shape, w, backend, f"+{delay:g}ms", r, rec["query_seconds"], rec.get("http_requests", ""), flush=True)
        finally:
            if px:
                px.terminate()
                px.wait()
    count_file.unlink(missing_ok=True)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("cmd", choices=["build", "bench", "one"])
    p.add_argument("--where", default="local", choices=["local", "floci"])
    p.add_argument("--manifest", type=Path, default=SUBSETS / "4GB.jsonl")
    p.add_argument("--shapes", default="open,count_cell_type,corpus_obs")
    p.add_argument("--workers", default="8")
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--backends", default="zarr,parent,icechunk,virtual", help="for bench")
    p.add_argument("--delays-ms", default="0", help="for bench on floci: added delay per request, one pass each")
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--append", action="store_true", help="keep the records already in --out")
    p.add_argument("--backend", default="icechunk", help="for one")
    p.add_argument("--endpoint", default=None, help="for one: the S3 endpoint (the proxy)")
    p.add_argument("--count", action="store_true", help="for one: count zarr-level reads")
    a = p.parse_args()
    if a.where == "floci":
        env = subprocess.run(["sh", "-c", f". {HERE}/floci/env.sh && env -0"], capture_output=True, text=True).stdout
        os.environ.update(kv.split("=", 1) for kv in env.split("\0") if "=" in kv)
    if a.cmd == "build":
        build(a.where, a.manifest, virtual=False)
        build(a.where, a.manifest, virtual=True)
    elif a.cmd == "one":
        if a.endpoint:
            os.environ["AWS_ENDPOINT_URL"] = a.endpoint
        print(json.dumps(run(a.backend, a.where, a.shapes, int(a.workers), a.manifest, a.count)))
    else:
        bench(a)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
