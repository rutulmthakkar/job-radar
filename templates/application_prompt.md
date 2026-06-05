# Application Drafting Prompt Template

When you tap **"Draft application"** on a role, this prompt is built and
copied to your clipboard. Paste it into a fresh Claude chat. You'll get
back tailored materials in one shot.

The dashboard fills these placeholders automatically:

```
You are helping me apply for a software engineering role. Generate
tailored application materials.

COMPANY:        {company}
ROLE:           {title}
LOCATION:       {location}
APPLY LINK:     {url}
PERM SPONSOR:   {perm_count} certified PERM filings (FY{fy})
DAY-ONE PERM:   {day_one_yes_no}{day_one_notes}
LAYOFF STATUS:  {layoff_note}

--- JOB DESCRIPTION ---
{jd}
--- END JD ---

--- MY BASE RESUME (markdown) ---
{resume}
--- END RESUME ---

Produce in this exact order:

1. **Tailored resume bullets (5-7)** — rewrite the most relevant
   bullets from my resume to match the JD's language and priorities.
   Lead with metrics. Mirror keywords ATS will scan for.

2. **Cover letter (≤220 words)** — opens with a specific reason I
   want this role at this company (use a public signal: their product,
   recent launch, tech stack). One paragraph on fit. One on impact.
   No "I am writing to apply for…" filler.

3. **Three likely interview questions + my answers** — based on the JD,
   in STAR format, ≤80 words each, using my real experience.

4. **ATS keyword checklist** — 10 must-include terms from the JD that
   should appear verbatim in my application.

5. **One concern + how to address it** — what's the weakest match
   between me and this JD, and how do I get ahead of it.

Keep it tight. No filler. Markdown formatting.
```

When `has_resume` is false (no `resume.md` on disk), the dashboard
shows a notice and disables the button until you add one.
