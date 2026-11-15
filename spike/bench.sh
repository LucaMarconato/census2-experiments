#!/bin/sh
# The spike's head-to-head on local disk over all stores: store path vs Iceberg table vs DuckDB over the
# obs fragments (spike/fragments.py first). Local files only: DuckDB installs no extension for them.
# 8 workers. Writes <results>/spike/bench.jsonl anew. Runs in the spike env. SHAPES, REPEATS (3) override.
set -e
cd "$(dirname "$0")/.."
eval "$(python config.py)"
T=$PWD/ext/spike-obs/census2-sdk/tools
S=$RESULTS/spike
rm -rf "$S/catalogs" "$S/table" "$S/bench.jsonl"
mkdir -p "$S/catalogs"
N=$(ls -d "$DATA"/zarr/*.zarr | wc -l | tr -d ' ')
python $T/build_catalog.py "$(cd "$DATA/zarr" && pwd -P)/" "$S/catalogs/catalog-$N.parquet"
python $T/build_obs_table.py "$S/catalogs/catalog-$N.parquet" "$S/table" --verify-digest
Q=single,cell_type,query:compound,query:fp_none,query:fp_some,query:tissue_general,query:numeric,query:membership
Q=$Q,corpus_obs,count_donor:cell_type,count_donor:all,count:wmg:tissue_general_ontology_term_id+cell_type_ontology_term_id
cd $T && python -m bench.matrix --catalogs "$S/catalogs" --sizes $N --shapes ${SHAPES:-$Q} --vias stores,table,sql \
  --obs-table "$S/table" --workers 8 --repeats ${REPEATS:-3} \
  --cell-type neutrophil --queries results/obs_duckdb/queries.json --where "$PROFILE" --out "$S/bench.jsonl"
