#!/usr/bin/env python3
"""Download the source h5ads of the manifests. Resumable; re-run to continue."""

import argparse
import json
import shutil
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from itertools import accumulate
from pathlib import Path

from config import H5AD

HERE = Path(__file__).parent
MANIFESTS = sorted((HERE / "ext/cellxgene-census2-prototype/bulk-ingest-nf/manifests").glob("*.jsonl"), key=lambda m: "harness" not in m.name)


def fetch(rec: dict, dest: Path, tries: int = 5) -> str:
    for i in range(tries):  # timeouts and dropped connections are common; resume
        try:
            return fetch_once(rec, dest)
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(30 * (i + 1))


def fetch_once(rec: dict, dest: Path) -> str:
    out = dest / f"{rec['dataset_version_id']}.h5ad"
    part = out.with_suffix(".h5ad.part")
    if out.exists() and out.stat().st_size == rec["filesize"]:
        return f"skip {out.name}"
    have = part.stat().st_size if part.exists() else 0
    req = urllib.request.Request(rec["url"], headers={"Range": f"bytes={have}-"})
    with urllib.request.urlopen(req, timeout=60) as r, part.open("ab") as f:
        if r.status != 206:  # server ignored the range: start over
            f.truncate(0)
        shutil.copyfileobj(r, f, 1 << 24)
    if part.stat().st_size != rec["filesize"]:
        raise RuntimeError(f"size mismatch {part.name}")
    part.rename(out)
    return f"done {out.name}"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("manifests", nargs="*", type=Path, default=MANIFESTS)
    p.add_argument("--dest", type=Path, default=H5AD)
    p.add_argument("--jobs", type=int, default=4)
    p.add_argument("--max-gib", type=float, help="subset: first datasets up to this total")
    p.add_argument("--smallest", type=int, help="subset: the N smallest datasets (tiny profile)")
    a = p.parse_args()

    recs = [json.loads(line) for m in a.manifests for line in m.open() if line.strip()]
    if a.max_gib:
        cum = list(accumulate(r["filesize"] for r in recs))
        recs = [r for r, c in zip(recs, cum) if c <= a.max_gib * 2**30]
    if a.smallest:
        recs = sorted(recs, key=lambda r: r["filesize"])[: a.smallest]
    a.dest.mkdir(parents=True, exist_ok=True)
    need = sum(r["filesize"] for r in recs if not (a.dest / f"{r['dataset_version_id']}.h5ad").exists())
    free = shutil.disk_usage(a.dest).free
    print(f"{len(recs)} datasets, {need / 2**30:.1f} GiB to fetch, {free / 2**30:.1f} GiB free")
    if need > free:
        sys.exit("not enough disk space: use --dest on a larger disk")

    errors = 0
    with ThreadPoolExecutor(a.jobs) as pool:
        for rec, fut in [(r, pool.submit(fetch, r, a.dest)) for r in recs]:
            try:
                print(fut.result(), flush=True)
            except Exception as e:
                errors += 1
                print(f"FAIL {rec['dataset_version_id']}: {e}", flush=True)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
