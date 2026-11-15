#!/usr/bin/env python3
"""One parent Zarr store over the stores of a manifest: data/parent.zarr/<id> -> data/zarr/<id>.zarr
(symlinks, no copy), with the whole tree's metadata consolidated into the root zarr.json."""

import json
import sys
import time
from pathlib import Path

import zarr

HERE = Path(__file__).parent.resolve()
manifest = Path(sys.argv[1] if len(sys.argv) > 1 else HERE / "subsets/4g.jsonl")
parent = HERE / "data/parent.zarr"
zarr.open_group(str(parent), mode="w")
for line in manifest.open():
    dvid = json.loads(line)["dataset_version_id"]
    (parent / dvid).symlink_to(HERE / "data/zarr" / f"{dvid}.zarr")
t = time.monotonic()
zarr.consolidate_metadata(str(parent))
size = (parent / "zarr.json").stat().st_size
print(f"{parent}: {len(list(parent.iterdir())) - 1} stores, root zarr.json {size / 2**20:.1f} MiB, "
      f"consolidated in {time.monotonic() - t:.1f} s")
