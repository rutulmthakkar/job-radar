"""
Fetch Android-developer roles from Greenhouse, Lever, and Ashby.

Uses data/discovered_slugs.json (populated by fetchers/discover.py).
Falls back to data/company_slugs.json for hand-curated extras.
Fetches the job description text for each match so the application
prompt can include it without an extra round-trip.
"""
from __future__ import annotations
import json, pathlib, requests, concurrent.futures as cf, re, html

ROOT = pathlib.Path(__file__).parent.parent
DISCOVERED = ROOT / "data" / "discovered_slugs.json"
MANUAL     = ROOT / "data" / "company_slugs.json"

KEYWORDS = re.compile(
    r"\b(android|kotlin|jetpack compose|mobile (engineer|developer|swe))\b", re.I,
)
NEG = re.compile(r"\b(manager|director|designer|recruiter|intern)\b", re.I)

UA = {"User-Agent": "job-radar/1.0 (+github actions)"}

_US_STATES = re.compile(
    r"\b(CA|NY|WA|TX|MA|IL|CO|GA|FL|OR|VA|NC|NJ|PA|OH|MI|AZ|MN|WI|MO|IN|TN|MD|"
    r"CT|NV|UT|KS|AR|MS|NM|NE|ID|HI|ME|MT|RI|DE|SD|ND|AK|VT|WY|WV|DC)\b"
)
_CA_PROVINCES = re.compile(r"\b(ON|BC|QC|AB|MB|SK|NS|NB|NL|PE)\b")
_US_CITIES = re.compile(
    r"\b(San Francisco|New York|Seattle|Austin|Boston|Chicago|Denver|Atlanta|"
    r"Los Angeles|Portland|San Jose|San Diego|Dallas|Houston|Phoenix|"
    r"Minneapolis|Detroit|Pittsburgh|Philadelphia|Miami|Nashville|Raleigh|"
    r"Washington|Remote)\b",
    re.I,
)
_US_COUNTRY = re.compile(r"\b(United States|USA|U\.S\.A|U\.S\.|US)\b", re.I)
_CANADA = re.compile(r"\bCanada\b", re.I)
_EXCLUDE = re.compile(
    r"\b(India|UK|Britain|Germany|France|Spain|Brazil|Mexico|Japan|China|"
    r"Singapore|Australia|Israel|Ireland|Netherlands|Poland|Argentina|Colombia|"
    r"EMEA|APAC|Europe|Asia|Africa|Latin America|South America)\b",
    re.I,
)


def _is_us_or_canada(location: str) -> bool:
    if not location or not location.strip():
        return True
    if _EXCLUDE.search(location):
        return False
    if _US_COUNTRY.search(location) or _US_STATES.search(location) or _US_CITIES.search(location):
        return True
    if _CANADA.search(location) or _CA_PROVINCES.search(location):
        return True
    loc = location.strip().lower()
    if loc == "remote":
        return True
    return True  # permissive for ambiguous


def _strip_html(s: str) -> str:
    s = html.unescape(s or "")
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:2500]


def _to_iso(ms_epoch) -> str:
    """Convert milliseconds-since-epoch int to ISO-8601 UTC string."""
    try:
        import datetime
        return datetime.datetime.utcfromtimestamp(int(ms_epoch) / 1000).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return ""


def _greenhouse(slug, display):
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
    try:
        r = requests.get(url, headers=UA, timeout=15)
        if r.status_code != 200: return []
        out = []
        for j in r.json().get("jobs", []):
            t = j["title"]
            if not KEYWORDS.search(t) or NEG.search(t): continue
            out.append({
                "company": display, "company_slug": slug, "ats": "greenhouse",
                "title": t,
                "location": (j.get("location") or {}).get("name", ""),
                "url": j["absolute_url"],
                "jd": _strip_html(j.get("content", "")),
                "posted_at": j.get("updated_at", ""),
            })
        return out
    except Exception:
        return []


def _lever(slug, display):
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    try:
        r = requests.get(url, headers=UA, timeout=15)
        if r.status_code != 200: return []
        out = []
        for j in r.json():
            t = j["text"]
            if not KEYWORDS.search(t) or NEG.search(t): continue
            jd = j.get("descriptionPlain") or _strip_html(j.get("description", ""))
            created = _to_iso(j["createdAt"]) if j.get("createdAt") else ""
            updated = _to_iso(j["updatedAt"]) if j.get("updatedAt") else ""
            posted_at = max(created, updated) if created and updated else (updated or created)
            out.append({
                "company": display, "company_slug": slug, "ats": "lever",
                "title": t,
                "location": (j.get("categories") or {}).get("location", ""),
                "url": j["hostedUrl"],
                "jd": jd[:2500],
                "posted_at": posted_at,
            })
        return out
    except Exception:
        return []


def _ashby(slug, display):
    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
    try:
        r = requests.get(url, headers=UA, timeout=15)
        if r.status_code != 200: return []
        out = []
        for j in r.json().get("jobs", []):
            t = j.get("title", "")
            if not KEYWORDS.search(t) or NEG.search(t): continue
            out.append({
                "company": display, "company_slug": slug, "ats": "ashby",
                "title": t,
                "location": j.get("location", ""),
                "url": j.get("jobUrl", ""),
                "jd": _strip_html(j.get("descriptionHtml", "")),
                "posted_at": j.get("publishedAt", ""),
            })
        return out
    except Exception:
        return []


def _load_targets():
    targets = []
    if DISCOVERED.exists():
        for h in json.loads(DISCOVERED.read_text()).get("discovered", []):
            targets.append((h["ats"], h["slug"], h["company"]))
    if MANUAL.exists():
        m = json.loads(MANUAL.read_text())
        for s in m.get("greenhouse", []):
            targets.append(("greenhouse", s, s.replace("-", " ").title()))
        for s in m.get("lever", []):
            targets.append(("lever", s, s.replace("-", " ").title()))
        for s in m.get("ashby", []):
            targets.append(("ashby", s, s.replace("-", " ").title()))
    seen = set(); uniq = []
    for t in targets:
        k = (t[0], t[1])
        if k in seen: continue
        seen.add(k); uniq.append(t)
    return uniq


FETCHERS = {"greenhouse": _greenhouse, "lever": _lever, "ashby": _ashby}


def fetch():
    targets = _load_targets()
    print(f"  Querying {len(targets)} ATS boards…")
    jobs = []
    with cf.ThreadPoolExecutor(max_workers=25) as pool:
        futs = [pool.submit(FETCHERS[ats], slug, name) for ats, slug, name in targets]
        for fut in cf.as_completed(futs):
            jobs.extend(fut.result())
    jobs = [j for j in jobs if _is_us_or_canada(j.get("location", ""))]
    return jobs


if __name__ == "__main__":
    j = fetch()
    print(f"Total: {len(j)} Android roles")
