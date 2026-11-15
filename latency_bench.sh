#!/bin/sh
# Separate vs parent vs Icechunk on floci with an added delay per S3 request.
# Needs floci on :4566 with the 4g stores, the parent store and the Icechunk repo.
# Per delay (ms, default 10 50): latency_proxy.py on :4567 holds each new HTTP request
# that long before forwarding to floci (responses pass undelayed), icechunk_bench.py runs
# through it (open, count_cell_type, corpus_obs, single; 1 and 8 workers; 3 timed repeats
# plus one counted run, each a new process), then the proxy stops.
# Appends to $OUT (default results/icechunk/bench-latency.jsonl), label +<ms>ms$LABEL_SUFFIX.
cd "$(dirname "$0")"
for ms in ${@:-10 50}; do
  python3 latency_proxy.py --listen 4567 --target 4566 --delay-ms $ms & P=$!
  sleep 1  # the proxy starts in the background: give it time to listen before the bench connects
  .venv/bin/python -W ignore icechunk_bench.py bench --where floci --endpoint http://127.0.0.1:4567 --label "+${ms}ms${LABEL_SUFFIX}" \
    --shapes open,count_cell_type,corpus_obs,single --workers 1,8 --repeats 3 --out ${OUT:-results/icechunk/bench-latency.jsonl}
  kill $P
done
