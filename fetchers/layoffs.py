"""Fetch recent layoffs. Fails soft if source is unreachable."""
from __future__ import annotations
import csv, io, datetime as dt, requests

# layoffs.fyi sheet IDs rotate occasionally. If this 404s, find the current
# ID by viewing source on https://layoffs.fyi and update SHEET_CSV.
SHEET_CSV = (
    "https://docs.google.com/spreadsheets/d/"
    "1Bnu1ndKMU0FX-tlKKLztpYffuwApiOLKQt48BalkkVo/export?format=csv&gid=137811653"
)
CUTOFF_DAYS = 90


def fetch() -> list[dict]:
    try:
        r = requests.get(SHEET_CSV, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"  ⚠ layoffs source unavailable ({e}); continuing with empty list")
        return []
    reader = csv.DictReader(io.StringIO(r.text))
    cutoff = dt.date.today() - dt.timedelta(days=CUTOFF_DAYS)
    out = []
    for row in reader:
        date_str = (row.get("Date") or row.get("Date Added") or "").strip()
        try:
            d = dt.datetime.strptime(date_str, "%m/%d/%Y").date()
        except ValueError:
            continue
        if d < cutoff:
            continue
        company = (row.get("Company") or "").strip()
        if not company:
            continue
        out.append({
            "company": company,
            "layoff_date": d.isoformat(),
            "laid_off": (row.get("# Laid Off") or "").strip(),
            "industry": (row.get("Industry") or "").strip(),
            "hq": (row.get("HQ") or row.get("Location HQ") or "").strip(),
            "source": "layoffs.fyi",
        })
    return out
