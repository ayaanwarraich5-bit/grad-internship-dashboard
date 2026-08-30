# Grad &amp; Internship Dashboard

A local dashboard for tracking 2026/27 asset-management graduate schemes and summer
internships. Replaces the published Claude Artifact — this version writes real files to
disk and has exactly one source of truth, so nothing gets silently overwritten.

## Run it

```bash
python app.py
```

Then open **http://127.0.0.1:5173**. Set `PORT` to use a different port.

First time only:

```bash
pip install -r requirements.txt
```

## What's where

| path | what it is |
|---|---|
| `data.json` | every application, one object per line. The single source of truth. |
| `uploads/<id>/` | real CV files. Nothing is base64'd into JSON. |
| `app.py` | Flask server: REST API, CV upload/download, the two AI endpoints. |
| `static/` | `index.html`, `styles.css`, `app.js`. No build step. |
| `CLAUDE.md` | job-search strategy and maintenance rules, loaded by Claude Code. |

## Two ways to edit, at once

Click around in the browser, **or** tell Claude Code in chat ("check Trackr and update
anything that's changed"). Claude Code edits `data.json` directly; the open page polls
every 3 seconds and re-renders when it sees a change — no manual refresh. Polling pauses
while a field is focused, so it never yanks text out from under you mid-edit.

## API

```
GET    /api/applications
POST   /api/applications
PATCH  /api/applications/:id
DELETE /api/applications/:id

POST   /api/applications/:id/cv          multipart upload, max 15MB, .pdf/.doc/.docx
GET    /api/applications/:id/cv          downloads the attached file
DELETE /api/applications/:id/cv
```

## CV analysis and role research — done in chat, no buttons

There's no `/analyse-cv` or `/find-roles` endpoint. Both existed once as buttons that
shelled out to a locally-installed Claude CLI, but that CLI only ever existed inside the
dev environment Claude Code runs commands in — never on the machine actually running the
browser — so neither button could really work there, and both were removed.

**CV analysis**: drag a CV onto a grad/internship row, then just ask Claude Code in chat
— *"analyse the CV on the Redburn row"*. It reads the file directly (no subprocess, no
login needed), scores 1–10 for how tailored *that* CV is to *that specific posting* — not
whether it's a good CV in general. If the row has a programme pinned under **Applying
for**, it fetches that page and scores against the real job description; otherwise it
falls back to the row's notes and says so in the summary. Below **7/10**, or if the
content doesn't already fit one side of **A4**, it gets rewritten (truthfully — rephrasing
and cutting only, never inventing) and rendered to a genuinely one-page A4 PDF via
headless Edge/Chrome, tightening the layout and re-rendering until it fits. The result is
saved as `Ayaan.Warraich.<FIRM>.CV.pdf` and shown under **CV used for this application**
on the row; your original upload is always kept alongside it as `original-<filename>`.

**Role research**: ask Claude Code — *"find the specific roles at Schroders"*. It browses
the firm's actual careers site (a single Trackr line is often nine separate postings),
judges each track against the strategy in `CLAUDE.md`, and writes them as starred/
unstarred pills on the row.

Either way, the result lands in `data.json` and the score badge, summary, or pills appear
on the page within a few seconds — no refresh needed.
