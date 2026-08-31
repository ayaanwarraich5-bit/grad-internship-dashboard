# Handover — Grad and Internship Dashboard

Written 2026-08-31, when the build conversation that produced this project approached
its context limit. This is **not** the primary reference for working on the project —
`CLAUDE.md` and `APPLICATIONS.md` are, and a fresh Claude Code session started in this
folder loads `CLAUDE.md` automatically. This document exists for what those two files
don't cover: the debugging journey, the reasoning behind decisions that could otherwise
look arbitrary, and the state of things that were mid-flight when the conversation
ended. Read it once, then it's git history.

## Starting a new session

A brand new chat, opened with this folder as the working directory, already gets:

- `CLAUDE.md`, automatically — dashboard architecture, data model, job-search strategy,
  maintenance rules.
- `APPLICATIONS.md`, only if told to read it — the CV/cover-letter/interview-prep
  brief. It's deliberately **not** auto-loaded by Claude Code the way CLAUDE.md is, so
  a plain dashboard session doesn't carry writing-workflow context it won't use, and a
  writing session that needs it must be told explicitly (see the paste-in below).
- The full git history (`git log`) and this file.

It does **not** get: anything said in this conversation that never made it into a
committed file. Everything that mattered has been pushed — check `git log --oneline`
against the changelog below if anything feels missing.

**Two separate paste-in prompts, for two separate kinds of work:**

For dashboard engineering (the Flask app, the frontend, features, bugs) — nothing
needed. Just open a session here and describe the task; `CLAUDE.md` loads on its own.

For CV/cover letter/interview work, start that chat in this same folder and paste:

```
Read APPLICATIONS.md in this project root before doing anything, and follow it.

It's the brief for all CV, cover letter, written answer and interview prep work:
my background, the full experience bank, the recruiter persona to judge against,
the feedback style I want, and the writing rules for anything I'll actually submit.

For CV edits use tools/cv_tools.py — don't hand-roll the docx mechanics and don't
rebuild my CV in a new template, it has its own formatting that must survive
untouched. Python is at %LOCALAPPDATA%\Programs\Python\Python312\python.exe (it is
not on PATH as `python`).

Don't touch data.json, app.py, static/, or uploads/ — that's the dashboard, a
separate concern. I'll attach finished files to it myself.

Be brutally honest, like a recruiter with 200 CVs to get through. If something is
weak, say so plainly and say what would fix it. No filler praise.

First task: <describe it here>
```

## What this project is

A local Flask dashboard tracking Ayaan's 2026/27 graduate scheme and summer internship
applications, replacing an earlier Claude Artifact that couldn't store real files or
reliably persist edits (the Artifact tool can't read back a published page's live state
before pushing an update, so any edit made directly on the page risked silent
overwrite). `CLAUDE.md` §1 has the full "who this is for" and job-search strategy;
that's not repeated here.

Run it: `python app.py` → `http://127.0.0.1:5173`. On this machine, `python` isn't on
PATH — use `%LOCALAPPDATA%\Programs\Python\Python312\python.exe`.

## How the build actually went — chronological, with the reasoning

This section is the part a fresh session can't get from the code alone: *why* things
are shaped the way they are, including the dead ends.

**1. Initial rebuild** (`9805d2f`). The original ask was a full local rewrite of the
Artifact: Flask + JSON REST API, real file uploads instead of base64, `data.json` as
one authoritative file both the browser and Claude Code read/write. Seeded with 29
real researched rows. Python and the requisite packages weren't installed on this
machine at the start — that had to happen first.

**2. The CLI-invocation dead end** (`5636482`, `6c872fb`, then reversed by `cbe2604`,
`eafbabc`). The original design had **Analyse CV** and **Find roles** buttons that
shelled out to a local `claude` CLI so the AI work could run from the browser without
an API key. This never worked, for a specific and non-obvious reason worth
understanding if anything like it is ever attempted again:

