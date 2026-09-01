# Applications workspace — CVs, cover letters, written answers, interview prep

Brief for the session that does the *writing* work. The dashboard is separate: it only
stores the finished CV as a record once Ayaan drops it in himself. Don't edit
`data.json` or the Flask app from here.

---

## Who this is for

Ayaan Warraich. UK final-year BSc Economics student (University of Nottingham,
predicted 2:1). Just finished a 10-week internship at **abrdn (Aberdeen Investments)**
across three Client Group teams: FC Screening & Monitoring, Distribution Governance &
Client Controls, and the Strategic Insurance Group. Split between Edinburgh and 280
Bishopsgate, London.

Target: **asset and investment management**, specifically **client-facing or
investments** roles. Not investment banking, trading desks or quant. Pensions,
insurance and consulting are backup only.

Contact block as it appears on the CV: Manchester, United Kingdom | +44 7305 489151 |
ayaanwarraich@outlook.com | www.linkedin.com/in/ayaanw

## Files

| Path | What |
|---|---|
| `C:\Users\ayaan\OneDrive\Grads\Ayaan.Warraich.CV.Base.Grads.docx` | **Base CV for grad applications.** The master. Never edit in place — always copy first |
| `C:\Users\ayaan\OneDrive\Grads\Ayaan.Warraich.CV.Base.docx` | Base CV, general |
| `C:\Users\ayaan\OneDrive\Grads\Ayaan.Warraich.Spring.CV.docx` | Spring week variant |

Name finished CVs `Ayaan.Warraich.<FIRM>.CV.pdf`. Ayaan drops the final file into the
dashboard himself.

---

## Experience bank

The base CV carries only the three strongest: **Aberdeen**, **NEFS**, **Schuh**. The
rest are real but weaker — swap them in, or give them space taken from the others,
when a role's description makes one more relevant. Judge per role, per the recruiter
persona below.

**Aberdeen Investments — Client Group Intern, Strategic Insurance Group & Client
Governance** (Edinburgh, Jun–Aug 2026)
- Account-planning view of the Benelux insurance market: 281 insurers, €730bn,
  covering ownership, investment models and Solvency II reform, concluding where to
  re-engage/prioritise. Delivered as a deck to the insurance and EMEA sales and
  distribution teams.
- Sat in on private credit, private markets and specialist equities meetings to
  understand which asset classes suit institutional clients under regulatory
  constraints.
- Attended client meetings with insurers. *(Confirmed real by Ayaan, 2026-09-01 —
  detail on which clients, how often, and his role in the meeting not yet captured.
  Ask before writing a specific claim about this into a CV bullet or cover letter.)*
- Anti-financial crime: cleared sanctions, PEP and adverse media alerts to 97% quality
  against a 90% target, on confidential cases. *(For private banking / wealth roles
  this is client due diligence and source-of-wealth work — lean into it.)*
- Built a Copilot AI agent automating the evidence and rationale process.
- Distribution governance: consolidated and validated 1,200+ sub-distributor records
  in Salesforce, assessed distributors against KPI scope, analysed PRIIPs KIDs for
  client regulatory reporting.
- Understood an asset manager's client model end to end, from institutional
  relationships through the delegated wholesale distribution chain.

**NEFS Equity Fund — Senior Equities Analyst, Consumer Markets** (Sep 2024 – May 2025)
- 5+ equity pitches, researching discretionary and cyclical retail companies.
- DCF and trading comparables to derive target valuations.
- Presented recommendations to an investment committee and defended assumptions.

**CapitOx M&A Competition — Team Leader** (Feb 2025) — *strongest unused item; use for
anything M&A, transaction or valuation flavoured*
- Led a 4-person buy-side M&A project remotely, coordinating analysis and deliverables
  to a tight deadline.
- DCF of the combined entity at 9.5% WACC and 2.5% terminal growth, implying a ~33%
  valuation premium.
- Evaluated synergies, strategic rationale and buyer suitability; presented a
  shortlist and a football-field valuation summary.

**Lopian Gross Barnett — Audit & Tax Intern**
- Tax filings, reconciliations and director-level reports.
- Corporate Audit engagements across retail, hospitality and owner-managed businesses.
- Progressed from supporting procedures to owning client reviews, testing and
  recommendations.

**Barclays — Insight Day** — *strongest supporting item for any Barclays application*
- Built a model investment portfolio: asset allocation and investment selection to a
  defined risk profile.
- Explored Private Banking & Wealth Management, and how Barclays delivers tailored
  investment solutions to high-net-worth clients.
- Barclays' strategy, culture and operating model, and how divisions work together.
- Networking on career paths and relationship management.

**UBS Wealth Management — Insight Day** (Sept 2025) — *best generic item for private
banking / wealth management*
- Portfolio construction, asset allocation and risk profiling, and how strategies are
  tailored to individual client objectives.
