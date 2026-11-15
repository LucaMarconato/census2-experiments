# census2_experiments

A design spike built around [cellxgene-census2-prototype](https://github.com/chanzuckerberg/cellxgene-census2-prototype) (`e54290c`; spike branch `spike/obs-duckdb` @ `8a174de`).
Not intended for production: it explores how Census 2 (one Zarr store per dataset, Parquet catalog) performs against local disk and local S3 emulators, with more stores, under added latency, and against a parent Zarr store, Icechunk, Iceberg and DuckDB, to guide development ideas.

Claude (Anthropic) was used to run the benchmarks and present the results.

## Data

103 human datasets of Census 1 LTS `2025-11-08` (147 GiB h5ad, 13.3M cells); manifests from the prototype's `bulk-ingest-nf/manifests/`.

```bash
git clone --recurse-submodules <this repo>   # prototype and spike, pinned as submodules
cp config.example.toml config.toml           # set local paths
uv run python download.py                    # to h5ad; --max-gib 50 for a subset. Resumable
uv run python ext/cellxgene-census2-prototype/bulk-ingest-nf/tools/stage-refdata.py data/refdata/
```

## Benchmarks

```bash
uv run python subset.py <h5ad dir>                  # subsets/50g.jsonl
uv run python convert.py subsets/50g.jsonl          # data/zarr/
uv run python subset.py data/zarr --max-gib 0.117 --fill --max-store-mib 60 --from subsets/50g.jsonl --out subsets/emu-small.jsonl
emulator/start.sh                                   # AWS Emulator (Docker), uploads emu-small
floci/start.sh                                      # floci (Docker), uploads emu-small + 4g
uv run python bench.py && uv run python table.py    # results/bench.md
uv run python consistency.py local-small emu-small floci-small
uv run python scaling.py && uv run python scaling_plot.py   # time vs number of stores
sudo ./profile.sh && ./render_profiles.sh           # py-spy flamegraphs
uv run python parent_zarr.py && floci/upload-parent.sh
uv run python icechunk_bench.py build && uv run python icechunk_bench.py bench
./latency_bench.sh 10 50                            # floci behind latency_proxy.py
uv run --project spike python spike/fragments.py data/zarr && spike/bench.sh   # Iceberg, DuckDB
```

Emulators bind to 127.0.0.1 only, telemetry and update checks off. AWS Emulator caps a bucket at 64 MiB, so each store has its own bucket.

## License

Provided as is, without warranty of any kind. BSD-3-Clause, see [LICENSE](LICENSE).
