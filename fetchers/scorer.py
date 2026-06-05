"""Score each role 0-100 against resume.md using keyword overlap + IDF."""
from __future__ import annotations
import re, math, pathlib, collections

STOP = set("""
a an and or but if then else for of to in on at by with from as is are was were
be been being have has had do does did will would could should may might can
this that these those i me my we our you your they them their it its he she
""".split())

ROOT = pathlib.Path(__file__).parent.parent
RESUME = ROOT / "resume.md"


def tokens(text: str) -> list[str]:
    text = text.lower()
    return [t for t in re.findall(r"[a-z][a-z0-9+#.]{1,}", text)
            if t not in STOP and len(t) > 2]


def score_jobs(companies: list[dict]) -> None:
    """Mutate companies in place, adding 'match' (0-100) to each job."""
    resume_text = RESUME.read_text() if RESUME.exists() else ""
    resume_terms = collections.Counter(tokens(resume_text))
    if not resume_terms:
        for c in companies:
            for j in c["jobs"]:
                j["match"] = 0
        return

    # Build IDF across all JDs so common words ("software", "engineer") count less
    jd_docs = []
    for c in companies:
        for j in c["jobs"]:
            jd_docs.append(set(tokens(j.get("jd", "") + " " + j["title"])))
    N = max(len(jd_docs), 1)
    df = collections.Counter()
    for doc in jd_docs:
        for t in doc:
            df[t] += 1
    idf = {t: math.log((N + 1) / (df[t] + 1)) + 1 for t in df}

    # Score each role
    raw = []
    for c in companies:
        for j in c["jobs"]:
            jd_terms = set(tokens(j.get("jd", "") + " " + j["title"]))
            overlap = jd_terms & set(resume_terms)
            s = sum(idf.get(t, 1) * math.log(1 + resume_terms[t]) for t in overlap)
            # Bonuses
            if c.get("day_one"): s += 8
            if c.get("perm_count", 0) > 100: s += 4
            if c.get("avoid"): s -= 15
            raw.append((c, j, s))

    # Normalize to 0-100
    if raw:
        lo = min(s for _, _, s in raw)
        hi = max(s for _, _, s in raw)
        span = hi - lo or 1
        for c, j, s in raw:
            j["match"] = round((s - lo) / span * 100)
