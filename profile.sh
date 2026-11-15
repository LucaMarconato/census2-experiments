#!/bin/sh
# py-spy profiles at 8 workers: collapsed stacks (raw, for flame.py) and speedscope json, per store set
# and shape, in <results>/profiles. py-spy needs root on macOS: run via `pixi run profiles` (sudo).
# Runs from the prototype's tools dir: the repo's own bench.py would shadow its bench package.
set -e
cd "$(dirname "$0")"
R=$PWD
PY=${PY:-python}
eval "$($PY config.py)"
TOOLS=$R/ext/cellxgene-census2-prototype/census2-sdk/tools
SPY=$(dirname "$(command -v $PY)")/py-spy
P=$RESULTS/profiles
mkdir -p "$P"
rec() {  # rec <env file or -> <out> <py-spy args...> -- <bench.run args...>
  envf=$1 out=$2; shift 2
  (cd "$TOOLS" && { [ "$envf" = - ] || . "$envf"; } && \
    PYTHONPATH=$TOOLS "$SPY" record --threads --rate 200 -o "$out" "$@")
}
for set in ${@:-local-all floci-4GB}; do
  envf=-
  case $set in floci*) envf=$R/floci/env.sh ;; esac
  cat=$(ls "$RESULTS"/catalogs/$set/catalog-[0-9]*.parquet)
  for shape in corpus_obs cell_type corpus_x; do
    run="-- $PY -m bench.run $cat --shape $shape --workers 8"
    rec $envf "$P/$set-$shape-w8.txt" --idle -f raw $run
    rec $envf "$P/$set-$shape-w8.speedscope.json" --idle -f speedscope $run
  done
  # where the GIL is held, for the X read
  rec $envf "$P/$set-corpus_x-w8-gil.txt" --gil -f raw -- $PY -m bench.run $cat --shape corpus_x --workers 8
done
[ -z "$SUDO_USER" ] || chown -R "$SUDO_USER" "$P"
