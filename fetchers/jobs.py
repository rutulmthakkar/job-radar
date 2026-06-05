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


def _strip_html(s: str) -> str:
    s = html.unescape(s or "")
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:2500]


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
                "updated": j.get("updated_at", ""),
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
            out.append({
                "company": display, "company_slug": slug, "ats": "lever",
                "title": t,
                "location": (j.get("categories") or {}).get("location", ""),
                "url": j["hostedUrl"],
                "jd": jd[:2500],
                "updated": "",
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
                "updated": j.get("publishedAt", ""),
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
    return jobs


if __name__ == "__main__":
    j = fetch()
    print(f"Total: {len(j)} Android roles")
