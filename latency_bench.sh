#!/bin/sh
# Separate vs parent vs Icechunk on floci behind latency_proxy.py, at each added delay (ms).
cd "$(dirname "$0")"
for ms in ${@:-10 50}; do
  python3 latency_proxy.py --listen 4567 --target 4566 --delay-ms $ms & P=$!
  sleep 1
  .venv/bin/python -W ignore icechunk_bench.py bench --where floci --endpoint http://127.0.0.1:4567 --label "+${ms}ms${LABEL_SUFFIX}" \
    --shapes open,count_cell_type,corpus_obs,single --workers 1,8 --repeats 3 --out ${OUT:-results/icechunk/bench-latency.jsonl}
  kill $P
done
