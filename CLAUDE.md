# Grad and Internship Dashboard — project context

Local dashboard tracking Ayaan Warraich's 2026/27 graduate scheme and summer internship
applications. Replaces a published Claude Artifact, which couldn't store real files or
reliably persist edits.

## Who this is for

UK final-year BSc Economics student (University of Nottingham). Completed a 10-week
summer internship at **abrdn (Aberdeen Investments)**, rotating across three Client Group
teams: FC Screening & Monitoring, Distribution Governance & Client Controls, and the
Strategic Insurance Group. Split between Edinburgh and 280 Bishopsgate, London.
**Received a full-time offer from abrdn (Sept 2026).** That offer is now the floor every
other application is measured against — see strategy below.

Target: **investment analyst or client group / client-facing roles**, exclusively at
asset managers judged bigger or as prestigious as abrdn, plus bulge-bracket private banks.
**London only** (added 2026-09-18) — this is why Baillie Gifford was dropped despite
clearing the prestige bar; Edinburgh/regional-only roles are out regardless of firm.

## Job search strategy — this drives which firms belong where

Rewritten 2026-09-06 following the abrdn offer. This **replaces** the old "smaller/
independent firms for better odds" logic entirely — that framing is retired. The bar is
now quality, not odds: with abrdn as a confirmed offer in hand, a new application only
makes sense if the firm is a genuine step up.

- **In scope, `type: "grad"` or `"intern"` — whichever the firm actually runs:**
  - **Bulge-bracket private banks** (grad or internship, either now fair game — not
    internship-only). E.g. Barclays, J.P. Morgan Private Bank, UBS.
  - **Bulge-bracket banks' asset management arms** (grad or internship). E.g. GSAM,
    Morgan Stanley Investment Management, J.P. Morgan Asset Management.
  - **Elite or large independent asset managers** — judged bigger (AUM) or at least as
    prestigious/selective as abrdn. E.g. BlackRock, Vanguard, Capital Group, Fidelity,
    Schroders, Franklin Templeton, PIMCO, Columbia Threadneedle, Insight Investment,
    Northern Trust, Baillie Gifford (smaller AUM than abrdn but judged "as good" on
    selectivity/prestige — a judgment call, flagged on that row), Lazard Asset Management.
- **Explicit exclusions, even if previously tracked:**
  - Any asset manager judged **not** bigger or as good as abrdn (this is what took out
    most of the old "smaller/independent, better odds" watchlist — Rathbones, Evelyn
    Partners, St James's Place, GIB AM, Ruffer, Russell Investments, VenCap, Barings,
    Principal Asset Management, Janus Henderson, M&G, Skybound, etc.).
  - **Independent (non-BB) private banks** — Julius Baer, Weatherbys, EFG International.
    Previously routed to the grad track as an exception; no longer in scope at all now
    that private banks must be bulge-bracket.
  - **Any pensions or insurance employer** — WTW, Aon, Legal & General, Aviva Investors
    (insurer-owned). No backup tier for these anymore; they're just out.
  - **Consulting**, except **BCG, Bain, and McKinsey** specifically. Accuracy is out.
  - **Marshall Wace** — excluded by name, regardless of prestige.
  - Top investment banks, trading desks, quant roles — unchanged from before.
- **Backup tier (`type: "backup"`):** now reserved solely for BCG / Bain / McKinsey, if
  and when he points at a specific role there — not a priority, and not populated yet.
  Everything that used to live in backup (pensions, insurance, other consulting) is a
  flat exclusion now, not a lower tier.
- **Grandfathered regardless of the above:** firms already applied to before this reset —
  Barclays, J.P. Morgan Private Bank, BlackRock (grad), Macquarie, UBS, GSAM — stay on
  the dashboard as the applied/in-progress record even if one wouldn't individually clear
  today's bar on paper.
- **Priority principle:** fewer roles he genuinely wants beats maximising volume — more
  true than ever now that abrdn is a confirmed floor, not a hoped-for outcome.
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
- **Watchlist rows need checking often enough to actually catch the opening, not just
  confirm it opened.** On 2026-09-18 Ayaan reported Capital Group and Schroders both
  opened and he found out too late to apply with good odds (Schroders he applied to
  anyway, ~2 weeks late; Capital Group he skipped entirely) — the gap was checking
  cadence, not the strategy. If a while has passed since a `watchlist` row's firm was
  last checked, proactively re-check rather than waiting to be asked.

## Architecture

- `app.py` — Flask server. JSON REST API + CV file upload/download/view.
- `data.json` — the single source of truth, one application object per line (kept
  one-per-line deliberately so chat edits and diffs stay readable).
- `uploads/<id>/` — real CV files on disk. Nothing is base64'd into JSON.
- `static/` — `index.html`, `styles.css`, `app.js`. No build step, no framework.
- Run: `python app.py` → http://127.0.0.1:5173

### Auto-start at logon — and a hard environment limit discovered while fixing it

The server used to die every reboot/logout and need a manual restart each time.

**Read this before touching auto-start again.** On 2026-09-09, checking this session's
own `(Get-CimInstance Win32_OperatingSystem).LastBootUpTime` / `systeminfo` returned a
boot time from **13 days before** the reboot Ayaan had just done. That's hard proof this
session's Bash/PowerShell tools run in a persistent background context on his machine
that never itself experiences his real logons or reboots — the same underlying gap
already known from the Claude CLI (below) and from `schtasks`/`ScheduledTasks` both
failing "Access is denied" here even for a trivial task. Startup-folder scripts,
Scheduled Tasks — anything gated on "at logon" or "at boot" — **cannot be verified from
this session by testing it here**, no matter how clean the test looks. Manually running
a `.vbs`/`.bat`/task action and watching it succeed only proves the script's own logic
is correct; it proves nothing about whether Windows will actually fire it at Ayaan's
real logon. Two auto-start fixes (a `pythonw.exe`-direct `.vbs`, then a `.bat`-wrapped
version with logging) both looked verified from here and were both silent no-ops for
him. **Don't repeat that mistake** — say so explicitly and get him to confirm after a
real reboot, rather than reporting success off a manual test.

Current setup, two layers:
- `tools/launch_dashboard.bat` — logs a timestamped line then runs `python.exe app.py`,
  both appended to `dashboard_startup.log` in the project root (git-ignored). Deliberately
  uses `python.exe` not `pythonw.exe` so a crash has output to look at.
- `tools/start_dashboard.vbs` — a copy sits in the Startup folder
  (`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\GradDashboardAutoStart.vbs`),
  sleeps 20s (OneDrive remount headroom), then runs the `.bat` hidden. **Unconfirmed
  whether this actually fires at Ayaan's real logon** — two attempts produced zero lines
  in `dashboard_startup.log`, meaning either the Startup item never ran or something
  failed before the `.bat`'s very first line, and it couldn't be diagnosed further from
  this session. Kept as a harmless second layer, not trusted as the primary fix.
- **Scheduled Task, registered by Ayaan himself** (not from a Claude session — that's
  the whole point): `schtasks /create /SC ONLOGON /TN "GradDashboardAutoStart" /TR
  "\"...\tools\launch_dashboard.bat\"" /DELAY 0000:20 /F`, run from a PowerShell window
  he opens normally. This is the mechanism actually expected to work, since it's created
  from his real session rather than this one.

If he reports it's still not starting after a real reboot: ask him to paste
`dashboard_startup.log` (git-ignored, local only) rather than guessing again — an empty
file still narrows it down (Startup/Task Scheduler trigger itself didn't fire), and a
file with a Python traceback tells you exactly what to fix.

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
