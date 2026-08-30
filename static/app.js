/* Grad & Internship Dashboard — talks to the local Flask API.
   One source of truth on disk: data.json. The page polls it so edits Claude Code
   makes from chat show up here without a refresh. */

const STAGES = [
  ['watchlist',         'Watchlist',         'neutral'],
  ['applied',           'Applied',           'active'],
  ['online_assessment', 'Online Assessment', 'active'],
  ['hirevue',           'HireVue',           'active'],
  ['interview',         'Interview',         'active'],
  ['assessment_centre', 'Assessment Centre', 'active'],
  ['awaiting',          'Awaiting',          'awaiting'],
  ['offer',             'Offer',             'offer'],
  ['rejected',          'Rejected',          'rejected'],
];
const STAGE_GROUP = Object.fromEntries(STAGES.map(([k, , g]) => [k, g]));
const STAGE_LABEL = Object.fromEntries(STAGES.map(([k, l]) => [k, l]));

const STATUS = {
  open:         { label: 'Open',        group: 'offer',    glyph: '●' },
  not_yet_open: { label: 'Not open',    group: 'neutral',  glyph: '○' },
  unknown:      { label: 'Unconfirmed', group: 'awaiting', glyph: '?' },
};

const SECTIONS = [
  { type: 'personal', title: 'In progress', addable: false },
  { type: 'grad',     title: 'Graduate schemes — independent & best-fit managers', addable: true },
  { type: 'intern',   title: 'Summer internships — BB private banks & elite-boutique AM arms', addable: true },
  { type: 'backup',   title: 'Backup — pensions, insurance & consulting', addable: true },
];

const TYPE_FILTERS = [['all', 'All'], ['grad', 'Grad schemes'], ['intern', 'Internships'], ['backup', 'Backup']];
const STATUS_FILTERS = [['any', 'Any'], ['open', 'Open now'], ['not_yet_open', 'Not open yet'], ['unknown', 'Unconfirmed']];

let rows = [];
let serialised = '';
let inFlight = 0;              // writes we've sent but not yet seen echoed back
const openPins = new Set();    // rows whose "applying for" picker is expanded
const armedDeletes = new Set();

const $ = (sel) => document.querySelector(sel);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

/* ── preferences ──────────────────────────────────────────────────────── */
const pref = {
  get(key, fallback) { try { return localStorage.getItem(key) ?? fallback; } catch { return fallback; } },
  set(key, value) { try { localStorage.setItem(key, value); } catch { /* private mode */ } },
};
let fType = pref.get('gd.filter.type', 'all');
let fStatus = pref.get('gd.filter.status', 'any');
let query = '';   // search text — transient, deliberately not persisted

/* ── theme ────────────────────────────────────────────────────────────── */
function applyTheme(mode) {
  const root = document.documentElement;
  if (mode === 'system') root.removeAttribute('data-theme');
  else root.setAttribute('data-theme', mode);
  $('#theme-glyph').textContent = mode === 'dark' ? '☾' : mode === 'light' ? '☀' : '◐';
  $('#theme-label').textContent = mode === 'dark' ? 'Dark' : mode === 'light' ? 'Light' : 'Auto';
}
let theme = pref.get('gd.theme', 'system');
applyTheme(theme);
$('#theme').addEventListener('click', () => {
  theme = { system: 'light', light: 'dark', dark: 'system' }[theme];
  pref.set('gd.theme', theme);
  applyTheme(theme);
});

/* ── toast + saved flag ───────────────────────────────────────────────── */
let toastTimer;
function toast(message, bad = false) {
  const el = $('#toast');
  el.textContent = message;
  el.classList.toggle('bad', bad);
  el.classList.add('on');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('on'), bad ? 6500 : 2200);
}
let savedTimer;
function flashSaved() {
  const el = $('#saved');
  el.classList.add('on');
  clearTimeout(savedTimer);
  savedTimer = setTimeout(() => el.classList.remove('on'), 1300);
}

/* ── API ──────────────────────────────────────────────────────────────── */
async function api(path, options = {}) {
  const res = await fetch(path, options);
  let body = null;
  try { body = await res.json(); } catch { /* empty body */ }
  if (!res.ok) throw new Error((body && body.error) || `${res.status} ${res.statusText}`);
  return body;
}

