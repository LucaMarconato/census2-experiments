#!/bin/sh
# The parent Zarr store (parent_zarr.py) on floci: s3://parent/<id>/... plus the consolidated root zarr.json.
set -e
cd "$(dirname "$0")/.."
eval "$(python config.py)"
. floci/env.sh
aws s3 mb s3://parent >/dev/null 2>&1 || true
aws s3 rm --quiet --recursive s3://parent
aws s3 cp --only-show-errors "$DATA/parent.zarr/zarr.json" s3://parent/zarr.json
for id in $(python -c "import json,sys; [print(json.loads(l)['dataset_version_id']) for l in open(sys.argv[1])]" "$SUBSETS/4GB.jsonl"); do
  aws s3 sync --only-show-errors "$DATA/zarr/$id.zarr" s3://parent/$id
done