The `claude` executable this session's own tools can find and run
(`%APPDATA%\Claude\claude-code\<version>\claude.exe`) lives inside the **desktop app's
sandboxed environment that Claude Code's own tool-execution runs in — not on Ayaan's
actual interactive Windows session.** Proven by direct comparison: this session's
`Bash`/`PowerShell` tools could find and run that CLI, but when Ayaan opened his own
Command Prompt and ran the exact same path, Windows said the folder didn't exist.
Same computer name, same username, same resolved `%APPDATA%` — genuinely different
execution contexts under the hood. A Flask subprocess call to that CLI from `app.py`
inherits whichever context is running the server, so it hit the same wall from the
browser side too.

Once identified, this wasn't fixable by more troubleshooting — it needed the CLI
logged in via `/login`, which requires an interactive browser popup that no headless
tool call can drive. So the design changed: **both buttons were removed entirely**, and
the same work now happens by asking Claude Code directly in chat, which reads/writes
`data.json` and `uploads/` directly with no subprocess involved. This is simpler and
more reliable than the button ever was. The removal also deleted ~220 lines of now-dead
CLI-invocation plumbing (`find_claude_cli`, `run_claude`, `extract_json_object`,
`CLI_MISSING`, `STRATEGY`) — none of it is coming back.

**3. The cloud-routine dead end.** Separately, a scheduled cloud routine was set up via
`/schedule` to check Trackr and Bright Network weekly and commit findings to GitHub.
This also hit real friction and was abandoned (routine left `enabled: false`, still
visible at claude.ai/code/routines if ever revisited):

- Cloud routines run in Anthropic's cloud sandbox, not on Ayaan's machine — they can
  only reach a GitHub repo, never `data.json` or the running Flask server directly.
- The sandbox's default network egress policy blocks *all* outbound web access
  (confirmed by testing a neutral control domain, not just Trackr) — Trackr research
  needs an environment with an explicit allowlist, which needed setting up in a
  separate product surface (`claude.ai/code` environments, not the Anthropic Console,
  which has its own unrelated environment registry) and a GitHub App connection.
- Even fully configured, a cloud routine's commits only land on GitHub — bringing them
  into the locally-running dashboard still needs a manual `git pull` or an ask-in-chat
  step, so "automatic" was never going to mean fully hands-off end to end.

Conclusion, and current standing recommendation: **just ask Claude Code in chat** —
"check Trackr", "check Bright Network" — whenever wanted. It's immediate, uses this
session's real browsing, and writes straight to the live `data.json`. This is strictly
simpler and more reliable than the cloud-routine path for a personal-scale dashboard.

**4. The CV-rework formatting mistake, and the fix** (`3eab4ab`). Early CV rework
(for a Barclays application) rebuilt the CV from scratch in new HTML/CSS via a headless
browser — different fonts, different layout, nothing like Ayaan's real template. This
was explicitly wrong and had to be redone. The corrected approach — edit the bullet
text of a copy of the real `.docx` in place with `python-docx`, export through actual
Word (COM automation), never touch anything but the wording — is now packaged as
`tools/cv_tools.py` (`57c839d`) rather than something to reconstruct by hand each time.

Along the way, two non-obvious failure modes got documented because they cost real
iteration time:

- **The one-page budget is per-bullet, not aggregate.** The CV fills exactly one page
  with zero spare line. Shortening nine bullets by 200+ characters total still
  overflowed to two pages once, because a *different* single bullet grew by only ~16
  characters and flipped its own line-wrap from 1 line to 2 — and that alone pushed the
  last line of the whole document onto page 2. The fix was shortening that one bullet
  back down; shortening bullets elsewhere didn't matter to page count at all.
  `cv_tools.apply_bullets(..., strict=True)` now enforces a per-bullet ceiling and
  raises rather than letting this happen silently.
- **Word COM page counts can lie if read too early.** `SaveAs` can return before the
  PDF is fully flushed to disk; a same-instant page count once reported 1 page for a
  file that was really 2 (66KB read vs 70KB on disk moments later).
  `cv_tools.export_pdf()` waits for the file size to stop changing before trusting
  `pypdf`'s page count.
