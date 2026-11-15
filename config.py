"""Paths of the active profile (C2E_PROFILE: real, the default, or tiny).

real: data/ (a link to `data` in config.toml), results/, subsets/; h5ads at `h5ad` (default data/h5ad).
tiny: everything under tiny/ (gitignored), so a test run never touches the real data or results.
`python config.py` prints them as shell assignments, for the shell scripts.
"""

import os
import tomllib
from pathlib import Path

HERE = Path(__file__).parent.resolve()
PROFILE = os.environ.get("C2E_PROFILE", "real")
_f = HERE / "config.toml"
_c = tomllib.loads(_f.read_text()) if _f.exists() else {}

if PROFILE == "real":
    DATA = HERE / "data"
    if "data" in _c and not DATA.exists() and not DATA.is_symlink():
        DATA.symlink_to(_c["data"])
    RESULTS, SUBSETS = HERE / "results", HERE / "subsets"
    H5AD = Path(_c.get("h5ad", DATA / "h5ad"))
elif PROFILE == "tiny":
    DATA, RESULTS, SUBSETS = HERE / "tiny/data", HERE / "tiny/results", HERE / "tiny/subsets"
    H5AD = DATA / "h5ad"
else:
    raise SystemExit(f"C2E_PROFILE must be real or tiny, not {PROFILE!r}")

for _d in (DATA, RESULTS, SUBSETS):
    _d.mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":
    for k, v in {"PROFILE": PROFILE, "DATA": DATA, "RESULTS": RESULTS, "SUBSETS": SUBSETS, "H5AD": H5AD}.items():
        print(f"{k}='{v}'")
