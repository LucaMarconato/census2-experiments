#!/bin/sh
# The spike paths on the 21-store 4GB set, for the Icechunk comparison (same stores as icechunk_bench.py).
set -e
cd "$(dirname "$0")/.."
T=$PWD/ext/spike-obs/census2-sdk/tools
cd $T && $OLDPWD/spike/.venv/bin/python -m bench.matrix --catalogs $OLDPWD/results/spike/catalogs-4GB --sizes 21 \
  --shapes single,corpus_obs,count_donor:cell_type,count_donor:all --vias stores,table,sql \
  --obs-table "$OLDPWD/results/spike/tables/obs-{size}" --workers 1,8 --repeats 3 \
  --cell-type neutrophil --queries results/obs_duckdb/queries.json --where laptop-local \
  --out $OLDPWD/results/spike/bench-21.jsonl
