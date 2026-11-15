#!/bin/sh
# Start AWS Emulator in Docker; upload each store of a manifest to its own bucket, s3://s-<id>/<id>.zarr.
# One bucket per store: the emulator caps a bucket at 64 MiB.
set -e
cd "$(dirname "$0")/.."
MANIFEST=${1:-subsets/emu-small.jsonl}
if ! docker ps -q -f name=census2-emu | grep -q .; then
  docker build -q --platform linux/arm64 -t aws-emulator emulator/
  mkdir -p ~/.aws/emulator
  docker rm -f census2-emu 2>/dev/null || true
  docker run -d --platform linux/arm64 --name census2-emu --memory=7g --memory-swap=7g -p 127.0.0.1:9297:9297 \
    -e HOME="$HOME" -v "$HOME/.aws/emulator:$HOME/.aws/emulator" aws-emulator -p 9297 --telemetry off
fi
until curl -sf --cacert ~/.aws/emulator/9297/ca.pem https://127.0.0.1:9297/__admin/health; do sleep 1; done
. emulator/env.sh
for id in $(python3 -c "import json,sys; [print(json.loads(l)['dataset_version_id']) for l in open(sys.argv[1])]" "$MANIFEST"); do
  aws s3 mb s3://s-$id >/dev/null 2>&1 || true
  aws s3 sync --only-show-errors data/zarr/$id.zarr s3://s-$id/$id.zarr
done
docker stats --no-stream census2-emu
