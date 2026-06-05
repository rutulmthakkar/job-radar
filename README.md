# Job Radar

Self-updating dashboard for an Android-engineer job search. Shows you:

- ⭐ **Day-one PERM filers** (no waiting period) — top priority list
- 🟢 Companies hiring Android devs **and** sponsoring PERM/I-140
- 📄 All certified PERM sponsors
- 🔴 Companies that announced layoffs in the **last 90 days** — avoid these

Searchable, filterable, mobile-friendly. Per-role **"Draft application"**
button copies a pre-filled prompt to your clipboard — paste into Claude
and get tailored resume bullets, cover letter, and interview prep.

Hosted free on GitHub Pages. Two cron jobs do all the work:
- **daily** — refresh layoffs, fetch latest jobs, redeploy site
- **weekly** — auto-discover new ATS slugs from the PERM sponsor list

## What's automated vs what isn't

**Fully automated:**
- Layoffs data (90-day rolling window from layoffs.fyi)
- Job listings (Greenhouse + Lever + Ashby public APIs)
- Company list (auto-discovered from DOL PERM sponsor names — no manual entry)
- Job descriptions (inlined into the dashboard so prompts are self-contained)
- Daily build + Pages deploy

**Manual (rarely):**
- `resume.md` — write your real resume once
- `data/perm_sponsors.csv` — refresh quarterly from DOL disclosure files
- `data/day_one_perm.json` — verify quarterly (community-curated; policies shift)

**Not automated (intentionally):**
- Submitting applications. Company ATSes require login, captchas, and
  often have strict ToS against automation. The "Draft application"
  button gets you 95% of the way: tap → paste into Claude → get tailored
  materials in seconds → submit through the portal yourself.

## Setup (≈10 minutes, one time)

1. Push this folder to a new GitHub repo (e.g. `job-radar`).
2. **Settings → Pages → Source: GitHub Actions**.
3. **Settings → Actions → General → Workflow permissions → Read and write**.
4. **Actions tab → weekly-discovery → Run workflow** (populates ATS slugs, takes ~5 min).
5. **Actions tab → daily-build → Run workflow** (builds the site).
6. Open `https://YOUR-USERNAME.github.io/job-radar/` — bookmark on phone.
7. Edit `resume.md`, commit. Daily run will pick it up.

## Using the "Draft application" button

1. On the dashboard, expand a company's roles.
2. Tap **📋 Draft application** on the role you want.
3. Open Claude (mobile app or claude.ai). Paste — it's all there:
   company context, the JD, your resume, structured instructions.
4. Claude returns: tailored bullets, cover letter, interview prep, ATS
   keywords, weakness mitigation.
5. Copy, paste into the company's portal, submit.

Time per application: ~2 minutes instead of 30.

## Architecture

```
data/perm_sponsors.csv      ← DOL sponsor list (manual quarterly refresh)
data/day_one_perm.json      ← curated day-one PERM list (manual quarterly)
data/discovered_slugs.json  ← AUTO (weekly): ATS slugs probed from sponsor names
data/company_slugs.json     ← optional manual extras
resume.md                   ← your resume (one-time fill-in)
        │
        ▼
fetchers/layoffs.py         ← layoffs.fyi public sheet, last 90 days
fetchers/perm_sponsors.py   ← loads CSV
fetchers/day_one_perm.py    ← loads JSON
fetchers/jobs.py            ← fetches Android roles + JD text
fetchers/discover.py        ← probes Greenhouse/Lever/Ashby for slugs
        │
        ▼
build.py                    ← merges everything → site/companies.json
        │
        ▼
site/index.html             ← dashboard (vanilla JS, mobile-first)
        │
        ▼
GitHub Pages
```

## Cost

$0. GitHub Actions free tier (2,000 min/month) — daily uses ~3 min,
weekly uses ~8 min. Pages is free for public repos.

## Maintenance

- **Quarterly**: refresh `data/perm_sponsors.csv` (download latest PERM
  disclosure XLSX from <https://www.dol.gov/agencies/eta/foreign-labor/performance>,
  group certified cases by employer, write CSV with `company,perm_count,fy`).
- **Quarterly**: skim `data/day_one_perm.json` against Blind/Reddit threads
  for any companies that changed policy.
- **As needed**: if a fetcher breaks, the bad data simply doesn't appear —
  the rest of the dashboard keeps working.
