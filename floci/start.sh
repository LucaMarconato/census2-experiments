#!/bin/sh
# Start floci (pinned image) on 127.0.0.1:4566 as census2-floci-<profile> (other profiles' stopped), S3 state
# in <data>/floci; upload each store of <subsets>/4GB.jsonl to one bucket, s3://stores/<id>.zarr.
# Same as `floci start`, but with a pinned digest, a localhost-only port and persistent storage.
set -e
cd "$(dirname "$0")/.."
eval "$(python config.py)"
IMAGE=floci/floci@sha256:5ee85db604c4aa74ac76e07ea5cc83086f37bb472bf3dbb97e34019e48efae9c  # 2.4.0, linux/arm64
NAME=census2-floci-$PROFILE
for c in $(docker ps --format '{{.Names}}' | grep '^census2-floci' | grep -vx "$NAME"); do docker stop "$c" >/dev/null; done
if ! docker ps --format '{{.Names}}' | grep -qx "$NAME"; then
  mkdir -p "$DATA/floci"
  docker rm -f "$NAME" >/dev/null 2>&1 || true
  docker run -d --name "$NAME" -p 127.0.0.1:4566:4566 \
    -e FLOCI_STORAGE_MODE=persistent -v "$(cd "$DATA/floci" && pwd -P):/app/data" $IMAGE >/dev/null
fi
until curl -sf http://127.0.0.1:4566/_floci/health >/dev/null; do sleep 1; done
. floci/env.sh
aws s3 mb s3://stores >/dev/null 2>&1 || true
for id in $(python -c "import json,sys; [print(json.loads(l)['dataset_version_id']) for l in open(sys.argv[1])]" "$SUBSETS/4GB.jsonl"); do
  aws s3 sync --only-show-errors "$DATA/zarr/$id.zarr" s3://stores/$id.zarr
done
