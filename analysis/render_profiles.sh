#!/bin/sh
# Flamegraph SVGs from profile.sh's raw stacks (flame.py), in <results>/profiles. No GUI app opens.
set -e
cd "$(dirname "$0")/.."
eval "$(python config.py)"
P=$RESULTS/profiles
f() { python analysis/flame.py "$P/$1.txt" $3 --title "$2" -o "$P/$4.svg"; }
B="share of busy thread samples, idle waits removed"
f local-all-corpus_x-w8     "corpus_x: all X, local disk, 8 workers. $B" --no-idle flame-local-corpus_x
f local-all-corpus_obs-w8   "corpus_obs: all obs, local disk, 8 workers. $B" --no-idle flame-local-corpus_obs
f local-all-cell_type-w8    "cell_type: get_anndata of one cell type, local disk, 8 workers. $B" --no-idle flame-local-cell_type
f floci-4GB-corpus_x-w8     "corpus_x: all X of the 4GB set, floci S3 on localhost, 8 workers. $B" --no-idle flame-floci-corpus_x
f local-all-corpus_x-w8     "Zoom: the zarr_io event-loop thread in corpus_x" "--no-idle --focus ^zarr_io$" zoom-local-corpus_x-zarr_io
f local-all-corpus_x-w8-gil "Zoom: who holds the GIL in corpus_x" "" zoom-local-corpus_x-gil
f local-all-corpus_obs-w8   "Zoom: the zarr_io event-loop thread in corpus_obs" "--no-idle --focus ^zarr_io$" zoom-local-corpus_obs-zarr_io
f local-all-cell_type-w8    "Zoom: the zarr_io event-loop thread in cell_type" "--no-idle --focus ^zarr_io$" zoom-local-cell_type-zarr_io
ls -1 "$P"/*.svg
