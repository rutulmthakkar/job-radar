"""
Auto-discover company ATS slugs.

Seed = every company in data/perm_sponsors.csv (DOL-certified sponsors).
For each, generate candidate slugs and probe Greenhouse, Lever, and Ashby
public endpoints. Save the hits to data/discovered_slugs.json.

This is the slow job (~hundreds of HTTP requests). Run weekly, not daily.
Slugs rarely change; new ones appear gradually.
"""
from __future__ import annotations
import json, pathlib, requests, concurrent.futures as cf, re, csv

ROOT = pathlib.Path(__file__).parent.parent
SPONSORS = ROOT / "data" / "perm_sponsors.csv"
MANUAL   = ROOT / "data" / "company_slugs.json"  # extra hand-added seeds
OUT      = ROOT / "data" / "discovered_slugs.json"

SUFFIXES = re.compile(
    r"\b(inc|llc|corp|corporation|company|co|ltd|limited|technologies|"
    r"services|holdings|group|labs|platforms|systems|america)\b\.?", re.I,
)


def candidates(name: str) -> list[str]:
    base = SUFFIXES.sub("", name).lower()
    base = re.sub(r"[^a-z0-9 ]", " ", base)
    parts = base.split()
    if not parts:
        return []
    joined = "".join(parts)
    hyphen = "-".join(parts)
    first  = parts[0]
    return list(dict.fromkeys([joined, hyphen, first]))  # dedup, preserve order


def _try(url: str) -> bool:
    try:
        r = requests.get(url, timeout=7)
        return r.status_code == 200 and len(r.content) > 200
    except Exception:
        return False


def probe(name: str) -> dict | None:
    for slug in candidates(name):
        if _try(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"):
            return {"company": name, "ats": "greenhouse", "slug": slug}
        if _try(f"https://api.lever.co/v0/postings/{slug}?mode=json"):
            return {"company": name, "ats": "lever", "slug": slug}
        if _try(f"https://api.ashbyhq.com/posting-api/job-board/{slug}"):
            return {"company": name, "ats": "ashby", "slug": slug}
    return None


def discover() -> dict:
    names: list[str] = []
    if SPONSORS.exists():
        with SPONSORS.open(encoding="utf-8-sig") as f:
            names += [row["company"] for row in csv.DictReader(f)]
    if MANUAL.exists():
        m = json.loads(MANUAL.read_text())
        names += m.get("extra_names", [])

    print(f"Probing {len(names)} companies across Greenhouse/Lever/Ashby…")
    found = []
    with cf.ThreadPoolExecutor(max_workers=15) as pool:
        for hit in pool.map(probe, names):
            if hit:
                found.append(hit)
                print(f"  ✓ {hit['company']} → {hit['ats']}:{hit['slug']}")

    payload = {"discovered": found}
    OUT.write_text(json.dumps(payload, indent=2))
    print(f"Saved {len(found)} ATS hits to {OUT}")
    return payload


if __name__ == "__main__":
    discover()