function mergeRow(updated) {
  const i = rows.findIndex((r) => r.id === updated.id);
  if (i >= 0) rows[i] = updated; else rows.push(updated);
  serialised = JSON.stringify(rows);
}

async function patch(id, changes) {
  inFlight += 1;
  try {
    mergeRow(await api(`/api/applications/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(changes),
    }));
    flashSaved();
  } catch (err) {
    toast(`Couldn't save: ${err.message}`, true);
  } finally {
    inFlight -= 1;
  }
}

/* ── dates ────────────────────────────────────────────────────────────── */
const DAY = 86400000;
function daysUntil(iso) {
  const then = new Date(iso + 'T00:00:00');
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.round((then - today) / DAY);
}
function formatDate(iso) {
  return new Date(iso + 'T00:00:00').toLocaleDateString('en-GB',
    { day: 'numeric', month: 'short', year: 'numeric' });
}
function countdown(days) {
  if (days < 0) return `closed ${-days}d ago`;
  if (days === 0) return 'closes today';
  if (days === 1) return '1 day left';
  return `${days} days left`;
}
function formatBytes(n) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

/* ── header widgets ───────────────────────────────────────────────────── */
function renderStats() {
  const activeCount = rows.filter((r) => STAGE_GROUP[r.stage] === 'active').length;
  const tiles = [
    ['Tracked total', rows.length, ''],
    ['Open right now', rows.filter((r) => r.status === 'open').length, 'is-open'],
    ['Not started', rows.filter((r) => r.stage === 'watchlist').length, ''],
    ['In motion', activeCount, 'is-motion'],
    ['Awaiting outcome', rows.filter((r) => r.stage === 'awaiting').length, 'is-awaiting'],
    ['Offers', rows.filter((r) => r.stage === 'offer').length, 'is-offer'],
  ];
  $('#stats').innerHTML = tiles.map(([label, n, cls]) =>
    `<div class="stat ${cls}"><span class="n">${n}</span><span class="k">${label}</span></div>`).join('');
}

function renderPipeline() {
  $('#pipeline').innerHTML = STAGES.map(([key, label, group]) => {
    const n = rows.filter((r) => r.stage === key).length;
    return `<span class="pipe"><span class="dot" style="background:var(--st-${group})"></span>` +
           `${label}<span class="c">${n}</span></span>`;
  }).join('');
}

function renderFilters() {
  const build = (host, items, current, kind) => {
    host.querySelectorAll('.chip').forEach((c) => c.remove());
    items.forEach(([value, label]) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'chip';
      b.textContent = label;
      b.setAttribute('aria-pressed', String(current === value));
      b.addEventListener('click', () => {
        if (kind === 'type') { fType = value; pref.set('gd.filter.type', value); }
        else { fStatus = value; pref.set('gd.filter.status', value); }
        renderFilters();
        renderSections();
      });
      host.appendChild(b);
    });
  };
  build($('#f-type'), TYPE_FILTERS, fType, 'type');
  build($('#f-status'), STATUS_FILTERS, fStatus, 'status');
}

function renderDeadlines() {
  const soon = rows.filter((r) => r.dateISO)
    .sort((a, b) => a.dateISO.localeCompare(b.dateISO))
    .slice(0, 8);
  if (!soon.length) {
    $('#deadlines').innerHTML = '<p style="margin:0">No confirmed closing dates yet — the ' +
      'open rows are either rolling or still showing “TBC”.</p>';
    return;
  }
  $('#deadlines').innerHTML = soon.map((r) => {
    const days = daysUntil(r.dateISO);
    const urgent = days <= 14;
    return `<div class="dl-item">
      <span class="co">${esc(r.company)}<small>${esc(r.role)}</small></span>
      <span class="dd ${urgent ? 'soon' : ''}">${formatDate(r.dateISO)}<br>${countdown(days)}</span>
    </div>`;
  }).join('');
}

/* ── row pieces ───────────────────────────────────────────────────────── */
function subRolesHTML(row) {
  if (!Array.isArray(row.subRoles) || !row.subRoles.length) return '';
  const pills = row.subRoles.map((s) => {
    const cls = s.highlighted ? 'sr star' : 'sr';
    const star = s.highlighted ? '<span aria-hidden="true">★</span>' : '';
    const inner = `${star}<span class="nm">${esc(s.name)}</span>`;
    const title = esc(s.reason || s.name);
    return s.url
      ? `<a class="${cls}" href="${esc(s.url)}" target="_blank" rel="noopener" title="${title}">${inner}</a>`
      : `<span class="${cls}" title="${title}">${inner}</span>`;
  }).join('');
  return `<div class="subroles">${pills}</div>`;
}

function pinHTML(row) {
  const picked = row.selectedProgramme;
  const editing = openPins.has(row.id) || !picked;
  const hasSubs = Array.isArray(row.subRoles) && row.subRoles.length;

  if (picked && !editing) {
    const name = esc(picked.name);
    const link = picked.url
      ? `<a href="${esc(picked.url)}" target="_blank" rel="noopener">${name}</a>`
      : name;
    return `<div class="pin"><span class="pin-lbl">Applying for</span>${link}
      <button class="linkish" data-act="pin-edit" type="button">edit</button></div>`;
  }

  let controls = '';
  if (hasSubs) {
    const options = row.subRoles.map((s, i) => {
      const on = picked && picked.name === s.name ? ' selected' : '';
      return `<option value="${i}"${on}>${esc(s.name)}</option>`;
    }).join('');
    const custom = picked && !row.subRoles.some((s) => s.name === picked.name) ? ' selected' : '';
    controls += `<select data-act="pin-select" aria-label="Choose the programme applied for">
      <option value="">Pick a track…</option>${options}
      <option value="custom"${custom}>Other / custom link</option></select>`;
  }
  const showCustom = !hasSubs ||
    (picked && !row.subRoles.some((s) => s.name === picked.name)) ||
    (!picked && !hasSubs);
  if (!hasSubs || showCustom) {
    controls += `<input data-act="pin-name" placeholder="Programme name"
        value="${esc(picked ? picked.name : '')}" aria-label="Programme name">
      <input data-act="pin-url" placeholder="https://…"
        value="${esc(picked ? picked.url : '')}" aria-label="Programme URL">`;
  }
  return `<div class="pin"><span class="pin-lbl">Applying for</span>
    ${picked ? '<button class="linkish" data-act="pin-done" type="button">done</button>' : ''}
    <div class="pin-edit">${controls}</div></div>`;
}

function analysisBadge(row) {
  const analysis = row.cvAnalysis;
  if (!analysis) return '';
  const group = analysis.score >= 7 ? 'offer' : analysis.score >= 5 ? 'awaiting' : 'rejected';
  const verb = analysis.action === 'reworked_and_renamed' ? 'reworked to fit + renamed' : 'renamed';
  return `<span class="badge b-${group}" title="${esc(analysis.summary || '')}">${analysis.score}/10 — ${verb}</span>`;
}

function cvHTML(row) {
  const file = row.cvFile;
  const analysis = row.cvAnalysis;
  const badge = analysisBadge(row);

  if (!file) {
    // An analysis written straight into data.json from chat must still be visible
    // even when no file has been dropped on this row.
    return `<div class="cvbox drop" data-act="drop">
      <input type="file" class="hidden-file" accept=".pdf,.doc,.docx" data-act="file">
      Drop a CV here (PDF/DOC) or click to choose
    </div>
    ${badge ? `<div class="cv-line" style="margin-top:8px">${badge}</div>` : ''}
    ${analysis ? `<div class="cv-summary">${esc(analysis.summary || '')}</div>` : ''}`;
  }

  // The CV used for this application: whatever a chat-driven analysis last renamed
  // it to (Ayaan.Warraich.<FIRM>.CV.pdf), or your original upload if none has run yet.
  return `<div class="cvbox has" data-act="drop">
    <input type="file" class="hidden-file" accept=".pdf,.doc,.docx" data-act="file">
    <div class="cv-label">CV used for this application</div>
    <div class="cv-line">
      <span class="cv-name">${esc(file.filename)}</span>
      <span class="cv-size">${formatBytes(file.size)}</span>
      ${badge}
    </div>
    <div class="cv-line" style="margin-top:8px">
      <button class="mini" data-act="cv-download" type="button">Download</button>
      <button class="mini" data-act="cv-remove" type="button">Remove</button>
    </div>
    ${analysis ? `<div class="cv-summary">${esc(analysis.summary || '')}</div>` : ''}
  </div>`;
}

function rowHTML(row) {
  const isPersonal = row.type === 'personal';
  const stageGroup = STAGE_GROUP[row.stage] || 'neutral';
  const status = STATUS[row.status];

  const statusBadge = (!isPersonal && status)
    ? `<span class="badge b-${status.group}"><span class="g" aria-hidden="true">${status.glyph}</span>${status.label}</span>`
    : '';

  const deadline = row.dateISO
    ? (() => {
        const days = daysUntil(row.dateISO);
        return `<div class="deadline">${formatDate(row.dateISO)}
          <span class="days ${days <= 14 ? 'soon' : ''}">${countdown(days)}</span></div>`;
      })()
    : `<div class="deadline">${row.sourceUrl
        ? `<a href="${esc(row.sourceUrl)}" target="_blank" rel="noopener">${esc(row.deadlineLabel)} ↗</a>`
        : esc(row.deadlineLabel)}</div>`;

  const cvTag = isPersonal ? '' : (row.cv
    ? `<span class="tag cv">${esc(row.cv)}</span>`
    : '<span class="tag cv pending">pending your CV</span>');

  const stageOptions = STAGES.map(([key, label]) =>
    `<option value="${key}"${row.stage === key ? ' selected' : ''}>${label}</option>`).join('');

  const armed = armedDeletes.has(row.id);

  return `<article class="row" data-id="${esc(row.id)}">
    <div class="row-main">
      <h3 class="row-title">${esc(row.company)}</h3>
      <p class="row-role">${esc(row.role)}</p>
      ${isPersonal ? '' : pinHTML(row)}
      <div class="tags">
        <span class="tag">${esc(row.sector)}</span>
        ${cvTag}
        <span class="badge b-${stageGroup}">${esc(STAGE_LABEL[row.stage] || row.stage)}</span>
      </div>
      ${subRolesHTML(row)}
    </div>
    <div class="row-side">
      ${statusBadge}
      ${deadline}
      <span class="side-lbl">Progress</span>
      <select class="stage" data-act="stage" aria-label="Stage for ${esc(row.company)}">${stageOptions}</select>
      ${isPersonal ? '' : `<button class="del ${armed ? 'arm' : ''}" data-act="del" type="button">
        ${armed ? 'Click again to delete' : 'Delete'}</button>`}
    </div>
    <div class="row-extra">
      <textarea class="notes" data-act="notes" aria-label="Notes for ${esc(row.company)}"
        placeholder="Notes…">${esc(row.notes)}</textarea>
      ${isPersonal ? '' : cvHTML(row)}
    </div>
  </article>`;
}

/* ── sections ─────────────────────────────────────────────────────────── */
function matchesQuery(row, q) {
  if (!q) return true;
  return [row.company, row.role, row.sector]
    .some((v) => String(v || '').toLowerCase().includes(q));
}

function renderSections() {
  const host = $('#sections');
  const parts = [];
  const q = query.trim().toLowerCase();

  for (const section of SECTIONS) {
    if (fType !== 'all' && fType !== section.type) continue;

    const all = rows.filter((r) => r.type === section.type);
    const visible = all.filter((r) =>
      (fStatus === 'any' || section.type === 'personal' || r.status === fStatus)
      && matchesQuery(r, q));

    // While searching, an empty section is just noise — drop it entirely.
    if (q && !visible.length) continue;

    const count = visible.length === all.length
      ? `${all.length}`
      : `${visible.length} of ${all.length}`;

    parts.push(`<section class="section" data-type="${section.type}">
      <div class="section-head"><h2>${esc(section.title)}</h2><span class="count">${count}</span></div>
      <div class="rows">${visible.length
        ? visible.map(rowHTML).join('')
        : '<p class="empty">Nothing here under the current filters.</p>'}</div>
      ${section.addable && !q ? addFormHTML(section) : ''}
    </section>`);
  }

  host.innerHTML = parts.length
    ? parts.join('')
    : `<p class="empty">Nothing matches “${esc(query.trim())}”.</p>`;
}

function addFormHTML(section) {
  return `<form class="addform" data-add="${section.type}">
    <input name="company" placeholder="Company" required>
    <input name="role" placeholder="Programme / role">
    <input name="sector" placeholder="Sector tag">
    <input name="deadlineLabel" placeholder="Deadline label">
    <input name="sourceUrl" placeholder="Link">
    <button class="go" type="submit">Add application</button>
  </form>`;
}

function renderAll() {
  renderStats();
  renderPipeline();
  renderDeadlines();
  renderSections();
}

/* ── events (delegated, so re-renders don't drop handlers) ────────────── */
const sections = $('#sections');

sections.addEventListener('change', async (event) => {
  const target = event.target;
  const article = target.closest('.row');
  const act = target.dataset.act;

  if (article && act === 'stage') {
    const id = article.dataset.id;
    const row = rows.find((r) => r.id === id);
    if (row) row.stage = target.value;
    await patch(id, { stage: target.value });
    renderAll();
    return;
  }

  if (article && act === 'file') {
    const file = target.files && target.files[0];
    if (file) uploadCV(article.dataset.id, file);
    target.value = '';
    return;
  }

  if (article && act === 'pin-select') {
    const id = article.dataset.id;
    const row = rows.find((r) => r.id === id);
    if (!row) return;
    if (target.value === 'custom') {
      openPins.add(id);
      row.selectedProgramme = row.selectedProgramme || { name: '', url: '' };
      renderSections();
      const input = sections.querySelector(`.row[data-id="${CSS.escape(id)}"] [data-act="pin-name"]`);
      if (input) input.focus();
      return;
    }
    if (target.value === '') return;
    const sub = row.subRoles[Number(target.value)];
    if (!sub) return;
    row.selectedProgramme = { name: sub.name, url: sub.url || '' };
    openPins.delete(id);
    await patch(id, { selectedProgramme: row.selectedProgramme });
    renderSections();
  }
});

sections.addEventListener('blur', async (event) => {
  const target = event.target;
  const article = target.closest && target.closest('.row');
  if (!article) return;
  const id = article.dataset.id;
  const row = rows.find((r) => r.id === id);
  if (!row) return;

  if (target.dataset.act === 'notes') {
    if (target.value === row.notes) return;
    row.notes = target.value;
    await patch(id, { notes: target.value });
    renderAll();
    return;
  }

  if (target.dataset.act === 'pin-name' || target.dataset.act === 'pin-url') {
    const nameEl = article.querySelector('[data-act="pin-name"]');
    const urlEl = article.querySelector('[data-act="pin-url"]');
    const next = { name: (nameEl && nameEl.value.trim()) || '', url: (urlEl && urlEl.value.trim()) || '' };
    const current = row.selectedProgramme || { name: '', url: '' };
    if (next.name === current.name && next.url === current.url) return;
    row.selectedProgramme = next.name || next.url ? next : undefined;
    await patch(id, { selectedProgramme: row.selectedProgramme || null });
  }
}, true);

sections.addEventListener('click', async (event) => {
  const target = event.target.closest('[data-act]');
  if (!target) return;
  const article = target.closest('.row');
  if (!article) return;
  const id = article.dataset.id;
  const act = target.dataset.act;

  if (act === 'pin-edit') { openPins.add(id); renderSections(); return; }
  if (act === 'pin-done') { openPins.delete(id); renderSections(); return; }

  if (act === 'del') {
    if (!armedDeletes.has(id)) {
      armedDeletes.add(id);
      renderSections();
      setTimeout(() => { if (armedDeletes.delete(id)) renderSections(); }, 4000);
      return;
    }
    armedDeletes.delete(id);
    inFlight += 1;
    try {
      await api(`/api/applications/${id}`, { method: 'DELETE' });
      rows = rows.filter((r) => r.id !== id);
      serialised = JSON.stringify(rows);
      flashSaved();
      renderAll();
    } catch (err) {
      toast(`Couldn't delete: ${err.message}`, true);
    } finally { inFlight -= 1; }
    return;
  }

  if (act === 'drop') {
    const input = article.querySelector('[data-act="file"]');
    if (input && !event.target.closest('button')) input.click();
    return;
  }

  if (act === 'cv-download') { window.location.href = `/api/applications/${id}/cv`; return; }

  if (act === 'cv-remove') {
    inFlight += 1;
    try {
      mergeRow(await api(`/api/applications/${id}/cv`, { method: 'DELETE' }));
      flashSaved();
      renderSections();
    } catch (err) {
      toast(`Couldn't remove the CV: ${err.message}`, true);
    } finally { inFlight -= 1; }
    return;
  }
});

sections.addEventListener('submit', async (event) => {
  const form = event.target.closest('.addform');
  if (!form) return;
  event.preventDefault();
  const payload = { type: form.dataset.add };
  new FormData(form).forEach((value, key) => { payload[key] = String(value).trim(); });
  if (!payload.company) return;
  inFlight += 1;
  try {
    rows.push(await api('/api/applications', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }));
    serialised = JSON.stringify(rows);
    form.reset();
    flashSaved();
    renderAll();
  } catch (err) {
    toast(`Couldn't add: ${err.message}`, true);
  } finally { inFlight -= 1; }
});

