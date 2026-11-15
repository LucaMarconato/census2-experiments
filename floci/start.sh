#!/bin/sh
# Start floci (pinned image) on 127.0.0.1:4566, S3 state in data/floci; upload each store to s3://s-<id>/<id>.zarr.
# Same as `floci start`, but with a pinned digest, a localhost-only port and persistent storage.
set -e
cd "$(dirname "$0")/.."
IMAGE=floci/floci@sha256:5ee85db604c4aa74ac76e07ea5cc83086f37bb472bf3dbb97e34019e48efae9c  # 2.4.0, linux/arm64
. floci/env.sh
if ! docker ps -q -f name=census2-floci | grep -q .; then
  mkdir -p data/floci
  docker rm -f census2-floci 2>/dev/null || true
  docker run -d --platform linux/arm64 --name census2-floci -p 127.0.0.1:4566:4566 \
    -e FLOCI_STORAGE_MODE=persistent -v "$(cd data/floci && pwd -P):/app/data" $IMAGE
fi
until curl -sf http://127.0.0.1:4566/_floci/health >/dev/null; do sleep 1; done
for id in $(python3 -c "import json,sys; [print(json.loads(l)['dataset_version_id']) for m in sys.argv[1:] for l in open(m)]" ${@:-subsets/emu-small.jsonl subsets/4GB.jsonl} | sort -u); do
  aws s3 mb s3://s-$id >/dev/null 2>&1 || true
  aws s3 sync --only-show-errors data/zarr/$id.zarr s3://s-$id/$id.zarr
done
