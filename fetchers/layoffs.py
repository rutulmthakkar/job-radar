"""Fetch recent layoffs. Fails soft if source is unreachable.

Source priority:
1. layoffs.fyi Google Sheet (ID rotates occasionally — update SHEET_CSV if 404)
2. California EDD WARN Act XLSX (https://edd.ca.gov — reliable fallback)
"""
from __future__ import annotations
import csv, io, datetime as dt, requests

# layoffs.fyi sheet IDs rotate occasionally. If this 404s, find the current
# ID by viewing source on https://layoffs.fyi and update SHEET_CSV.
SHEET_CSV = (
    "https://docs.google.com/spreadsheets/d/"
    "1Bnu1ndKMU0FX-tlKKLztpYffuwApiOLKQt48BalkkVo/export?format=csv&gid=137811653"
)

# California EDD WARN Act XLSX — rolling current-year report
WARN_XLSX = "https://edd.ca.gov/siteassets/files/jobs_and_training/warn/warn_report1.xlsx"

CUTOFF_DAYS = 90


def _from_layoffs_fyi() -> list[dict] | None:
    """Returns list or None if source is unavailable."""
    try:
        r = requests.get(SHEET_CSV, timeout=30)
        if r.status_code != 200:
            return None
    except Exception:
        return None
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


def _from_ca_warn() -> list[dict] | None:
    """Returns list or None if source is unavailable."""
    try:
        import openpyxl
        r = requests.get(WARN_XLSX, timeout=60)
        if r.status_code != 200:
            return None
        wb = openpyxl.load_workbook(io.BytesIO(r.content), read_only=True, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return None
        headers = [str(h).strip() if h else "" for h in rows[0]]
        cutoff = dt.date.today() - dt.timedelta(days=CUTOFF_DAYS)
        out = []
        for row in rows[1:]:
            data = dict(zip(headers, row))
            # WARN columns: "Notice Date", "Company", "# Affected" (varies by year)
            date_val = data.get("Notice Date") or data.get("Effective Date") or ""
            if isinstance(date_val, dt.datetime):
                d = date_val.date()
            elif isinstance(date_val, dt.date):
                d = date_val
            else:
                try:
                    d = dt.datetime.strptime(str(date_val).strip(), "%m/%d/%Y").date()
                except Exception:
                    continue
            if d < cutoff:
                continue
            company = str(data.get("Company") or data.get("Employer") or "").strip()
            if not company:
                continue
            laid_off = str(data.get("# Affected") or data.get("Employees Affected") or "").strip()
            out.append({
                "company": company,
                "layoff_date": d.isoformat(),
                "laid_off": laid_off,
                "industry": "",
                "hq": "California",
                "source": "CA WARN",
            })
        return out
    except Exception:
        return None


def fetch() -> list[dict]:
    result = _from_layoffs_fyi()
    if result is not None:
        print(f"  layoffs source: layoffs.fyi ({len(result)} rows)")
        return result

    print("  ⚠ layoffs.fyi unavailable, trying CA WARN fallback…")
    result = _from_ca_warn()
    if result is not None:
        print(f"  layoffs source: CA WARN ({len(result)} rows)")
        return result

    print("  ⚠ all layoff sources unavailable; continuing with empty list")
    return []
