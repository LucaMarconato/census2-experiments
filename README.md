# census2_experiments

A design spike built around [cellxgene-census2-prototype](https://github.com/chanzuckerberg/cellxgene-census2-prototype) (`e54290c`; spike branch `spike/obs-duckdb` @ `8a174de`).
Not intended for production: it explores how Census 2 (one Zarr store per dataset, Parquet catalog) performs against local disk and local S3 emulators, with more stores, under added latency, and against a parent Zarr store, Icechunk, Iceberg and DuckDB, to guide development ideas.

Claude (Anthropic) was used to run the benchmarks and present the results.

## Overview

![Overview](docs/overview.svg)

## Data

103 human datasets of Census 1 LTS `2025-11-08` (147 GiB h5ad, 13.3M cells); manifests from the prototype's `bulk-ingest-nf/manifests/` (`tools/census1-sample.py`).
Of the prototype's Nextflow ingest pipeline only `stage-refdata.py` is used: it fetches the GENCODE gene references that the writer needs. `download.py` fetches the h5ads over HTTPS, and `convert.py` calls the same writer (`census2_dataset_writer.create`) locally, with no Nextflow, Docker or AWS.

```bash
git clone --recurse-submodules <this repo>   # prototype and spike, pinned as submodules
cp config.example.toml config.toml           # set local paths
uv run python download.py                    # to h5ad; --max-gib 50 for a subset. Resumable
uv run python ext/cellxgene-census2-prototype/bulk-ingest-nf/tools/stage-refdata.py data/refdata/   # gene references (GENCODE), needs aria2c
uv run python subset.py <h5ad dir> --max-gib 1000 --out subsets/all.jsonl   # finished h5ads
uv run python convert.py subsets/all.jsonl   # h5ad -> Census 2 Zarr in data/zarr/. Resumable
```

## Benchmarks

```bash
uv run python subset.py data/zarr --max-gib 0.117 --fill --max-store-mib 60 --from subsets/50g.jsonl --out subsets/emu-small.jsonl
emulator/start.sh                                   # AWS Emulator (Docker), uploads emu-small
floci/start.sh                                      # floci (Docker), uploads emu-small + 4g
uv run python bench.py && uv run python table.py    # results/bench.md
uv run python consistency.py local-small emu-small floci-small
uv run python scaling.py && uv run python scaling_plot.py   # time vs number of stores
sudo ./profile.sh && ./render_profiles.sh           # py-spy flamegraphs (SVG)
uv run python parent_zarr.py && floci/upload-parent.sh
uv run python icechunk_bench.py build && uv run python icechunk_bench.py bench
./latency_bench.sh 10 50                            # floci behind latency_proxy.py
uv run --project spike python spike/fragments.py data/zarr && spike/bench.sh   # Iceberg, DuckDB
spike/bench-4g.sh                                   # spike paths on the 4g set, vs Icechunk
```

Results in `results/` ran on an external USB SSD with all 103 stores. Emulators bind to 127.0.0.1 only, telemetry and update checks off. AWS Emulator caps a bucket at 64 MiB, so each store has its own bucket.

## Takeaways

External USB SSD, 103 stores (13.3M cells, 56 GB X); 21 stores on floci; medians at 8 workers.
- Cost grows linearly with the number of stores: opening takes 4 requests and about 9 ms per store (17 s at 2,000), an `obs` scan about 80 ms per store (166 s at 2,000). A one-dataset query stays at 0.3 s.
- Whole corpus: all `obs` in 8 s, all X in 148 s (about 380 MB/s). 32 workers add nothing over 8.
- Iceberg or DuckDB over `obs` fragments: counts 40 to 180x faster than reading each store, the `obs` scan 4x, filtered queries 1.1 to 3.5x.
- Parent Zarr with consolidated metadata: open needs 4 requests instead of 84 and a cell-type count 46 instead of 126. Icechunk opens fast (0.02 s vs 0.2 s on floci) but makes as many store reads as separate stores.
- Latency dominates on S3: at +50 ms per request the `obs` scan of 21 stores takes 10 s at 8 workers and 67 s at 1 (1.2 s with none). Fewer requests (parent) and concurrency matter more than the format.

## Earlier takeaways

From an earlier version of the code, on a smaller subset (5, 21 and 44 stores, internal SSD); results not kept:
- Local disk, AWS Emulator and floci return identical results (requests, bytes, `get_anndata` hashes).
- 8 workers speed up the `obs` scan about 1.3x; 32 add nothing.
- floci on localhost: reading all X of 21 stores (4 GB) took 21 s vs 7 s on local disk; other shapes 1.1 to 1.5x slower.
- Profiles of the full X read: one `zarr_io` event-loop thread is busy 80% of wall time and holds most of the GIL. `obs` scans spend their time in string decoding, cell-type queries in coordinate indexing.
- Spike, 21 stores: an Iceberg table or DuckDB over `obs` fragments answers `obs` scans 3 to 9x and counts 7 to 55x faster than reading each store.

## License

Provided as is, without warranty of any kind. BSD-3-Clause, see [LICENSE](LICENSE).
