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

POST   /api/applications/:id/analyse-cv  fit score + tailored one-page rewrite
POST   /api/applications/:id/find-roles  researches the firm's actual advertised tracks
```

## The AI buttons

Both shell out to the Claude Code CLI (`claude -p … --output-format json`) so they reuse
your existing login rather than needing a separate API key.

**Analyse CV** scores 1–10 for how tailored *that* CV is to *that specific posting* — not
whether it's a good CV in general. If the row has a programme pinned under **Applying
for**, the server fetches that page and scores against its real job description; if the
fetch fails it falls back to the row's notes and says so in the summary. Below **7/10**,
or if the content doesn't already fit one side of **A4**, Claude rewrites it (truthfully —
rephrasing and cutting only, never inventing) and it's rendered to a genuinely one-page A4
PDF via headless Edge/Chrome, tightening the layout and re-rendering until it fits. The
result is saved as `Ayaan.Warraich.<FIRM>.CV.pdf`, and your original upload is always kept
alongside it as `original-<filename>`.

**Find roles** researches the distinct tracks a firm actually advertises (a single Trackr
line is often nine separate postings) and stores them as starred/unstarred pills on the
row.

If the `claude` CLI isn't on your PATH, both buttons return a message telling you to ask
Claude Code in chat instead — the result lands in `data.json` in the same shape either
way, so the page doesn't care which path produced it.
