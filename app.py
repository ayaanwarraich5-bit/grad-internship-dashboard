"""Grad and Internship Dashboard — local Flask server.

One authoritative file on disk (data.json) that both the browser and Claude Code
read and write directly. Real CV files live in uploads/<id>/, never base64 in JSON.

Run:  python app.py   ->  http://127.0.0.1:5173
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
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
    "tasks",
}
# Per-row assessment tracking. A task is absent when the application doesn't have one,
# "todo" when it's outstanding, "done" once sat.
VALID_TASKS = {"oa", "hirevue"}
VALID_TASK_STATES = {"todo", "done"}
VALID_STAGES = {"watchlist", "applied", "online_assessment", "hirevue", "interview",
                "assessment_centre", "awaiting", "offer", "rejected"}
# Earlier versions had coarser stages; map them so old data and any stale browser tab
# still work rather than failing validation.
LEGACY_STAGES = {"testing": "online_assessment", "final": "assessment_centre"}
VALID_STATUSES = {"open", "not_yet_open", "unknown"}
VALID_TYPES = {"personal", "grad", "intern", "backup"}

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES + (1024 * 1024)

_lock = threading.Lock()


# ---------------------------------------------------------------- data store

def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as fh:
        rows = json.load(fh)
    for row in rows:
        if row.get("stage") in LEGACY_STAGES:
            row["stage"] = LEGACY_STAGES[row["stage"]]
    return rows


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
        # This project lives in a OneDrive folder, and OneDrive (like AV scanners) takes
        # a brief exclusive lock on data.json while it syncs. That makes os.replace fail
        # with PermissionError often enough to lose a save, so retry before giving up.
        last_error = None
        for delay in (0, 0.05, 0.15, 0.3, 0.6, 1.0):
            if delay:
                time.sleep(delay)
            try:
                os.replace(tmp, DATA_FILE)
                return
            except PermissionError as exc:
                last_error = exc
        raise last_error
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
            if key == "stage":
                value = LEGACY_STAGES.get(value, value)
                if value not in VALID_STAGES:
                    return jsonify({"error": f"invalid stage: {value}"}), 400
            if key == "status":
                if row.get("type") == "personal":
                    continue
                if value not in VALID_STATUSES:
                    return jsonify({"error": f"invalid status: {value}"}), 400
            if key == "selectedProgramme" and value in (None, {}, ""):
                row.pop("selectedProgramme", None)
                continue
            if key == "tasks":
                if value in (None, {}, ""):
                    row.pop("tasks", None)
                    continue
                if not isinstance(value, dict):
                    return jsonify({"error": "tasks must be an object"}), 400
                cleaned = {k: v for k, v in value.items()
                           if k in VALID_TASKS and v in VALID_TASK_STATES}
                if cleaned:
                    row["tasks"] = cleaned
                else:
                    row.pop("tasks", None)
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


# ------------------------------------------------ attached documents (cv, cover)

# Each row can hold one of each kind. Both live flat in uploads/<id>/; the row records
# which filename belongs to which kind.
DOC_KINDS = {"cv": "cvFile", "cover": "coverFile"}
DOC_LABELS = {"cv": "CV", "cover": "cover letter"}


def other_kind_filenames(row, kind):
    """Filenames belonging to the row's OTHER document kinds — never delete these."""
    return {(row.get(field) or {}).get("filename")
            for k, field in DOC_KINDS.items() if k != kind} - {None}


@app.post("/api/applications/<app_id>/docs/<kind>")
def doc_upload(app_id, kind):
    field = DOC_KINDS.get(kind)
    if field is None:
        return jsonify({"error": f"unknown document type: {kind}"}), 404

    with _lock:
        row = find_row(load_data(), app_id)
    if row is None:
        return jsonify({"error": "not found"}), 404
    if row.get("type") == "personal":
        return jsonify({"error": f"no {DOC_LABELS[kind]} on the in-progress row"}), 400

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
    os.makedirs(target_dir, exist_ok=True)

    # Replace only the file this kind was previously pointing at. Deleting anything
    # else would take out the row's other document (or a kept original) with it.
    previous = (row.get(field) or {}).get("filename")
    if previous and previous != filename and previous not in other_kind_filenames(row, kind):
        try:
            os.unlink(os.path.join(target_dir, previous))
        except OSError:
            pass

    with open(os.path.join(target_dir, filename), "wb") as fh:
        fh.write(blob)

    with _lock:
        rows = load_data()
        row = find_row(rows, app_id)
        if row is None:
            return jsonify({"error": "not found"}), 404
        row[field] = {"filename": filename, "size": len(blob), "uploadedAt": now_iso()}
        if kind == "cv":
            row.pop("cvAnalysis", None)   # a new CV invalidates the old scoring
        save_data(rows)
    return jsonify(row)


@app.get("/api/applications/<app_id>/docs/<kind>")
def doc_download(app_id, kind):
    field = DOC_KINDS.get(kind)
    if field is None:
        return jsonify({"error": f"unknown document type: {kind}"}), 404

    with _lock:
        row = find_row(load_data(), app_id)
    if row is None or not row.get(field):
        return jsonify({"error": f"no {DOC_LABELS[kind]} attached"}), 404
    filename = row[field]["filename"]
    path = os.path.join(row_dir(app_id), filename)
    if not os.path.isfile(path):
        return jsonify({"error": "file missing on disk"}), 404
    # ?inline=1 lets the browser render the PDF in a tab instead of forcing a save,
    # which is what you want when reviewing rather than filing it.
    inline = request.args.get("inline") == "1"
    return send_file(path, as_attachment=not inline, download_name=filename)


@app.delete("/api/applications/<app_id>/docs/<kind>")
def doc_remove(app_id, kind):
    field = DOC_KINDS.get(kind)
    if field is None:
        return jsonify({"error": f"unknown document type: {kind}"}), 404

    with _lock:
        rows = load_data()
        row = find_row(rows, app_id)
        if row is None:
            return jsonify({"error": "not found"}), 404
        filename = (row.get(field) or {}).get("filename")
        keep = other_kind_filenames(row, kind)
        row.pop(field, None)
        if kind == "cv":
            row.pop("cvAnalysis", None)
        save_data(rows)
    if filename and filename not in keep:
        try:
            os.unlink(os.path.join(row_dir(app_id), filename))
        except OSError:
            pass
    return jsonify(row)


# Older paths, kept so a browser tab left open on the previous build still works.
@app.post("/api/applications/<app_id>/cv")
def cv_upload_legacy(app_id):
    return doc_upload(app_id, "cv")


@app.get("/api/applications/<app_id>/cv")
def cv_download_legacy(app_id):
    return doc_download(app_id, "cv")


@app.delete("/api/applications/<app_id>/cv")
def cv_remove_legacy(app_id):
    return doc_remove(app_id, "cv")


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


# ------------------------------------------------------------- PDF rendering
#
# There's no local Claude CLI invocation left in this file. It shelled out to a copy
# of `claude` that only ever existed inside the dev environment Claude Code's own
# tools run commands in, never on the machine actually running this Flask server, so
# every button built on it (Analyse CV, Find roles) could never really work from the
# browser. Both are now done directly through chat instead - ask Claude Code, e.g.
# "analyse the CV on the X row" or "find the specific roles at X" - which reads/writes
# files and data.json directly, with no subprocess call needed. extract_text(),
# fetch_posting_text(), and render_cv_pdf() below remain as reusable pieces for that.

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