/* drag and drop onto the CV zone */
['dragenter', 'dragover'].forEach((type) => {
  sections.addEventListener(type, (event) => {
    const zone = event.target.closest && event.target.closest('.cvbox');
    if (!zone) return;
    event.preventDefault();
    zone.classList.add('over');
  });
});
sections.addEventListener('dragleave', (event) => {
  const zone = event.target.closest && event.target.closest('.cvbox');
  if (zone) zone.classList.remove('over');
});
sections.addEventListener('drop', (event) => {
  const zone = event.target.closest && event.target.closest('.cvbox');
  if (!zone) return;
  event.preventDefault();
  zone.classList.remove('over');
  const file = event.dataTransfer.files && event.dataTransfer.files[0];
  if (file) uploadCV(zone.closest('.row').dataset.id, file);
});

/* ── CV upload + AI jobs ──────────────────────────────────────────────── */
async function uploadCV(id, file) {
  const ext = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();
  if (!['.pdf', '.doc', '.docx'].includes(ext)) {
    toast('Only .pdf, .doc and .docx files can be attached.', true);
    return;
  }
  if (file.size > 15 * 1024 * 1024) {
    toast('That file is larger than 15MB.', true);
    return;
  }
  const body = new FormData();
  body.append('file', file);
  inFlight += 1;
  try {
    mergeRow(await api(`/api/applications/${id}/cv`, { method: 'POST', body }));
    flashSaved();
    toast(`Attached ${file.name}`);
    renderSections();
  } catch (err) {
    toast(`Upload failed: ${err.message}`, true);
  } finally { inFlight -= 1; }
}

