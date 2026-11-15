#!/bin/sh
# Link data/ (config.toml), clone the prototype and the spike at pinned commits, make the envs, stage the gene references.
set -e
cd "$(dirname "$0")"
D=$(python3 -c "import tomllib; print(tomllib.load(open('config.toml', 'rb')).get('data', ''))" 2>/dev/null || true)
[ -n "$D" ] && [ ! -e data ] && ln -s "$D" data
clone() { [ -d "$1" ] || git clone -q https://github.com/chanzuckerberg/cellxgene-census2-prototype.git "$1"; git -C "$1" fetch -q origin "$2" 2>/dev/null || true; git -C "$1" checkout -q "$3"; }
clone ext/cellxgene-census2-prototype main e54290c50a4c080ca7e1e4483ac017b192b36024
clone ext/spike-obs spike/obs-duckdb 8a174de
uv sync
uv sync --project spike
uv run python ext/cellxgene-census2-prototype/bulk-ingest-nf/tools/stage-refdata.py data/refdata/
