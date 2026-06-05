"""Load curated day-one PERM filer list."""
from __future__ import annotations
import json, pathlib
from fetchers.perm_sponsors import normalize

DATA = pathlib.Path(__file__).parent.parent / "data" / "day_one_perm.json"


def fetch() -> dict[str, dict]:
    if not DATA.exists():
        return {}
    raw = json.loads(DATA.read_text())
    out = {}
    for c in raw.get("companies", []):
        out[normalize(c["company"])] = {
            "verified": c.get("verified", ""),
            "notes": c.get("notes", ""),
        }
    return out


if __name__ == "__main__":
    print(f"Loaded {len(fetch())} day-one PERM filers")
