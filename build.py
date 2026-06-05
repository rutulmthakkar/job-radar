"""Merge layoffs + sponsors + day-one + jobs into site/companies.json."""
from __future__ import annotations
import json, pathlib, datetime as dt
from fetchers import layoffs, perm_sponsors, jobs, day_one_perm
from fetchers.perm_sponsors import normalize
from fetchers.scorer import score_jobs

ROOT = pathlib.Path(__file__).parent
OUT  = ROOT / "site" / "companies.json"
RESUME = ROOT / "resume.md"

# Companies that use proprietary career portals (not Greenhouse/Lever/Ashby).
# These always appear in the dashboard with a direct job-search link.
# Attempted Google Careers API (careers.google.com → /about/careers/applications/jobs/results/)
# but the site is fully JS-rendered with no accessible XHR endpoint from server-side.
CAREERS_LINKS = {
    "google": {
        "company": "Google",
        "careers_url": "https://www.google.com/about/careers/applications/jobs/results/?q=android&location=United+States",
        "note": "Search Google Careers (Android · US)",
    },
}


def main():
    print("Fetching layoffs…")
    lo = layoffs.fetch();          print(f"  {len(lo)} recent events")
    print("Loading PERM sponsors…")
    sp = perm_sponsors.fetch();    print(f"  {len(sp)} sponsors")
    print("Loading day-one PERM list…")
    d1 = day_one_perm.fetch();     print(f"  {len(d1)} day-one filers")
    print("Fetching jobs…")
    jb = jobs.fetch();             print(f"  {len(jb)} Android roles")

    by_co = {}

    # Seed with every PERM sponsor and every day-one filer so they always appear
    for key, info in sp.items():
        by_co[key] = {
            "company": info["company"], "jobs": [],
            "perm_count": info["perm_count"], "fy": info["fy"],
            "day_one": key in d1,
            "day_one_notes": d1.get(key, {}).get("notes", ""),
            "layoffs": [], "avoid": False,
        }
    for key, info in d1.items():
        if key not in by_co:
            by_co[key] = {
                "company": info.get("notes", "").split(";")[0] or key.title(),
                "jobs": [], "perm_count": 0, "fy": "",
                "day_one": True, "day_one_notes": info["notes"],
                "layoffs": [], "avoid": False,
            }

    # Attach scraped Android jobs
    for j in jb:
        key = normalize(j["company"])
        rec = by_co.setdefault(key, {
            "company": j["company"], "jobs": [],
            "perm_count": 0, "fy": "",
            "day_one": False, "day_one_notes": "",
            "layoffs": [], "avoid": False,
        })
        rec["jobs"].append({
            "title": j["title"], "location": j["location"],
            "url": j["url"], "jd": j.get("jd", ""), "ats": j.get("ats",""),
        })

    # Apply layoffs
    for ev in lo:
        key = normalize(ev["company"])
        rec = by_co.setdefault(key, {
            "company": ev["company"], "jobs": [],
            "perm_count": 0, "fy": "",
            "day_one": key in d1,
            "day_one_notes": d1.get(key, {}).get("notes", ""),
            "layoffs": [], "avoid": False,
        })
        rec["layoffs"].append(ev)
        rec["avoid"] = True

    # Inject manual-portal companies (e.g. Google)
    for key, info in CAREERS_LINKS.items():
        rec = by_co.setdefault(key, {
            "company": info["company"], "jobs": [],
            "perm_count": 0, "fy": "",
            "day_one": key in d1, "day_one_notes": d1.get(key, {}).get("notes", ""),
            "layoffs": [], "avoid": False,
        })
        rec["careers_link"] = info["careers_url"]
        rec["careers_note"] = info["note"]

    score_jobs(list(by_co.values()))

    companies = sorted(
        by_co.values(),
        key=lambda r: (not r["day_one"], -len(r["jobs"]), -r["perm_count"]),
    )

    payload = {
        "generated_at": dt.datetime.utcnow().isoformat() + "Z",
        "has_resume": RESUME.exists() and len(RESUME.read_text().strip()) > 50,
        "stats": {
            "companies":  len(companies),
            "hiring":     sum(1 for c in companies if c["jobs"] and not c["avoid"]),
            "sponsors":   sum(1 for c in companies if c["perm_count"] > 0),
            "day_one":    sum(1 for c in companies if c["day_one"]),
            "avoid":      sum(1 for c in companies if c["avoid"]),
            "open_roles": sum(len(c["jobs"]) for c in companies),
        },
        "companies": companies,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {OUT}\n  {payload['stats']}")


if __name__ == "__main__":
    main()
