"""Local paths from config.toml (see config.example.toml)."""

import tomllib
from pathlib import Path

HERE = Path(__file__).parent.resolve()
_f = HERE / "config.toml"
_c = tomllib.loads(_f.read_text()) if _f.exists() else {}
DATA = HERE / "data"  # a symlink to _c["data"], made by setup.sh
H5AD = Path(_c.get("h5ad", DATA / "h5ad"))
