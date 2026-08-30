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
4. Below **7/10**, or if the content doesn't already fit one side of A4, rewrite it.

   **Never rebuild the CV in new HTML/CSS or a different template.** Ayaan's own
   `.docx` has its own real formatting (fonts, spacing, margins, layout) — edit the
   bullet text of that exact file in place with `python-docx` and re-export it, so the
   result looks identical to his template with only the wording changed. Concretely:
   - Open the original with `docx.Document(path)`.
   - For each `RELEVANT EXPERIENCE` bullet paragraph you're rewording, set
     `paragraph.runs[0].text = new_text`, then delete every other run in that paragraph
     (`for r in p.runs[1:]: r._element.getparent().remove(r._element)`) — bullets are
     often split across several runs from past edits that all share identical
     formatting, so keeping just the first run and clearing the rest preserves the
     exact font/bold/italic with no visible change.
   - Only touch bullets (the accomplishment lines) — never section headers, job
     titles, company names, dates, education, skills, or contact info.
   - Keep each replacement bullet at or under the original bullet's character count.
     The original CV has essentially zero slack (it fills exactly one page with no
     spare line) — a replacement just a little longer than the original can flip a
     line-wrap from 1 line to 2, and that alone is enough to push the last line of the
     whole CV onto a second page. This actually happened once: shortening nine bullets
     by ~200 characters total still didn't help, because a single +16-character bullet
     wrapped onto a second line — the fix was shortening that one bullet back down,
     not shortening things elsewhere.
   - Truthfully (rephrase/cut, never invent) reframe wording to mirror the target
     posting's own language (e.g. "client relationship", "business case") where it's
     honestly supported by what Ayaan actually did.
   - Export to PDF via Word COM (`New-Object -ComObject Word.Application`, `.SaveAs`
     with format 17) — this uses the real installed Word engine, not a browser
     approximation, so the PDF looks exactly like the source .docx. Verify the ACTUAL
     page count via `$doc.ComputeStatistics(2)` before export and `pypdf`'s
     `len(PdfReader(path).pages)` after, waiting for the file size to stop changing
     first — Word COM's SaveAs can return before the file is fully flushed, and a
     stale read once reported 1 page for a file that was really 2 (66KB read vs 70KB
     on disk). Always kill any lingering `WINWORD` process afterward
     (`Get-Process WINWORD | Stop-Process -Force`) since COM automation can leave it
     running. Keep the original upload as `original-<filename>`, never delete it.
5. Save the final file as `Ayaan.Warraich.<FIRM>.CV.pdf` (rendered PDF) in
   `uploads/<id>/` — keep the edited `.docx` alongside it too, not just the PDF — and
   write `cv`, `cvFile`, and `cvAnalysis: {score, summary, action, analyzedAt}`
   (`action` is `"renamed"` or `"reworked_and_renamed"`) into `data.json`.
   **`cvFile` isn't in the PATCH endpoint's editable-fields list** (it's normally only
   set by the upload route), so update it via `app.load_data()`/`app.save_data()`
   directly rather than the API — `cv` and `cvAnalysis` can go through PATCH fine. The
   open dashboard picks it up within a few seconds via its poll — no need to tell it
   to refresh.

`app.render_cv_pdf()` (HTML+CSS → headless-browser PDF) still exists in `app.py` but
should only be used as a last resort when there's no real source document to edit in
place — e.g. the user pastes CV text directly with no file. Whenever a real `.docx` is
attached, always prefer editing it directly as above.

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