- Also: `$word.Quit()` under COM automation routinely blocked for **minutes**.
  `export_pdf()` skips it and kills only the Word process it started (recording
  pre-existing WINWORD PIDs first, so a document Ayaan has open elsewhere is never
  touched) — export dropped from a 2-minute timeout to ~4 seconds.

**5. Splitting CV/cover-letter work out of the dashboard session** (`20422d2`). Ayaan
chose to do CV, cover letter, and interview-prep work in a separate chat to keep this
project's context lighter, refining there and dropping the finished file into the
dashboard himself as a record. `APPLICATIONS.md` was created as that session's
self-contained brief (experience bank, recruiter persona, writing-style rules, the
`cv_tools.py` recipe) and `CLAUDE.md` was cut from ~250 lines to 113, keeping only what
the dashboard session itself needs.

**6. The cover-letter-overwrites-CV bug, found and fixed** (`57c839d` → `95cbc9b`).
Storage was generalized from one CV slot per row to one CV *and* one cover letter slot
(`/api/applications/<id>/docs/<kind>`, `kind` = `cv` or `cover`), each independently
upload/view/download/removable. This exposed a latent bug worth knowing about even
though it's fixed: **the original single-file upload code deleted every file in a
row's folder except kept originals** on each new upload. With one document per row
that was invisible; the moment a second kind existed, it would have silently destroyed
whichever file wasn't just uploaded. Fixed so uploads/removes only ever touch the file
the specific `kind` points at — verified with tests including the exact "upload CV,
then upload cover, CV must survive" case.