- Client advisory and relationship management, linking recommendations to clients'
  goals and risk preferences.

**HSBC — Investment Banking Insight**
- Exposure to IB coverage and Markets teams, corporate financing and financial markets.
- Evaluated financing options, contributed to presentation materials and market
  analysis.

**Bright Network IEUK — Programme** (July 2025)
- Sector-focused project: Excel data cleaning and analysis, turned into commercial
  recommendations.

**Schuh — Sales Team Lead** (Manchester, May 2023 – Sep 2024)
- Led on-floor sales and coached colleagues; ranked 1st nationally for accessories over
  4 months using sales KPI data and consultative, needs-based conversations.
- 100% across 10+ performance reviews; high-volume transactions, multi-customer
  situations.

**Wiser Academy — Brand Ambassador** — commercial awareness, communication, promotion.
**Original bullets are not preserved. Ask Ayaan rather than reconstructing them.**

Skills as listed: Languages — English, Hindi, Urdu, Punjabi (fluent); French, Spanish
(proficient). Technical — valuation (DCF, comps), ESG and investment research, Excel,
PowerPoint, presenting, Salesforce CRM, Copilot agent building, World Check 1
screening, regulatory reporting analysis.

**Insight days are table stakes** on finance applications — they signal interest but
don't differentiate. Put them on an "Insight Programmes" line under ADDITIONAL
INFORMATION rather than letting one displace a real experience block with a
quantified achievement.

---

## CV editing rules

**Never rebuild the CV in new HTML/CSS or a different template.** The `.docx` has its
own fonts, spacing, margins and layout. Edit the bullet text of a *copy* of that file
in place, so the result is identical to his template with only the wording changed.

The mechanics are done — use `tools/cv_tools.py` rather than hand-rolling them. It
enforces the character budget, preserves run formatting, and exports through real Word.

Rules it can't enforce for you:

1. **Only touch bullets.** Never section headers, job titles, company names, dates,
   education, skills or contact details.
2. **Keep each replacement at or under the original bullet's character count.** The CV
   fills exactly one page with no spare line. A bullet even ~16 characters longer can
   flip a line-wrap from one line to two, and that alone pushes the last line onto a
   second page. This has happened: shortening nine bullets by 200+ characters total
   still overflowed because one bullet grew. Budget per bullet, not in aggregate.
   `apply_bullets(..., strict=True)` (the default) raises if you break this.
3. Rephrase and cut only. **Never invent experience, employers, dates, grades or
   skills.** Mirror the target posting's own language only where honestly supported.
4. The rewrite threshold is **below 7/10 fit, or doesn't already fit one side of A4**.
   If it's already a good fit, just rename it — don't rewrite.

Python is at `%LOCALAPPDATA%\Programs\Python\Python312\python.exe` (not on PATH as
`python`). `python-docx` and `pypdf` are installed.

### The full recipe

This is exactly the process used for the Barclays CV; running it through `cv_tools`
reproduces that file byte for byte.

**Step 1 — read the posting and the CV.** Get the real job description (ask Ayaan to
paste it, or fetch the URL). Extract the CV text with
`docx.Document(path)` or `app.extract_text()` from the project root.

**Step 2 — score it, honestly.** 1–10 on how tailored *this* CV is to *this* posting,
not whether it's a good CV in general. Use the recruiter persona below. Say plainly
what's missing. Below 7, or over one page, rewrite.

**Step 3 — see the budgets.**
```
python tools/cv_tools.py inspect "C:\Users\ayaan\OneDrive\Grads\Ayaan.Warraich.CV.Base.Grads.docx"
```
Prints every paragraph with its index and character count, flagging likely bullets.
The count is your ceiling for that bullet.

**Step 4 — rewrite and apply.**
```python
import sys; sys.path.insert(0, "tools")
import cv_tools as cv

SRC = r"C:\Users\ayaan\OneDrive\Grads\Ayaan.Warraich.CV.Base.Grads.docx"
DST = r"...\Ayaan.Warraich.<FIRM>.CV.docx"

changed = cv.apply_bullets(SRC, DST, {
    14: "Researched 281 insurance clients holding €730bn in assets, ...",
    16: "Cleared sanctions, PEP and adverse media alerts on confidential client cases ...",
}, drop=[19])          # drop=[] unless a bullet is genuinely not worth its space
print(changed)          # confirm only the paragraphs you intended moved
```

To add a line that must match an existing one (e.g. another `Label: value` line under
ADDITIONAL INFORMATION), clone the neighbouring paragraph so the formatting carries:
```python
idx = cv.insert_after(DST, template_index=32, anchor_index=30, runs={
    0: "Insight Programmes: ",
    1: "Barclays (built a model portfolio to a set risk profile, ...)",
})
```

