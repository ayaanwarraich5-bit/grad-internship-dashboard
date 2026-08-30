# Grad and Internship Dashboard — project context

Local dashboard tracking Ayaan Warraich's 2026/27 graduate scheme and summer internship
applications. Replaces a published Claude Artifact, which couldn't store real files or
reliably persist edits.

## Who this is for

UK final-year BSc Economics student (University of Nottingham). Just finished a 10-week
summer internship at **abrdn (Aberdeen Investments)**, rotating across three Client Group
teams: FC Screening & Monitoring, Distribution Governance & Client Controls, and the
Strategic Insurance Group. Split between Edinburgh and 280 Bishopsgate, London. Awaiting
the full-time conversion decision.

Target: **asset management and investment management**, specifically **client-facing or
investments** roles.

## Job search strategy — this drives which firms belong where

- **Not applying to:** top investment banks, trading desks, quant roles.
- **Backup only, never priority:** pensions, insurance, consulting.
- **Grad schemes (`type: "grad"`):** smaller / independent asset managers, wealth managers
  and private banks where he's a strong fit and the odds beat the household names —
  e.g. Insight Investment, Baillie Gifford, Rathbones, Vanguard, Northern Trust, Julius Baer.
- **Summer internships (`type: "intern"`), not grad schemes, specifically at:**
  - Bulge-bracket banks' **asset management arms** and **private banks** — their grad
    schemes are very hard to get, but the internships are comparatively easier
    (GSAM, J.P. Morgan Private Bank, Morgan Stanley Investment Management).
  - **Elite-boutique AM arms** (Redburn, Lazard Asset Management).
  - "Private bank" here means **only private banks that are arms of bulge-bracket banks**.
    Independent private banks — Weatherbys, Julius Baer, Northern Trust — go on the
    **grad** track instead.
- **Priority principle:** fewer roles he genuinely wants beats maximising volume.
- **Sources:** Trackr (`app.the-trackr.com/uk-finance`), Bright Network, SEO London.

## CV workflow

For each target role: (1) assess CV suitability **against that specific role**, (2) tailor
it as a PDF **only if genuinely necessary**, (3) save/rename as
`Ayaan.Warraich.<FIRMNAME>.CV.pdf`. If it's already a good fit, **just rename it — don't
rewrite it**. Two hard rules: the **7/10 threshold** (rewrite only below 7, or if it
doesn't already fit one page) and **single-side A4**. Never invent experience; rewrites
rephrase and reprioritise truthful content only. Never delete the original upload — it's
kept as `uploads/<id>/original-<filename>`.

## Ongoing maintenance behaviour

- On "check Trackr" / "check <firm>": browse live (this environment has real internet
  access, unlike the old Artifact sandbox) and edit `data.json` directly. One file, one
  source of truth — no publish/conflict dance.
- **Only mark `status: "open"` when a genuinely current-cycle opening date is confirmed.**
  A Trackr row showing a single date is last year's reference, not this year's. This
  dashboard has been burned by ambiguous date columns before.
- New firms go into `grad` / `intern` / `backup` per the strategy split above.
- Keep `notes` specific about which sub-track/division fits the client-facing/investments
  interest whenever a firm publishes multiple tracks — the way Schroders, BlackRock and
  Redburn already are. Generic notes are fine only when a firm genuinely doesn't split
  by division.
- The running page polls `GET /api/applications` every 3s, so edits made to `data.json`
  from chat show up in the open browser tab without a manual refresh.

## Architecture

- `app.py` — Flask server. JSON REST API + CV file upload/download + the two AI endpoints.
- `data.json` — the single source of truth, one application object per line (kept
  one-per-line deliberately so chat edits and diffs stay readable).
- `uploads/<id>/` — real CV files on disk. Nothing is base64'd into JSON.
- `static/` — `index.html`, `styles.css`, `app.js`. No build step, no framework.
- Run: `python app.py` → http://127.0.0.1:5173

### Data model

`id`, `type` (`personal|grad|intern|backup`), `company`, `role`, `sector`,
`stage` (`watchlist|applied|testing|interview|final|awaiting|offer|rejected`),
`status` (`open|not_yet_open|unknown`; absent for `personal`), `deadlineLabel`,
`dateISO` (or null), `sourceUrl`, `notes`, and optionally `cv`, `cvFile`,
`cvAnalysis`, `subRoles`, `selectedProgramme`.

### AI: CV analysis is chat-only, not a button

There's no `/analyse-cv` route. It existed once, shelling out to a local Claude CLI —
but that CLI only ever lived inside the dev environment Claude Code's own tools run
commands in, never on the machine actually running the browser, so the button could
never really work there and was removed.

**When asked in chat** to "analyse the CV on the X row":
1. Read the attached file from `uploads/<id>/` directly (`app.extract_text()` handles
   PDF/DOCX extraction, reusable via `python -c "import app; ..."` from this project
   root).
2. If `selectedProgramme.url` is set, fetch that posting's text with
   `app.fetch_posting_text()` and score against it; otherwise fall back to the row's
   `role`/`sector`/`notes` and say so in the summary.
3. Score 1–10 for fit to *that specific role* (tailoring, not general CV quality) against
   the strategy in section 2 above.
4. Below **7/10**, or if the content doesn't already fit one side of A4, rewrite it
   truthfully (rephrase/cut, never invent) and render it with `app.render_cv_pdf()` —
   verified one-page A4 via headless Edge/Chrome, retried at tighter spacing until it
   fits. Keep the original upload as `original-<filename>`, never delete it.
5. Save the final file as `Ayaan.Warraich.<FIRM>.CV.pdf` in `uploads/<id>/` and write
   `cv`, `cvFile`, and `cvAnalysis: {score, summary, action, analyzedAt}` (`action` is
   `"renamed"` or `"reworked_and_renamed"`) into `data.json`. The open dashboard picks
   it up within a few seconds via its poll — no need to tell it to refresh.

### AI: find roles is still a button

`POST /api/applications/<id>/find-roles` shells out to the Claude Code CLI
(`claude -p ... --output-format json`) so it reuses the existing login rather than
needing an API key. If the CLI isn't reachable the endpoint returns a message pointing
to chat instead. When asked to "find the specific roles at X", write `subRoles` as
`[{name, highlighted, reason, url}]` — capture the **direct application URL** per track,
not just the name; that link is what lets `selectedProgramme` pin a row to a real
posting so CV analysis (above) can read the actual job description.
