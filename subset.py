#!/usr/bin/env python3
"""Write a manifest of the finished h5ads or Zarr stores in DIR, in order, up to a size cap."""

import argparse
import json
from pathlib import Path

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
    p.add_argument("dir", type=Path)
    p.add_argument("--max-gib", type=float, default=50)
    p.add_argument("--from", dest="src", type=Path, nargs="*", default=MANIFESTS)
    p.add_argument("--max-store-mib", type=float, help="skip larger stores")
    p.add_argument("--fill", action="store_true", help="skip what does not fit, do not stop")
    p.add_argument("--out", type=Path, default=Path("subsets/50GB.jsonl"))
    a = p.parse_args()

    ext = ".zarr" if any(a.dir.glob("*.zarr")) else ".h5ad"
    total, keep = 0, []
    for rec in (json.loads(line) for m in a.src for line in m.open() if line.strip()):
        n = size(a.dir / f"{rec['dataset_version_id']}{ext}", rec)
        if n is None or (a.max_store_mib and n > a.max_store_mib * 2**20):
            continue
        if total + n > a.max_gib * 2**30:
            if a.fill:
                continue
            break
        total += n
        keep.append(rec)
    a.out.write_text("".join(json.dumps(r) + "\n" for r in keep))
    cells = sum(r["cell_count"] for r in keep)
    print(f"{len(keep)} datasets, {total / 2**30:.1f} GiB {ext}, {cells:,} cells -> {a.out}")


if __name__ == "__main__":
    main()
