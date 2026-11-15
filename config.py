"""Paths of the active profile (C2E_PROFILE: real, the default, or tiny).

real: data/ (a link to `data` in config.toml), results/; h5ads at `h5ad` (default data/h5ad).
Store lists (prep/subset.py) go to <data>/subsets: generated, not committed.
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
    RESULTS = HERE / "results"
    H5AD = Path(_c.get("h5ad", DATA / "h5ad"))
elif PROFILE == "tiny":
    DATA, RESULTS = HERE / "tiny/data", HERE / "tiny/results"
    H5AD = DATA / "h5ad"
else:
    raise SystemExit(f"C2E_PROFILE must be real or tiny, not {PROFILE!r}")

SUBSETS = DATA / "subsets"
for _d in (DATA, RESULTS, SUBSETS):
    _d.mkdir(parents=True, exist_ok=True)



def scrub(jsonl: Path) -> None:
    """Make the local paths in a results file relative: <data>/... and repo-relative."""
    text = jsonl.read_text()
    for path, rel in ((DATA.resolve(), "<data>"), (HERE, ".")):
        text = text.replace(f"file://{path}/", f"{rel}/").replace(f"{path}/", f"{rel}/")
    jsonl.write_text(text)


if __name__ == "__main__":
    for k, v in {"PROFILE": PROFILE, "DATA": DATA, "RESULTS": RESULTS, "SUBSETS": SUBSETS, "H5AD": H5AD}.items():
        print(f"{k}='{v}'")
