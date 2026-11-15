#!/usr/bin/env python3
"""Convert the h5ads of a manifest to Census 2 Zarr stores. Resumable."""

import argparse
import json
import shutil
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import census2_dataset_writer as w

from config import H5AD

HERE = Path(__file__).parent


def convert(rec: dict, src: Path, dest: Path, refdata: Path) -> str:
    out = dest / f"{rec['dataset_version_id']}.zarr"
    if out.exists() and w.read_summary(str(out)) is not None:  # summary is the last write
        return f"skip {out.name}"
    shutil.rmtree(out, ignore_errors=True)
    t = time.monotonic()
    r = w.create(
        src / f"{rec['dataset_version_id']}.h5ad",
        str(out),
        dataset_id=rec["dataset_id"],
        dataset_version_id=rec["dataset_version_id"],
        refdata=refdata,
    )
    if not r["admitted"]:
        return f"rejected {out.name}: {r['reason']}"
    return f"done {out.name} {time.monotonic() - t:.0f}s"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("manifest", type=Path)
    p.add_argument("--src", type=Path, default=H5AD, help="h5ad directory")
    p.add_argument("--dest", type=Path, default=HERE / "data" / "zarr")
    p.add_argument("--refdata", type=Path, default=HERE / "data" / "refdata")
    p.add_argument("--jobs", type=int, default=2)
    a = p.parse_args()

    recs = [json.loads(line) for line in a.manifest.open() if line.strip()]
    a.dest.mkdir(parents=True, exist_ok=True)
    errors = 0
    with ProcessPoolExecutor(a.jobs) as pool:
        futs = [(r, pool.submit(convert, r, a.src, a.dest, a.refdata)) for r in recs]
        for rec, fut in futs:
            try:
                print(fut.result(), flush=True)
            except Exception as e:
                errors += 1
                print(f"FAIL {rec['dataset_version_id']}: {e!r}", flush=True)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
