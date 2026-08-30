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


## CV, cover letters, written answers — see APPLICATIONS.md

That work does **not** happen in this session. It has its own brief in
[`APPLICATIONS.md`](APPLICATIONS.md): the full experience bank, the rules for editing
the `.docx` template in place, the recruiter persona, feedback style, and the
writing-style rules for anything Ayaan submits.

The dashboard's only job here is **record keeping**. Ayaan writes and refines a CV in
that separate workspace, then drops the finished file onto the relevant row himself so
there's a record of what he actually submitted. Don't rewrite CVs from this session —
point him at the applications workspace instead.

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

- `app.py` — Flask server. JSON REST API + CV file upload/download/view.
- `data.json` — the single source of truth, one application object per line (kept
  one-per-line deliberately so chat edits and diffs stay readable).
- `uploads/<id>/` — real CV files on disk. Nothing is base64'd into JSON.
- `static/` — `index.html`, `styles.css`, `app.js`. No build step, no framework.
- Run: `python app.py` → http://127.0.0.1:5173

### Data model

`id`, `type` (`personal|grad|intern|backup`), `company`, `role`, `sector`,
`stage` (`watchlist|applied|online_assessment|hirevue|interview|assessment_centre|
awaiting|offer|rejected`),
`status` (`open|not_yet_open|unknown`; absent for `personal`), `deadlineLabel`,
`dateISO` (or null), `sourceUrl`, `notes`, and optionally `cv`, `cvFile`,
`cvAnalysis`, `subRoles`, `selectedProgramme`.

### CV files on a row are a record, not a task

The row's `cv` / `cvFile` / `cvAnalysis` fields record the CV Ayaan actually submitted.
He attaches it himself through the dashboard's drop zone once he's finished writing it
in the applications workspace (see `APPLICATIONS.md`).

If he asks for CV work *here*, point him at that workspace rather than doing it from
this session — it has the experience bank, the template rules, and the writing rules.

Two mechanical notes if you ever do write these fields from chat:
- **`cvFile` isn't in the PATCH endpoint's editable-fields list** (it's normally only
  set by the upload route), so write it via `app.load_data()` / `app.save_data()`
  directly. `cv` and `cvAnalysis` go through PATCH fine.
- `cvAnalysis` is `{score, summary, action, analyzedAt}` where `action` is `"renamed"`
  or `"reworked_and_renamed"`. The page shows it as a badge on the row.

### AI: find roles is also chat-only, not a button

There's no `/find-roles` route either — same reason as CV analysis: it shelled out to a
Claude CLI that only exists in the dev environment Claude Code's tools run in, never on
the machine actually running the browser. `data.json`'s `subRoles` field and the pill UI
are unchanged; only the trigger moved to chat.

**When asked in chat** to "find the specific roles at X": browse from Trackr's company
page (`app.the-trackr.com`) through to the firm's own careers site, judge each distinct
track against the strategy in section 2 above, and write `subRoles` as
`[{name, highlighted, reason, url}]` directly into that row in `data.json` — capture the
**direct application URL** per track, not just the company careers homepage; that link is
what lets `selectedProgramme` pin a row to a real posting so CV analysis (above) can read
the actual job description. The dashboard picks up the new pills within a few seconds via
its poll.
