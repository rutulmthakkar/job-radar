"""
Fetch top PERM sponsors. The DOL publishes quarterly disclosure files at:
  https://www.dol.gov/agencies/eta/foreign-labor/performance

Those files are large Excel workbooks (~hundreds of MB/year combined) and
the URL pattern changes each quarter. Rather than re-download every day,
we maintain a curated snapshot in data/perm_sponsors.csv that we refresh
quarterly. This fetcher just loads it and exposes the sponsor map.

To refresh: download the latest PERM_Disclosure_Data_FY*.xlsx from DOL,
group by EMPLOYER_NAME where CASE_STATUS == 'Certified', count rows,
and write data/perm_sponsors.csv with columns: company,perm_count,fy.
"""
from __future__ import annotations
import csv, pathlib

DATA = pathlib.Path(__file__).parent.parent / "data" / "perm_sponsors.csv"


def fetch() -> dict[str, dict]:
    """Return {normalized_company_name: {perm_count, fy}}."""
    if not DATA.exists():
        return {}
    out = {}
    with DATA.open() as f:
        for row in csv.DictReader(f):
            key = normalize(row["company"])
            out[key] = {
                "company": row["company"],
                "perm_count": int(row["perm_count"]),
                "fy": row.get("fy", ""),
            }
    return out


def normalize(name: str) -> str:
    n = name.lower().strip()
    for suffix in [" inc.", " inc", " llc", " corp.", " corp", " ltd.",
                   " ltd", " co.", " co", ",", "."]:
        n = n.replace(suffix, "")
    return " ".join(n.split())


if __name__ == "__main__":
    print(f"Loaded {len(fetch())} sponsors")
