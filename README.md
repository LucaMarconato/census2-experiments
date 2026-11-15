# census2_experiments

A design spike built around [cellxgene-census2-prototype](https://github.com/chanzuckerberg/cellxgene-census2-prototype) (`e54290c`; spike branch `spike/obs-duckdb` @ `8a174de`).
Not intended for production: it explores how Census 2 (one Zarr store per dataset, Parquet catalog) performs against local disk and a local S3 emulator, with more stores, under added latency, and against a parent Zarr store, Icechunk, Iceberg and DuckDB, to guide development ideas.

Claude (Anthropic) was used to run the benchmarks and present the results.

## Overview

![Overview](docs/overview.svg)

103 human datasets of Census 1 LTS `2025-11-08` (147 GiB h5ad, 13.3M cells); manifests from the prototype's `bulk-ingest-nf/manifests/` (`tools/census1-sample.py`).
Of the prototype's Nextflow ingest pipeline only `stage-refdata.py` is used, for the GENCODE gene references the writer needs. `download.py` fetches the h5ads over HTTPS, and `convert.py` calls the same writer (`census2_dataset_writer.create`) locally, with no Nextflow, Docker or AWS.

## Run

Needs [pixi](https://pixi.sh) and Docker (for floci). Every step is a pixi task; `pixi run all` runs the graph (`pixi task list` shows each task).

```bash
git clone --recurse-submodules <this repo>   # prototype and spike, pinned as submodules
pixi run all tiny                            # smoke test: 3 smallest datasets, everything under tiny/
```

The tiny profile runs every task and backend once (shape `open`, 8 workers, 1 repeat): about 2 min, plus about 1 min the first time for the environments, the download (70 MB) and the floci image.

Full data (not yet run with pixi; untested):

```bash
cp config.example.toml config.toml           # where the data (and h5ads) live
pixi run all                                 # download, convert, every benchmark -> results/
pixi run profiles                            # py-spy flamegraphs; asks for sudo
```

Estimated from earlier runs: a few hours to download and convert 147 GiB, then about 1 to 1.5 h of benchmarks.

Terms: a *shape* is a benchmark query, as in the prototype's `bench` tool: `single` (one dataset), `cell_type` (one cell type across all stores), `open` (open every store), `corpus_obs` (all `obs`), `corpus_x` (all X). A *set* is `<backend>-<stores>`: `local-all`, `local-4GB`, `floci-4GB`; 4GB is the stores that fit in 4 GiB of Zarr, used for S3, the parent store and Icechunk.

floci binds to 127.0.0.1 only, with update checks off; `pixi run floci-stop` stops it.

## License

Provided as is, without warranty of any kind. BSD-3-Clause, see [LICENSE](LICENSE).