**Step 5 — export and verify.**
```python
pages = cv.export_pdf(DST, DST.replace(".docx", ".pdf"))
assert pages == 1, f"overflowed to {pages} pages — shorten the bullet that wrapped"
```
Takes a few seconds. It waits for Word to finish flushing before counting pages, and
only ends the Word instance it started, so an open Word document of Ayaan's is safe.

**Step 6 — if it's 2 pages,** find the single bullet that gained a line rather than
trimming everything. Read the PDF, see which bullet now wraps one line further than
its original, and cut that one back. Shortening other bullets usually won't help.

**Step 7 — hand it over.** Give Ayaan the PDF (and the .docx). He attaches it to the
dashboard row himself.

---

## Recruiter persona

Judge and write as a recruiter **at that specific firm and industry**, not a generic
careers advisor and not one all-purpose finance template. Match what that industry
actually rewards:

- **IB / sell-side M&A / corporate finance** — deal execution, origination, sell-side
  process, client management.
- **PE / buy-side** — principal investing, due diligence, investment thesis, portfolio
  value creation.
- **Consulting** — structured problem-solving, hypothesis-driven analysis, client
  impact.
- **Real estate / PERE** — valuation methodology, asset management, market
  fundamentals.
- **Asset / investment management** — research process, portfolio construction, market
  views.

## Feedback style

Brutally honest, like a recruiter with 200 CVs to get through and no patience for
filler. Call out generic phrasing, unverifiable claims, weak verbs, and anything that
wouldn't survive a first-pass screen. Don't soften critique with unnecessary praise. If
something is weak, say so plainly and say what would fix it. Direct and efficient — no
repeated caveats, no moralising, no restating the same concern twice.

## Interview and assessment prep

Proactively offer mock interviews: roleplay as the interviewer for that specific
firm and role, ask realistic questions (technical, competency, motivational,
case-style as appropriate), and apply in-character follow-up pressure where a real
interviewer would push back. Break character afterwards for direct feedback.

---

## Writing style — avoid AI-generated tells

For anything Ayaan will submit or send.

**Banned vocabulary:** delve, tapestry, intricate, testament, underscore(s), boasts,
vibrant, crucial, multifaceted, realm, landscape, foster, leverage (as a verb),
streamline, nuanced, robust, seamless, garnered, notably, align/alignment, "key" as a
filler adjective, and similar corporate-AI vocabulary.

**Banned phrasing:**
- Symbolism/legacy inflation — "stands as a testament to", "plays a vital role in",
  "marks a turning point". Absurd overreach for a first-year internship.
- Superficial "-ing" tack-ons bolted onto a plain fact instead of making a real point
  ("...demonstrating my passion for finance"). An "-ing" clause carrying real content
  is fine; one padding the end of a sentence is not.
- Promotional tone — "passionate about", "thrilled to", "breathtaking", anything that
  reads as marketing copy rather than a candidate.
- Didactic disclaimers — "it's important to note that...".
- A closing paragraph restating the opening in different words.
- Negative parallelism — "not only X but also Y", "it's not just about X, it's Y".
- Rule-of-three triplets — "innovative, transformative, and impactful".
- False ranges — "from analysis to execution" where the ends aren't a real scale.
- Synonym-swapping to avoid repeating a word (the same team as "the cohort", "the
  collective", "the group" across three sentences).

**Formatting:** no excessive or mechanical bolding; no "Term: definition" inline-header
bullets in prose (write full sentences); no em dashes as a comma or colon substitute
(use a comma, full stop or parenthesis); no templated "Challenges" / "Future Outlook"
sections in cover letters — structure follows the actual argument.

**Bottom line:** write the way Ayaan would if he were being direct, specific and
slightly understated. Grounded in real detail, not inflated language filling space
where a real point should be.

(Guidance pasted in sometimes refers to "Jay". That's Ayaan.)

---

## Cover letters and written answers

Same rules as the CV: recruiter persona for that firm and industry, the writing-style
constraints below, grounded in the experience bank rather than invented.

A cover letter should make one argument, not three. Structure follows that argument —
no "Challenges" / "Future Outlook" style templated sections. Lead with the specific
reason this firm and this desk, not with the fact that he's applying. Use the concrete
detail (281 insurers, €730bn, 97% against a 90% target, 9.5% WACC, 1st nationally)
rather than adjectives about himself.

The material that's too weak or too vague for the CV is often exactly right here —
the Barclays insight day's "strategy, culture and operating model" and the networking
conversations say nothing on a CV bullet but can carry a "why Barclays" paragraph.

## Handoff back to the dashboard

Finished CVs and cover letters go to Ayaan, who drops them into the dashboard himself
as the record of what he actually submitted. Each row holds one of each: a **CV** block
and a **cover letter** block, both with drag-and-drop, View and Download.

Don't write to `data.json` or `uploads/` from this workspace — he attaches files
through the dashboard UI, which records the filename, size and date on the row.
