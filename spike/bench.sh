#!/bin/sh
# The spikes' head-to-head on local disk: store path vs Iceberg table vs DuckDB over the fragments.
# Needs spike/fragments.py first. Local files only: DuckDB installs no extension for them.
set -e
cd "$(dirname "$0")/.."
T=$PWD/ext/spike-obs/census2-sdk/tools
PY=$PWD/spike/.venv/bin/python
N=$(ls data/zarr/*.obs.parquet | wc -l | tr -d ' ')
C=$PWD/results/spike/catalogs
mkdir -p $C results/spike/tables
[ -f $C/catalog-$N.parquet ] || $PY $T/build_catalog.py $PWD/data/zarr/ $C/catalog-$N.parquet
[ -d results/spike/tables/obs-$N ] || $PY $T/build_obs_table.py $C/catalog-$N.parquet $PWD/results/spike/tables/obs-$N --verify-digest
QUERIES=single,cell_type,query:compound,query:fp_none,query:fp_some,query:tissue_general,query:numeric,query:membership
QUERIES=$QUERIES,corpus_obs,count_donor:cell_type,count_donor:all,count:wmg:tissue_general_ontology_term_id+cell_type_ontology_term_id
cd $T && $PY -m bench.matrix --catalogs $C --sizes $N --shapes $QUERIES --vias stores,table,sql \
  --obs-table "$OLDPWD/results/spike/tables/obs-{size}" --workers ${WORKERS:-1,8,32} --repeats ${REPEATS:-3} \
  --cell-type neutrophil --queries results/obs_duckdb/queries.json --where laptop-ext \
  --out $OLDPWD/results/spike/bench-$N.jsonl