That fix wasn't quite complete: a **second, separate bug** in the click-to-browse path
(`article.querySelector('[data-act="file"]')` matched the *first* file input in the
row regardless of which drop zone was actually clicked, so clicking the cover-letter
box silently opened the CV's file picker) shipped in the same commit as the storage
change and had to be fixed separately in `95cbc9b`, scoping the lookup to the clicked
box. **This is now confirmed working by Ayaan's own real use** — the Goldman Sachs
Asset Management row currently has both a real CV and a real cover letter attached,
uploaded seconds apart, distinct filenames. If a similar report ever comes up again,
suspect a **stale browser tab running old JS in memory** first (a long-lived tab never
re-fetches `app.js` until the page itself reloads — the 3-second poll only refreshes
data, not code) before assuming the bug is back.

**7. Progress-tracking beyond the coarse stage** (`ecafebd`, `59d7ee9`). The stage
dropdown (watchlist → applied → online assessment → HireVue → interview → assessment
centre → awaiting → offer/rejected) says *where* an application is, but not whether a
specific assessment has actually been sat — "at the online assessment stage" could mean
either. Each live row (applied through awaiting; not watchlist, not closed) got
independent OA/HireVue trackers (not required / to do / done), collected into a **To
do** card in the rail with a one-click tick to mark done. Gated on stage rather than
stored data, so rejecting or accepting a row silently drops its outstanding chores.

## Known state, right now

- **39 rows** in `data.json` (1 personal, 27 grad, 7 intern, 4 backup).
- Real attachments exist on 3 rows: `g28` (Barclays — CV + cvAnalysis, tasks: OA done),
  `i2` (GSAM — CV + cover letter, the confirmation case above), `b4` (PIMCO — CV; this
  row was added by Ayaan directly through the dashboard between sessions, not by any
  automated process — a reminder that `data.json` can change from outside any given
  chat and should be read fresh, not assumed).
- Working tree is clean; `main` is pushed to
  `https://github.com/ayaanwarraich5-bit/grad-internship-dashboard` (private).
- A disabled cloud routine (`trig_012pq4WvNvVavvCTunDR7D6E`, "Weekly Trackr/Bright
  Network grad dashboard sync") still exists but is `enabled: false` and won't fire.
- Two harmless cosmetic artifacts to expect and ignore: (a) `uploads/<id>/` can be left
  as an *empty* directory after a delete, because OneDrive briefly locks folders during
  sync and `rmdir` fails silently where `save_data`'s file-write retry (below) already
  succeeds for the JSON itself; (b) the smoke test at
  `%TEMP%\...\scratchpad\smoke.py` (session-local, not in the repo) hardcodes nothing
  about row count anymore — it captures a baseline at the top of its own run.

## Environment specifics worth knowing before debugging anything

- **Python**: `%LOCALAPPDATA%\Programs\Python\Python312\python.exe`. Not on PATH.
  `pip install -r requirements.txt` covers Flask, pypdf, python-docx.
- **No local `claude` CLI usable from this machine's real interactive session** — see
  §2 above. Don't re-attempt subprocess-based Claude invocation from `app.py`; do the
  work in chat instead.
- **OneDrive sync locks.** This entire project lives inside a synced OneDrive folder.
  `save_data()` in `app.py` retries `os.replace()` with backoff (up to ~2s total)
  because OneDrive taking a brief exclusive lock on `data.json` mid-sync caused a real
  `PermissionError` that silently ate a write once (surfaced as a 500 on delete, but
  could equally have swallowed a stage change or a note). If a save ever seems to not
  stick, suspect this class of issue before assuming application logic is wrong.
- **Word COM for CV export** — see §4. Only available because Microsoft Word is
  installed on this machine; there's no fallback path if it weren't (the earlier
  `app.render_cv_pdf()` HTML→headless-browser approach still exists in `app.py` for
  that scenario, but is explicitly documented as last-resort-only now).
- **Headless Edge/Chrome** is used for the one remaining PDF-rendering path
  (`app.render_cv_pdf`) and was previously used for CV rework before the Word-COM
  approach replaced it as primary.
- **The live-reload/polling design**: the frontend polls `GET /api/applications` every
  3 seconds, skipping the poll entirely while any field is focused so a chat-driven
  edit landing mid-keystroke can never clobber what's being typed — it adopts the
  fresh state on the very next tick after blur instead. This was deliberately
  simplified once (an earlier version tried to hold a "pending remote snapshot" and
  apply it after blur, which could apply a *stale* snapshot taken before a save
  completed and flash old text back — removed in favour of just skipping polls
  outright while editing).

## Architecture summary

(Full detail in `CLAUDE.md`; this is just orientation.)

| File | Lines | Role |
|---|---|---|
| `app.py` | 572 | Flask REST API, document upload/download/view, PDF/DOCX text extraction, job-posting fetch, HTML→PDF fallback renderer |
| `static/app.js` | 794 | All frontend logic, no framework, no build step |
| `static/index.html` | 89 | Page shell |
| `static/styles.css` | 462 | Full design system (light/dark, responsive) |
| `tools/cv_tools.py` | 205 | CV rework mechanics — inspect/apply_bullets/insert_after/export_pdf |
| `CLAUDE.md` | 113 | Dashboard's own persistent context, auto-loaded |
| `APPLICATIONS.md` | 310 | CV/cover-letter/interview-prep brief, loaded on request |
| `data.json` | — | Single source of truth, one JSON object per line |
| `uploads/<id>/` | — | Real files, never base64'd |

No test suite lives in the repo — the smoke test used throughout this build lives in
the session's scratchpad temp directory, not the project. If a fresh session wants
repeatable regression coverage, writing one properly into the repo (e.g.
`tests/smoke.py`) would be a reasonable thing to propose rather than assume exists.

## Where things are genuinely open

- **No automated Trackr/Bright Network checking.** Deliberate, per §3. Ask in chat.
- **`subRoles` (the starred/unstarred track breakdown per firm) is populated on very
  few rows.** It requires live browsing per firm and was never systematically run
  across all 39 — only done ad hoc when asked ("find the specific roles at X").
- **No automated test suite in the repo.** See above.
- The disabled cloud routine is inert but not deleted (the API used to create it has no
  delete action — only claude.ai/code/routines does, and only a human can do that).
