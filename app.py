"""Grad and Internship Dashboard — local Flask server.

One authoritative file on disk (data.json) that both the browser and Claude Code
read and write directly. Real CV files live in uploads/<id>/, never base64 in JSON.

Run:  python app.py   ->  http://127.0.0.1:5173
"""

import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.request
from datetime import datetime, timezone

from flask import Flask, jsonify, request, send_file, send_from_directory
from werkzeug.utils import secure_filename

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(ROOT, "data.json")
UPLOADS = os.path.join(ROOT, "uploads")
PORT = int(os.environ.get("PORT", "5173"))

MAX_UPLOAD_BYTES = 15 * 1024 * 1024
ALLOWED_EXT = {".pdf", ".doc", ".docx"}

EDITABLE_FIELDS = {
    "company", "role", "sector", "stage", "status", "deadlineLabel", "dateISO",
    "sourceUrl", "notes", "cv", "cvAnalysis", "subRoles", "selectedProgramme",
}
VALID_STAGES = {"watchlist", "applied", "testing", "interview", "final",
                "awaiting", "offer", "rejected"}
VALID_STATUSES = {"open", "not_yet_open", "unknown"}
VALID_TYPES = {"personal", "grad", "intern", "backup"}

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES + (1024 * 1024)

_lock = threading.Lock()


# ---------------------------------------------------------------- data store

