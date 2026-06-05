"""Merge layoffs + sponsors + day-one + jobs into site/companies.json."""
from __future__ import annotations
import json, pathlib, datetime as dt
from fetchers import layoffs, perm_sponsors, jobs, day_one_perm
from fetchers.perm_sponsors import normalize

ROOT = pathlib.Path(__file__).parent
OUT  = ROOT / "site" / "companies.json"
RESUME = ROOT / "resume.md"


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

    for key, rec in by_co.items():
        if key in sp:
            rec["perm_count"] = sp[key]["perm_count"]
            rec["fy"] = sp[key]["fy"]
        if key in d1:
            rec["day_one"] = True
            rec["day_one_notes"] = d1[key]["notes"]

    for ev in lo:
        key = normalize(ev["company"])
        if key in by_co:
            by_co[key]["layoffs"].append(ev)
            by_co[key]["avoid"] = True
        else:
            by_co[key] = {
                "company": ev["company"], "jobs": [],
                "perm_count": sp.get(key, {}).get("perm_count", 0),
                "fy": sp.get(key, {}).get("fy", ""),
                "day_one": key in d1,
                "day_one_notes": d1.get(key, {}).get("notes", ""),
                "layoffs": [ev], "avoid": True,
            }

    companies = sorted(
        by_co.values(),
        key=lambda r: (not r["day_one"], -len(r["jobs"]), -r["perm_count"]),
    )

    payload = {
        "generated_at": dt.datetime.utcnow().isoformat() + "Z",
        "has_resume": RESUME.exists() and len(RESUME.read_text().strip()) > 50,
        "stats": {
            "companies": len(companies),
            "hiring":    sum(1 for c in companies if c["jobs"] and not c["avoid"]),
            "sponsors":  sum(1 for c in companies if c["perm_count"] > 0),
            "day_one":   sum(1 for c in companies if c["day_one"]),
            "avoid":     sum(1 for c in companies if c["avoid"]),
            "open_roles": sum(len(c["jobs"]) for c in companies),
        },
        "companies": companies,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {OUT}\n  {payload['stats']}")


if __name__ == "__main__":
    main()
