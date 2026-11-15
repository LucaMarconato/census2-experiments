#!/bin/sh
# Separate vs parent vs Icechunk on floci with an added delay per S3 request.
# Needs floci on :4566 with the 4GB stores, the parent store and the Icechunk repo.
# Per delay (ms, default 10 50): latency_proxy.py on :4567 holds each new HTTP request
# that long before forwarding to floci (responses pass undelayed), icechunk_bench.py runs
# through it (open, count_cell_type, corpus_obs; 8 workers; 3 timed repeats
# plus one counted run, each a new process), then the proxy stops.
# Writes <results>/icechunk/bench-latency.jsonl anew, label +<ms>ms. SHAPES, REPEATS (3) and WORKERS (8) override.
set -e
cd "$(dirname "$0")/.."
eval "$(python config.py)"
OUT=$RESULTS/icechunk/bench-latency.jsonl
rm -f "$OUT"
for ms in ${@:-10 50}; do
  python benchmarks/latency_proxy.py --listen 4567 --target 4566 --delay-ms $ms & P=$!
  sleep 1  # the proxy starts in the background: give it time to listen before the bench connects
  python -W ignore benchmarks/icechunk_bench.py bench --where floci --endpoint http://127.0.0.1:4567 --label "+${ms}ms" \
    --shapes ${SHAPES:-open,count_cell_type,corpus_obs} --workers ${WORKERS:-8} --repeats ${REPEATS:-3} --out "$OUT" --append
  kill $P
done