def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_data(rows):
    """Write one object per line, then atomically replace.

    The one-per-line shape is deliberate: it keeps chat-driven edits and diffs
    readable, and matches how the seed file was authored.
    """
    lines = ["["]
    for i, row in enumerate(rows):
        comma = "," if i < len(rows) - 1 else ""
        lines.append(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + comma)
    lines.append("]")
    body = "\n".join(lines) + "\n"

    fd, tmp = tempfile.mkstemp(dir=ROOT, prefix=".data-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(body)
        os.replace(tmp, DATA_FILE)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def find_row(rows, app_id):
    for row in rows:
        if row.get("id") == app_id:
            return row
    return None


def next_id(rows, app_type):
    prefix = {"grad": "g", "intern": "i", "backup": "b", "personal": "p"}[app_type]
    used = set()
    for row in rows:
        m = re.fullmatch(re.escape(prefix) + r"(\d+)", str(row.get("id", "")))
        if m:
            used.add(int(m.group(1)))
    n = 1
    while n in used:
        n += 1
    return f"{prefix}{n}"


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def row_dir(app_id):
    return os.path.join(UPLOADS, secure_filename(app_id))


def purge_row_dir(app_id):
    """Delete a row's uploads. OneDrive can hold the folder handle briefly, so if the
    directory itself won't go, make sure the documents inside are gone regardless."""
    directory = row_dir(app_id)
    if not os.path.isdir(directory):
        return
    shutil.rmtree(directory, ignore_errors=True)
    if not os.path.isdir(directory):
        return
    for leftover in os.listdir(directory):
        try:
            os.unlink(os.path.join(directory, leftover))
        except OSError:
            pass
    try:
        os.rmdir(directory)
    except OSError:
        pass  # an empty directory left behind is harmless


def firm_slug(company):
    """'Goldman Sachs Asset Management (GSAM)' -> 'GoldmanSachsAssetManagement'."""
    cleaned = re.sub(r"\([^)]*\)", " ", company or "")
    cleaned = re.sub(r"[^A-Za-z0-9 ]+", " ", cleaned)
    parts = [p for p in cleaned.split() if p]
    return "".join(p[:1].upper() + p[1:] for p in parts) or "Firm"


# ------------------------------------------------------------------ REST API

@app.get("/api/applications")
def api_list():
    with _lock:
        return jsonify(load_data())


@app.post("/api/applications")
def api_create():
    payload = request.get_json(force=True, silent=True) or {}
    app_type = payload.get("type")
    if app_type not in VALID_TYPES or app_type == "personal":
        return jsonify({"error": "type must be grad, intern or backup"}), 400
    if not (payload.get("company") or "").strip():
        return jsonify({"error": "company is required"}), 400

    with _lock:
        rows = load_data()
        row = {
            "id": next_id(rows, app_type),
            "type": app_type,
            "company": payload.get("company", "").strip(),
            "role": payload.get("role", "").strip(),
            "sector": payload.get("sector", "").strip(),
            "stage": "watchlist",
            "status": "unknown",
            "deadlineLabel": payload.get("deadlineLabel", "").strip() or "See Trackr",
            "dateISO": payload.get("dateISO") or None,
            "sourceUrl": payload.get("sourceUrl", "").strip(),
            "notes": payload.get("notes", "").strip(),
        }
        rows.append(row)
        save_data(rows)
    return jsonify(row), 201


@app.patch("/api/applications/<app_id>")
def api_update(app_id):
    payload = request.get_json(force=True, silent=True) or {}
    with _lock:
        rows = load_data()
        row = find_row(rows, app_id)
        if row is None:
            return jsonify({"error": "not found"}), 404

        for key, value in payload.items():
            if key not in EDITABLE_FIELDS:
                continue
            if key == "stage" and value not in VALID_STAGES:
                return jsonify({"error": f"invalid stage: {value}"}), 400
            if key == "status":
                if row.get("type") == "personal":
                    continue
                if value not in VALID_STATUSES:
                    return jsonify({"error": f"invalid status: {value}"}), 400
            if key == "selectedProgramme" and value in (None, {}, ""):
                row.pop("selectedProgramme", None)
                continue
            row[key] = value
        save_data(rows)
    return jsonify(row)


@app.delete("/api/applications/<app_id>")
def api_delete(app_id):
    with _lock:
        rows = load_data()
        row = find_row(rows, app_id)
        if row is None:
            return jsonify({"error": "not found"}), 404
        if row.get("type") == "personal":
            return jsonify({"error": "the in-progress row cannot be deleted"}), 400
        rows = [r for r in rows if r.get("id") != app_id]
        save_data(rows)
    purge_row_dir(app_id)
    return jsonify({"ok": True})


# ------------------------------------------------------------------ CV files

@app.post("/api/applications/<app_id>/cv")
def cv_upload(app_id):
    with _lock:
        rows = load_data()
        row = find_row(rows, app_id)
    if row is None:
        return jsonify({"error": "not found"}), 404
    if row.get("type") == "personal":
        return jsonify({"error": "no CV on the in-progress row"}), 400

    upload = request.files.get("file")
    if upload is None or not upload.filename:
        return jsonify({"error": "no file supplied"}), 400

    filename = secure_filename(upload.filename)
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXT:
        return jsonify({"error": "only .pdf, .doc and .docx are accepted"}), 400

    blob = upload.read()
    if len(blob) > MAX_UPLOAD_BYTES:
        return jsonify({"error": "file is larger than 15MB"}), 400

    target_dir = row_dir(app_id)
    # Clear any previously attached file, but never touch a kept original.
    if os.path.isdir(target_dir):
        for existing in os.listdir(target_dir):
            if not existing.startswith("original-"):
                try:
                    os.unlink(os.path.join(target_dir, existing))
                except OSError:
                    pass
    os.makedirs(target_dir, exist_ok=True)
    with open(os.path.join(target_dir, filename), "wb") as fh:
        fh.write(blob)

    with _lock:
        rows = load_data()
        row = find_row(rows, app_id)
        if row is None:
            return jsonify({"error": "not found"}), 404
        row["cvFile"] = {
            "filename": filename,
            "size": len(blob),
            "uploadedAt": now_iso(),
        }
        row.pop("cvAnalysis", None)
        save_data(rows)
    return jsonify(row)


@app.get("/api/applications/<app_id>/cv")
def cv_download(app_id):
    with _lock:
        row = find_row(load_data(), app_id)
    if row is None or not row.get("cvFile"):
        return jsonify({"error": "no CV attached"}), 404
    filename = row["cvFile"]["filename"]
    path = os.path.join(row_dir(app_id), filename)
    if not os.path.isfile(path):
        return jsonify({"error": "file missing on disk"}), 404
    return send_file(path, as_attachment=True, download_name=filename)


@app.delete("/api/applications/<app_id>/cv")
def cv_remove(app_id):
    with _lock:
        rows = load_data()
        row = find_row(rows, app_id)
        if row is None:
            return jsonify({"error": "not found"}), 404
        filename = (row.get("cvFile") or {}).get("filename")
        row.pop("cvFile", None)
        row.pop("cvAnalysis", None)
        save_data(rows)
    if filename:
        try:
            os.unlink(os.path.join(row_dir(app_id), filename))
        except OSError:
            pass
    return jsonify(row)


# ------------------------------------------------------- text extraction etc.

def extract_text(path):
    """Plain text from a PDF or DOCX. Returns (text, error_message)."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            return None, "pypdf is not installed — run: pip install -r requirements.txt"
        try:
            reader = PdfReader(path)
            return "\n".join((p.extract_text() or "") for p in reader.pages).strip(), None
        except Exception as exc:
            return None, f"could not read the PDF: {exc}"
    if ext == ".docx":
        try:
            import docx
        except ImportError:
            return None, "python-docx is not installed — run: pip install -r requirements.txt"
        try:
            document = docx.Document(path)
            return "\n".join(p.text for p in document.paragraphs).strip(), None
        except Exception as exc:
            return None, f"could not read the DOCX: {exc}"
    if ext == ".doc":
        return None, ("legacy .doc can't be read directly — re-save the CV as PDF or "
                      "DOCX and re-attach it")
    return None, f"unsupported file type: {ext}"


def pdf_page_count(path):
    try:
        from pypdf import PdfReader
        return len(PdfReader(path).pages)
    except Exception:
        return None


_TAG_STRIP = re.compile(r"(?is)<(script|style|nav|header|footer|svg|noscript)[^>]*>.*?</\1>")


def fetch_posting_text(url, limit=9000):
    """Visible text of a job posting. Returns (text, error_message)."""
    if not url:
        return None, "no URL"
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) grad-dashboard/1.0",
            "Accept": "text/html,application/xhtml+xml",
        })
        with urllib.request.urlopen(req, timeout=25) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            html = resp.read(2_000_000).decode(charset, errors="replace")
    except Exception as exc:
        return None, str(exc)

    html = _TAG_STRIP.sub(" ", html)
    html = re.sub(r"(?is)<(br|/p|/div|/li|/tr|/h[1-6])[^>]*>", "\n", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    for entity, char in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"),
                         ("&gt;", ">"), ("&#39;", "'"), ("&quot;", '"')):
        text = text.replace(entity, char)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n\s*", "\n\n", text).strip()

    if len(text) < 250:
        return None, "the page returned almost no readable text (likely JS-only or gated)"
    return text[:limit], None


# ------------------------------------------------------------- Claude CLI

def find_claude_cli():
    for name in ("claude", "claude.cmd", "claude.exe"):
        found = shutil.which(name)
        if found:
            return found
    candidates = [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\claude\claude.exe"),
        os.path.expandvars(r"%APPDATA%\npm\claude.cmd"),
        os.path.expanduser("~/.local/bin/claude"),
        os.path.expanduser("~/.claude/local/claude"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    # The Windows Claude desktop app ships its own versioned Claude Code CLI here,
    # e.g. %APPDATA%\Claude\claude-code\2.1.247\claude.exe, and never puts it on PATH.
    versioned_root = os.path.expandvars(r"%APPDATA%\Claude\claude-code")
    if os.path.isdir(versioned_root):
        versions = sorted(os.listdir(versioned_root), reverse=True)
        for version in versions:
            for exe_name in ("claude.exe", "claude.cmd", "claude"):
                path = os.path.join(versioned_root, version, exe_name)
                if os.path.isfile(path):
                    return path
    return None


CLI_MISSING = ("The Claude Code CLI isn't on PATH, so this button can't run the analysis "
               "itself. Ask Claude Code in chat instead — e.g. \"analyse the CV on the "
               "{company} row\" — and it will write the result straight into data.json; "
               "this page will pick it up within a few seconds.")


def run_claude(prompt, timeout=300):
    """Run the Claude Code CLI headless. Returns (parsed_json, error_message)."""
    cli = find_claude_cli()
    if not cli:
        return None, "CLI_MISSING"
    try:
        proc = subprocess.run(
            [cli, "-p", prompt, "--output-format", "json"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout, cwd=ROOT,
        )
    except subprocess.TimeoutExpired:
        return None, "the Claude CLI timed out"
    except Exception as exc:
        return None, f"could not run the Claude CLI: {exc}"

    raw = proc.stdout.strip()
    envelope = None
    if raw:
        try:
            envelope = json.loads(raw)
        except json.JSONDecodeError:
            envelope = None

    if proc.returncode != 0:
        # The CLI still writes a JSON envelope on most failures (bad login, no
        # credit, etc.) - its "result" field is the human-readable reason.
        reason = envelope.get("result") if isinstance(envelope, dict) else None
        if isinstance(reason, str) and "not logged in" in reason.lower():
            return None, ('The Claude CLI at "{}" isn\'t logged in. Open it directly in '
                          'a terminal (not through chat) and run /login, then try again.'
                          ).format(cli)
        message = reason or (proc.stderr or proc.stdout or "the Claude CLI failed").strip()
        return None, str(message)[:500]

    text = envelope.get("result", raw) if isinstance(envelope, dict) else raw
    parsed = extract_json_object(text)
    if parsed is None:
        return None, "Claude's reply wasn't valid JSON"
    return parsed, None


def extract_json_object(text):
    """Pull the first balanced {...} out of a possibly fenced reply."""
    if not text:
        return None
    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    if fence:
        text = fence.group(1)
    start = text.find("{")
    if start == -1:
        return None
    depth, in_string, escape = 0, False, False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    return None
    return None


STRATEGY = """Ayaan Warraich is a UK final-year BSc Economics student (University of
Nottingham) who has just completed a 10-week summer internship at abrdn (Aberdeen
Investments), rotating across three Client Group teams: FC Screening & Monitoring,
Distribution Governance & Client Controls, and the Strategic Insurance Group.

He targets asset management and investment management, specifically CLIENT-FACING or
INVESTMENTS roles. He is NOT applying to top investment banks, trading desks or quant
roles. Pensions, insurance and consulting are backup only. He would rather apply to
fewer roles he genuinely wants than maximise volume."""


# ------------------------------------------------------------- PDF rendering

def find_browser():
    for path in (
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ):
        if os.path.isfile(path):
            return path
    for name in ("msedge", "chrome", "google-chrome", "chromium"):
        found = shutil.which(name)
        if found:
            return found
    return None


CV_PAGE_CSS = """
@page {{ size: A4; margin: {margin}mm; }}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; }}
body {{
  font-family: "Public Sans", "Segoe UI", Arial, sans-serif;
  font-size: {font}pt; line-height: {line}; color: #111;
}}
h1 {{ font-size: {h1}pt; margin: 0 0 1mm; letter-spacing: .2px; }}
h2 {{
  font-size: {h2}pt; margin: {gap}mm 0 1.2mm; text-transform: uppercase;
  letter-spacing: .8px; border-bottom: .6pt solid #999; padding-bottom: .8mm;
}}
h3 {{ font-size: {font}pt; margin: {gap2}mm 0 .4mm; }}
p {{ margin: 0 0 .8mm; }}
ul {{ margin: .4mm 0 1mm; padding-left: 4.5mm; }}
li {{ margin: 0 0 .5mm; }}
.contact {{ font-size: {small}pt; color: #333; margin: 0 0 1mm; }}
.meta {{ font-size: {small}pt; color: #444; font-style: italic; }}
"""


def render_cv_pdf(body_html, out_path):
    """HTML+CSS -> single-page A4 PDF, tightening until it fits. Returns error or None."""
    browser = find_browser()
    if not browser:
        return "no headless browser (Edge or Chrome) found to render the PDF"

    # Each attempt is progressively tighter: margin, base font, line-height, section gaps.
    attempts = [
        dict(margin=12, font=10.0, line=1.30, h1=17, h2=10.5, small=8.6, gap=3.4, gap2=1.6),
        dict(margin=10, font=9.4, line=1.22, h1=15.5, h2=10.0, small=8.2, gap=2.6, gap2=1.2),
        dict(margin=9, font=8.8, line=1.15, h1=14.5, h2=9.4, small=7.8, gap=2.0, gap2=0.9),
        dict(margin=8, font=8.3, line=1.10, h1=13.5, h2=9.0, small=7.4, gap=1.6, gap2=0.7),
    ]
    workdir = tempfile.mkdtemp(prefix="cvpdf-")
    last_error = "could not render the PDF"
    try:
        for spec in attempts:
            html_path = os.path.join(workdir, "cv.html")
            pdf_path = os.path.join(workdir, "cv.pdf")
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)
            with open(html_path, "w", encoding="utf-8") as fh:
                fh.write("<!doctype html><html><head><meta charset='utf-8'><style>"
                         + CV_PAGE_CSS.format(**spec)
                         + "</style></head><body>" + body_html + "</body></html>")
            try:
                subprocess.run(
                    [browser, "--headless=new", "--disable-gpu", "--no-sandbox",
                     "--no-pdf-header-footer", "--run-all-compositor-stages-before-draw",
                     "--virtual-time-budget=4000",
                     f"--print-to-pdf={pdf_path}",
                     "file:///" + html_path.replace("\\", "/")],
                    capture_output=True, timeout=90,
                )
            except Exception as exc:
                last_error = f"the headless browser failed: {exc}"
                continue
            if not os.path.isfile(pdf_path):
                last_error = "the headless browser produced no PDF"
                continue
            pages = pdf_page_count(pdf_path)
            if pages is None or pages <= 1:
                shutil.copyfile(pdf_path, out_path)
                return None
            last_error = f"the rewritten CV still ran to {pages} pages"
        return last_error
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


# --------------------------------------------------------- AI: find roles
#
# CV analysis has no HTTP route: the button that used to call one shelled out to a
# local Claude CLI that only ever worked from inside this dev environment, never from
# the browser on the user's own machine, so it was removed. The fix is to just ask
# Claude Code in chat ("analyse the CV on the X row") - it reads the file, reasons
# about fit itself with no subprocess call needed, and writes cvAnalysis/cvFile
# straight into data.json. extract_text(), fetch_posting_text() and render_cv_pdf()
# above remain as the reusable pieces for that: read the CV, read the pinned posting,
# and render a verified one-page A4 rewrite the same way this route used to.

@app.post("/api/applications/<app_id>/find-roles")
def find_roles(app_id):
    with _lock:
        row = find_row(load_data(), app_id)
    if row is None:
        return jsonify({"error": "not found"}), 404
    if row.get("type") not in ("grad", "intern"):
        return jsonify({"error": "only grad and internship rows have sub-roles"}), 400

    prompt = f"""{STRATEGY}

Research every distinct early-careers track that {row.get('company')} actually advertises
for the "{row.get('role')}" programme, then judge each one against the strategy above.

Start from Trackr's company page (app.the-trackr.com) and follow through to the firm's
own careers site. Known starting point: {row.get('sourceUrl') or 'search for it'}
Researched notes on this firm: {row.get('notes')}

A single Trackr line often splits into many separate postings once you reach the firm's
own site — Schroders' 2027 internship, for example, covers Client Group, Public Markets
Equities, Public Markets Multi-Asset, Quants, Finance, Marketing, Internal Audit and
Corporate & Regulatory Change as distinct applications. Capture that real breakdown.

Return ONLY a JSON object of the form:
{{"subRoles": [
  {{"name": "...", "highlighted": true, "reason": "why it fits or doesn't, one short phrase",
    "url": "direct link to that specific posting"}}
]}}

Set "highlighted": true only for tracks that are genuinely client-facing or investments
roles worth applying to. Capture each track's OWN direct application URL, not just the
company careers homepage — that link is what pins a row to a real posting later.
If the firm genuinely runs a single undivided programme, return one entry saying so."""

    result, err = run_claude(prompt, timeout=600)
    if err == "CLI_MISSING":
        return jsonify({"error": CLI_MISSING.format(company=row.get("company"))}), 503
    if err:
        return jsonify({"error": err}), 502

    sub_roles = []
    for item in (result.get("subRoles") or []):
        if not isinstance(item, dict) or not item.get("name"):
            continue
        sub_roles.append({
            "name": str(item["name"])[:160],
            "highlighted": bool(item.get("highlighted")),
            "reason": str(item.get("reason") or "")[:240],
            "url": str(item.get("url") or ""),
        })
    if not sub_roles:
        return jsonify({"error": "Claude found no distinct tracks for this firm"}), 502

    with _lock:
        rows = load_data()
        row = find_row(rows, app_id)
        if row is None:
            return jsonify({"error": "not found"}), 404
        row["subRoles"] = sub_roles
        save_data(rows)
    return jsonify(row)


# ---------------------------------------------------------------- static

@app.get("/")
def index():
    return send_from_directory(os.path.join(ROOT, "static"), "index.html")


@app.get("/<path:filename>")
def static_files(filename):
    return send_from_directory(os.path.join(ROOT, "static"), filename)


@app.errorhandler(413)
def too_large(_):
    return jsonify({"error": "file is larger than 15MB"}), 413


if __name__ == "__main__":
    if not os.path.isfile(DATA_FILE):
        sys.exit(f"data.json is missing from {ROOT}")
    os.makedirs(UPLOADS, exist_ok=True)
    print(f"\n  Grad and Internship Dashboard  ->  http://127.0.0.1:{PORT}\n")
    app.run(host="127.0.0.1", port=PORT, debug=False)