/* ── polling: pick up edits Claude Code makes to data.json ────────────── */
function userIsEditing() {
  const el = document.activeElement;
  return !!(el && sections.contains(el) &&
    ['TEXTAREA', 'INPUT', 'SELECT'].includes(el.tagName));
}

function adopt(next) {
  rows = next;
  serialised = JSON.stringify(next);
  renderAll();
}

async function poll() {
  // Skip entirely while the user is mid-edit or a write is in flight. `serialised`
  // stays stale, so the very next tick after they blur adopts fresh data — never a
  // snapshot taken before their edit was saved, which would flash the old text back.
  if (inFlight > 0 || userIsEditing()) return;
  let next;
  try { next = await api('/api/applications'); } catch { return; }
  if (JSON.stringify(next) === serialised) return;
  adopt(next);
}

/* ── search ───────────────────────────────────────────────────────────── */
const searchInput = $('#search');
searchInput.addEventListener('input', () => {
  query = searchInput.value;
  renderSections();
});
searchInput.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') {
    searchInput.value = '';
    query = '';
    renderSections();
  }
});

/* ── boot ─────────────────────────────────────────────────────────────── */
(async function start() {
  renderFilters();
  try {
    adopt(await api('/api/applications'));
  } catch (err) {
    $('#sections').innerHTML =
      `<p class="empty">Couldn't reach the server — is <code>python app.py</code> running? (${esc(err.message)})</p>`;
    return;
  }
  setInterval(poll, 3000);
})();
