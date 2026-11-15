#!/bin/sh
# Flamegraph SVGs from the py-spy raw stacks (flame.py -> svg). No GUI app opens.
set -e
cd "$(dirname "$0")/results/profiles"
f() { python3 ../../flame.py "$1.txt" $3 --title "$2" -o "$4.svg"; }
B="share of busy thread samples, idle waits removed"
f local-all-corpus_x-w8   "corpus_x: all X of 44 stores (18 GB), local disk, 8 workers. $B" --no-idle flame-local-corpus_x
f local-all-corpus_obs-w8 "corpus_obs: all obs of 44 stores (3.4M cells), local disk, 8 workers. $B" --no-idle flame-local-corpus_obs
f local-all-cell_type-w8  "cell_type: get_anndata(dendritic cell), 6 of 44 stores, local disk, 8 workers. $B" --no-idle flame-local-cell_type
f floci-4g-corpus_x-w8    "corpus_x: all X of 21 stores (4 GB), floci S3 on localhost, 8 workers. $B" --no-idle flame-floci-corpus_x
f local-all-corpus_x-w8   "Zoom: the one zarr_io event-loop thread in corpus_x (busy 80% of wall time)" "--no-idle --focus ^zarr_io$" zoom-local-corpus_x-zarr_io
f local-all-corpus_x-w8-gil "Zoom: who holds the GIL in corpus_x (GIL held 75% of wall time; 74% of that by zarr_io)" "" zoom-local-corpus_x-gil
f local-all-corpus_obs-w8 "Zoom: zarr_io event-loop thread in corpus_obs: vlen-utf8 string decode and scatter" "--no-idle --focus ^zarr_io$" zoom-local-corpus_obs-zarr_io
f local-all-cell_type-w8  "Zoom: zarr_io event-loop thread in cell_type: coordinate indexing of selected rows" "--no-idle --focus ^zarr_io$" zoom-local-cell_type-zarr_io
ls -1 *.svg
