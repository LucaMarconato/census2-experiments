#!/bin/sh
# py-spy profiles at 8 workers: collapsed stacks (raw, for flame.py) and speedscope json,
# per store set and shape. Needs sudo on macOS:  sudo ./profile.sh   (default: local-all floci-4g)
# Runs from the prototype's tools dir: the repo's own bench.py would shadow its bench package.
set -e
cd "$(dirname "$0")"
R=$PWD
TOOLS=$R/ext/cellxgene-census2-prototype/census2-sdk/tools
mkdir -p results/profiles
rec() {  # rec <env file or -> <out> <py-spy args...> -- <bench.run args...>
  envf=$1 out=$2; shift 2
  (cd "$TOOLS" && { [ "$envf" = - ] || . "$envf"; } && \
    PYTHONPATH=$TOOLS "$R/.venv/bin/py-spy" record --threads --rate 200 -o "$out" "$@")
}
for set in ${@:-local-all floci-4g}; do
  envf=-
  case $set in floci*) envf=$R/floci/env.sh ;; emu*) envf=$R/emulator/env.sh ;; esac
  cat=$(ls "$R"/results/catalogs/$set/catalog-[0-9]*.parquet)
  for shape in corpus_obs cell_type corpus_x; do
    run="-- $R/.venv/bin/python -m bench.run $cat --shape $shape --workers 8"
    rec $envf "$R/results/profiles/$set-$shape-w8.txt" --idle -f raw $run
    rec $envf "$R/results/profiles/$set-$shape-w8.speedscope.json" --idle -f speedscope $run
  done
  # where the GIL is held, for the X read
  rec $envf "$R/results/profiles/$set-corpus_x-w8-gil.txt" --gil -f raw \
    -- $R/.venv/bin/python -m bench.run $cat --shape corpus_x --workers 8
done
chown -R "${SUDO_USER:-$USER}" results/profiles
