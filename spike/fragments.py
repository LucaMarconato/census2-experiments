#!/usr/bin/env python3
"""Write each store's obs as a Parquet fragment (<store>.obs.parquet) with the prototype's code.

Uses the spike branch's writer (`fragment_table`, `write_fragment`, `spike/obs-duckdb`) on the
store's existing `obs` and `X/indptr`, so no store is converted again, and records the fragment
in the store's attributes. spike/bench.sh builds the Iceberg table and queries DuckDB over these.

    uv run --project spike python spike/fragments.py data/zarr
"""

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import census2_dataset_writer as w
import numpy as np
import zarr
from anndata.io import read_elem
from census2_dataset_writer.store_format import FRAGMENT_KEY, SUMMARY_NAMESPACE


def one(store: Path) -> str:
    root = zarr.open_group(str(store), mode="r+")
    if w.read_fragment_record(root) is not None:
        return f"skip {store.name}"
    obs = read_elem(root["obs"])
    indptr = np.asarray(root["X"]["indptr"][...])
    record = w.write_fragment(w.fragment_table(obs, indptr), w.fragment_location(str(store)))
    ns = dict(root.attrs[SUMMARY_NAMESPACE])
    root.update_attributes({SUMMARY_NAMESPACE: {**ns, FRAGMENT_KEY: dict(record)}})
    return f"done {store.name} {record['rows']} rows {record['bytes']} B"


if __name__ == "__main__":
    stores = sorted(Path(sys.argv[1]).glob("*.zarr"))
    with ProcessPoolExecutor(4) as pool:
        for line in pool.map(one, stores):
            print(line, flush=True)
