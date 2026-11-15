#!/usr/bin/env python3
"""Write <subsets>/NAME.jsonl: the finished h5ads or Zarr stores of a manifest, in order, up to a size cap.

    python prep/subset.py all --source h5ad                       # every downloaded h5ad
    python prep/subset.py 4GB --from all --max-gib 4 --fill       # stores that fit in 4 GiB
"""

import argparse
import json
from pathlib import Path

from config import DATA, H5AD, SUBSETS
from download import MANIFESTS


def size(path: Path, rec: dict) -> int | None:
    """Bytes of a finished file or store, else None."""
    if path.suffix == ".h5ad":
        ok = path.exists() and path.stat().st_size == rec["filesize"]
        return rec["filesize"] if ok else None
    root = path / "zarr.json"  # the summary record is the writer's last write
    if not (root.exists() and "cellxgene-census2" in root.read_text()):
        return None
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("name")
    p.add_argument("--source", choices=["h5ad", "zarr"], default="zarr")
    p.add_argument("--from", dest="src", help="a subset name; default: the prototype's manifests")
    p.add_argument("--max-gib", type=float, default=1e6)
    p.add_argument("--max-store-mib", type=float, help="skip larger stores")
    p.add_argument("--fill", action="store_true", help="skip what does not fit, do not stop")
    a = p.parse_args()

    src = [SUBSETS / f"{a.src}.jsonl"] if a.src else MANIFESTS
    d, ext = (H5AD, ".h5ad") if a.source == "h5ad" else (DATA / "zarr", ".zarr")
    total, keep = 0, []
    for rec in (json.loads(line) for m in src for line in m.open() if line.strip()):
        n = size(d / f"{rec['dataset_version_id']}{ext}", rec)
        if n is None or (a.max_store_mib and n > a.max_store_mib * 2**20):
            continue
        if total + n > a.max_gib * 2**30:
            if a.fill:
                continue
            break
        total += n
        keep.append(rec)
    out = SUBSETS / f"{a.name}.jsonl"
    out.write_text("".join(json.dumps(r) + "\n" for r in keep))
    cells = sum(r["cell_count"] for r in keep)
    print(f"{len(keep)} datasets, {total / 2**30:.2f} GiB {ext}, {cells:,} cells -> {out}")


if __name__ == "__main__":
    main()
