"""Skill-weighted job scoring against resume.md.

Score = (weighted skills the JD asks for that the resume also has) /
        (weighted skills the JD asks for) * 100

Designed so scores are intuitive: 85% means the resume covers 85% of
what the JD requires. Numbers don't shift when new roles are added.
Company-level signals (day-one PERM, layoffs) are surfaced as pills/filters
in the dashboard and do not affect this score.
"""
from __future__ import annotations
import re, pathlib

ROOT = pathlib.Path(__file__).parent.parent
RESUME = ROOT / "resume.md"

# Weighted skill dictionary, tuned for Android engineering roles.
# Key = lowercase phrase to match in JD/resume text. Value = importance.
SKILLS: dict[str, float] = {
    # --- core platform (highest weight) ---
    "android": 4, "kotlin": 4, "jetpack compose": 4, "compose": 3,
    "android sdk": 3, "android studio": 2,

    # --- architecture & async ---
    "mvvm": 3, "mvi": 2, "mvp": 1, "viper": 1,
    "coroutines": 3, "flow": 2.5, "stateflow": 2, "livedata": 1.5,
    "viewmodel": 2, "repository pattern": 1.5, "clean architecture": 1.5,
    "hilt": 2, "dagger": 2, "koin": 1, "dependency injection": 2,

    # --- libraries / jetpack ---
    "retrofit": 2, "okhttp": 1.5, "room": 1.5, "realm": 1, "sqlite": 1,
    "datastore": 1, "workmanager": 1.5, "navigation": 1, "lifecycle": 1,
    "paging": 1, "glide": 1, "coil": 1, "picasso": 0.5,
    "exoplayer": 1.5, "camerax": 1, "media3": 1,
    "firebase": 1, "crashlytics": 1, "analytics": 1,

    # --- languages ---
    "java": 1.5, "swift": 0.5, "rxjava": 1.5, "rxkotlin": 1,
    "c#": 0.5, "python": 0.5, "sql": 0.5,

    # --- testing ---
    "junit": 1.5, "mockk": 1, "mockito": 1, "robolectric": 1,
    "espresso": 1, "turbine": 1, "ui testing": 1, "unit testing": 1,

    # --- tools / workflow ---
    "gradle": 1, "ci/cd": 1.5, "github actions": 0.5, "jenkins": 0.5,
    "git": 0.5, "perforce": 0.5, "jira": 0.3, "confluence": 0.3,
    "agile": 0.3, "scrum": 0.3, "code review": 1,

    # --- product / scale signals (often in JD bullets) ---
    "consumer": 1, "scale": 1, "millions of users": 1.5,
    "performance": 1, "modular": 1, "modularization": 1,

    # --- AI/agentic (your differentiator) ---
    "ai": 0.5, "llm": 0.5, "agent": 0.5, "mcp": 1,
}

# Penalty terms — if the JD requires these and the resume lacks them,
# subtract a flat percentage. Strong domain mismatches.
HARD_REQUIREMENTS: dict[str, float] = {
    "ios": 0,        # iOS-only roles aren't relevant; will be filtered separately
    "react native": 5,
    "flutter": 5,
    "xamarin": 3,
}


def _present(phrase: str, text: str) -> bool:
    # word-ish boundary match; phrase may contain spaces or special chars
    pat = r"(?<![a-z0-9])" + re.escape(phrase) + r"(?![a-z0-9])"
    return re.search(pat, text) is not None


def _score_one(resume_text: str, jd_text: str, title: str) -> tuple[int, dict]:
    rt = resume_text.lower()
    jt = (jd_text + " " + title).lower()

    earned, possible = 0.0, 0.0
    matched, missing = [], []
    for skill, w in SKILLS.items():
        if _present(skill, jt):
            possible += w
            if _present(skill, rt):
                earned += w
                matched.append(skill)
            else:
                missing.append(skill)

    if possible < 3:
        if "android" in jt and ("engineer" in jt or "developer" in jt):
            return 50, {"note": "JD too sparse; title-based fallback (android engineer)."}
        return 30, {"note": "JD too sparse; generic fallback."}

    base = (earned / possible) * 100
    penalties = []

    for skill, pen in HARD_REQUIREMENTS.items():
        if _present(skill, jt) and not _present(skill, rt):
            base -= pen
            if pen > 0:
                penalties.append(f"JD requires {skill} (not in resume, -{pen}pts)")

    score = max(0, min(100, round(base)))
    reasons = {
        "matched": matched,
        "missing": missing,
        "penalties": penalties,
        "bonuses": [],
        "calc": f"Skill match: {earned:.1f} / {possible:.1f} = {score}%",
    }
    return score, reasons


def score_jobs(companies: list[dict]) -> None:
    """Mutate companies in place, adding 'match' (0-100) to each job."""
    resume_text = RESUME.read_text() if RESUME.exists() else ""
    if not resume_text.strip():
        for c in companies:
            for j in c["jobs"]:
                j["match"] = 0
                j["match_reasons"] = {"note": "No resume.md content."}
        return

    for c in companies:
        for j in c["jobs"]:
            score, reasons = _score_one(resume_text, j.get("jd", ""), j.get("title", ""))
            j["match"] = score
            j["match_reasons"] = reasons
