"""Fetch recent layoffs from layoffs.fyi public Google Sheet."""
from __future__ import annotations
import csv, io, datetime as dt, requests

# layoffs.fyi publishes a public Google Sheet. The CSV export URL is stable.
# If it breaks, replace with the current sheet ID from layoffs.fyi.
SHEET_CSV = (
    "https://docs.google.com/spreadsheets/d/"
    "1Bnu1ndKMU0FX-tlKKLztpYffuwApiOLKQt48BalkkVo/export?format=csv&gid=137811653"
)

CUTOFF_DAYS = 90  # avoid-list window


def fetch() -> list[dict]:
    r = requests.get(SHEET_CSV, timeout=30)
    r.raise_for_status()
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


if __name__ == "__main__":
    import json
    print(json.dumps(fetch()[:5], indent=2))
