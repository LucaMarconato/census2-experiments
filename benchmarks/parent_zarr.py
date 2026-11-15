#!/usr/bin/env python3
"""One parent Zarr store over the stores of a manifest: <data>/parent.zarr/<id> -> <data>/zarr/<id>.zarr
(symlinks, no copy), with the whole tree's metadata consolidated into the root zarr.json."""

import json
import shutil
import sys
import time
from pathlib import Path

import zarr

from config import DATA, SUBSETS

manifest = Path(sys.argv[1]) if len(sys.argv) > 1 else SUBSETS / "4GB.jsonl"
parent = DATA / "parent.zarr"
shutil.rmtree(parent, ignore_errors=True)  # links only: the stores stay
zarr.open_group(str(parent), mode="w")
for line in manifest.open():
    dvid = json.loads(line)["dataset_version_id"]
    (parent / dvid).symlink_to((DATA / "zarr" / f"{dvid}.zarr").resolve())
t = time.monotonic()
zarr.consolidate_metadata(str(parent))
size = (parent / "zarr.json").stat().st_size
print(f"{parent}: {len(list(parent.iterdir())) - 1} stores, root zarr.json {size / 2**20:.1f} MiB, "
      f"consolidated in {time.monotonic() - t:.1f} s")
