"""Local paths from config.toml (see config.example.toml). Links ./data to `data` on first import."""

import tomllib
from pathlib import Path

HERE = Path(__file__).parent.resolve()
_f = HERE / "config.toml"
_c = tomllib.loads(_f.read_text()) if _f.exists() else {}
DATA = HERE / "data"
if "data" in _c and not DATA.exists() and not DATA.is_symlink():
    DATA.symlink_to(_c["data"])
H5AD = Path(_c.get("h5ad", DATA / "h5ad"))
