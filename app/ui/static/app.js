// Aegis DeID — Clinical Archive front-end
// Rewritten for US/CA PHI workflows: no Greek samples, inline highlighted
// redaction view, coloured by policy action (hash/mask/redact).

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

const els = {
  original:    $('#original'),
  deid:        $('#deid'),
  deidView:    $('#deid-view'),
  lang:        $('#lang'),
  policy:      $('#policy'),
  run:         $('#run-btn'),
  clear:       $('#clear-btn'),
  upload:      $('#upload-btn'),
  fileInput:   $('#file-input'),
  download:    $('#download-btn'),
  copy:        $('#copy-btn'),
  paste:       $('#paste-btn'),
  charCounter: $('#char-counter'),
  dropzone:    $('#dropzone'),
  metrics:     $('#metrics-text'),
  lastEvalLink:$('#last-eval-link'),
  evalModal:   $('#eval-modal'),
  evalContent: $('#eval-content'),
  evalClose:   $('#close-eval'),
  entitiesBody:$('#entities-body'),
  labelFilter: $('#label-filter'),
  actionFilter:$('#action-filter'),
  minLenRange: $('#minlen-range'),
  minLenValue: $('#minlen-value'),
  sortBy:      $('#sort-by'),
  search:      $('#search-input'),
  prevPage:    $('#prev-page'),
  nextPage:    $('#next-page'),
  pageInfo:    $('#page-info'),
  tabs:        $('#files-tabs'),
  tablist:     $('#file-tablist'),
  panels:      $('#file-panels'),
};

// ─────────────────────────────────────────────────────────────
// US / CA sample library
// ─────────────────────────────────────────────────────────────
const SAMPLES = {
  medical: `Patient:  Eleanor R. Whitfield
MRN:      BWH-47882910
DOB:      03/14/1968
SSN:      412-55-7891
Address:  482 Commonwealth Avenue, Boston, MA 02215
Phone:    (617) 555-0134   Alt: 617.432.9008
Email:    e.whitfield@example.org
NPI:      NPI# 1538296472  (referring provider: Dr. J. Okonkwo)
DEA:      BO4872913
Insurer:  Blue Cross HICN 1EG4-TE5-MK73
Visit:    04/02/2026 — complaint of persistent chest discomfort, labs ordered.
Notes:    Patient reports allergy to penicillin; current med list includes
          lisinopril 10mg and atorvastatin 40mg.  Follow-up scheduled 04/16/2026.`,

  insurance: `Claim #:  CLM-2026-0091-43821
Member:   Marcus T. Delacroix
SIN:      046 454 286   (Canadian claimant)
Health Card: 4532-281-947-AB   (Ontario)
Address:  180 Bloor Street West, Toronto ON, M5S 2V6
Phone:    +1 416 555 0192
Email:    m.delacroix@example.ca

Service Date: 03/28/2026
Provider:     Sunnybrook Health Sciences, NPI 1093748572
Diagnosis:    K21.9 — GERD, unspecified
Amount billed:  $4,812.50 USD
Card on file:   4532 8827 1104 9951  exp 09/28
Routing (ACH refund): ABA: 026009593
IBAN (secondary):    GB29 NWBK 6016 1331 9268 19`,

  financial: `From:   James O'Hara <jim.ohara@example.com>
To:     stefan.muller@example.de
Sent:   04/10/2026 09:42

Stefan — following up on the wire.  Please confirm the beneficiary details:

  Account holder:  James O'Hara
  SSN (last-4 redacted on prior thread): 537-22-4419
  Passport #:      518294776
  Home:            1420 West Lafayette Blvd, Detroit, MI 48216
  Mobile:          +1 (313) 555-0180
  Card ending:     5412 7533 1900 8826
  Routing #:       ABA 072000096
  IBAN:            DE89 3704 0044 0532 0130 00

Expected amount USD 218,500.  Please respond to this email or call me
directly.  Server audit trail: client IP 72.14.212.85, session logged at
https://portal.example.com/sessions/7J8A-2291.`,

  incident: `Incident Report — Ref: IR-2026-00481
Filed: 04/08/2026 by Officer K. Ramirez, Badge 88142

Subject:     Natalie Chen, DOB 11/22/1991
Address:     755 Sansome Street Apt 4B, San Francisco, CA 94111
Phone:       (415) 555-0176
Email:       nat.chen@example.com
Driver Lic:  C5528194

Narrative:  At approximately 14:32 on 04/08/2026, subject reported unauthorized
            access to her medical chart at UCSF Medical Center (MRN: UCSF-0039821).
            Subject's SSN (651-28-4417) was used to request refills for controlled
            substances under DEA number AC9137284.  Incident forwarded to HIPAA
            compliance unit.  Server trail: 10.24.88.113 — session expired 15:04.`,
};

// ─────────────────────────────────────────────────────────────
// Toast helper
// ─────────────────────────────────────────────────────────────
const toast = (msg, type = 'success', timeout = 3500) => {
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.textContent = msg;
  $('#toaster').appendChild(t);
  setTimeout(() => t.remove(), timeout);
};

// ─────────────────────────────────────────────────────────────
// State
// ─────────────────────────────────────────────────────────────
const state = {
  policy: 'mask',
  entities: [],
  originalText: '',
  resultText: '',
  page: 1,
  pageSize: 20,
  labels: new Set(),
  files: [],
  maxTextSize: 500000,
};

// ─────────────────────────────────────────────────────────────
// API
// ─────────────────────────────────────────────────────────────
// When served via a reverse-proxy subpath (e.g. /aegis-deid/), absolute
// paths like "/api/v1/deid" resolve against the domain root which is a
// different origin. Derive a base prefix from our own script's URL so
// the same build works whether mounted at "/" or "/aegis-deid/".
const APP_BASE = (() => {
  const scripts = document.getElementsByTagName('script');
  for (let i = scripts.length - 1; i >= 0; i--) {
    const src = scripts[i].src || '';
    const m = src.match(/^(.*)\/static\/app\.js(?:\?.*)?$/);
    if (m) {
      try { return new URL(m[1] + '/').pathname.replace(/\/$/, ''); }
      catch (e) { /* ignore */ }
    }
  }
  return '';
})();

function apiPath(path) {
  // Normalize: accept both "/api/v1/…" and "api/v1/…" callers
  const p = path.startsWith('/') ? path : '/' + path;
  return APP_BASE + p;
}

async function fetchJSON(url, opts = {}) {
  const headers = new Headers(opts.headers || {});
  const k = localStorage.getItem('apiKey');
  if (k) headers.set('X-API-Key', k);
  opts.headers = headers;
  const res = await fetch(apiPath(url), opts);
  const ct = (res.headers.get('content-type') || '').toLowerCase();
  if (!res.ok) {
    if (ct.includes('application/json')) {
      const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    const txt = await res.text().catch(() => '');
    throw new Error(txt || `HTTP ${res.status}`);
  }
  if (ct.includes('application/json')) return res.json();
  return { detail: await res.text() };
}

const api = {
  getConfig:  () => fetchJSON('/api/v1/config'),
  putConfig:  (data) => fetchJSON('/api/v1/config', { method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) }),
  deid:       (text, lang_hint) => fetchJSON('/api/v1/deid', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ text, lang_hint }) }),
  deidFiles:  (files, lang_hint) => {
    const fd = new FormData();
    for (const f of files) fd.append('files', f);
    if (lang_hint) fd.append('lang_hint', lang_hint);
    return fetchJSON('/api/v1/deid/file', { method: 'POST', body: fd });
  },
  lastMetrics: () => fetchJSON('/api/v1/metrics/last'),
};

// ─────────────────────────────────────────────────────────────
// Inline highlighted render — reconstructs text with highlighted spans
// by replaying the engine's entity list over the original text
// ─────────────────────────────────────────────────────────────
function renderHighlightedOutput(original, resultText, entities) {
  const view = els.deidView;
  view.innerHTML = '';

  if (!original || (!entities || entities.length === 0)) {
    const raw = document.createElement('div');
    raw.textContent = resultText || '';
    view.appendChild(raw);
    return;
  }

  // Entities are reported with spans into the ORIGINAL text. We walk the
  // original text, slice plain segments for non-redacted ranges, and for
  // each entity slice replace with a highlighted <span> showing the
  // replacement text (rebuilt from `resultText`).
  const sorted = entities
    .map(e => ({ ...e, start: e.span ? e.span[0] : e.start, end: e.span ? e.span[1] : e.end }))
    .sort((a, b) => a.start - b.start);

  // Walk through result text, mirroring original positions.  To know what
  // each span was replaced with, we scan through `resultText` character by
  // character.  Simpler: re-run policy locally based on value + action.
  let cursor = 0;
  const frag = document.createDocumentFragment();

  // Rebuild: for each original entity, compute replacement text the engine
  // would produce — but easier to scan resultText at replacement points.
  // We approximate by tracking an offset delta.
  let delta = 0;
  for (const ent of sorted) {
    if (ent.start > cursor) {
      const plain = document.createTextNode(original.slice(cursor, ent.start));
      frag.appendChild(plain);
    }
    // Find the replacement in resultText at original.start + delta.
    const rStart = ent.start + delta;
    // Estimate the length of replacement: scan forward until next entity or end
    let nextOrigIdx = null;
    const idx = sorted.indexOf(ent);
    if (idx + 1 < sorted.length) nextOrigIdx = sorted[idx + 1].start;
    let rEnd;
    if (nextOrigIdx != null) {
      // bytes between current entity and next entity in original
      const origBetween = nextOrigIdx - ent.end;
      // find rEnd such that resultText[rEnd : rEnd + origBetween] matches original between
      rEnd = (resultText.length) - (original.length - ent.end) - ((original.length - nextOrigIdx));
      // simpler: compute rEnd by matching a known suffix
      const suffix = original.slice(ent.end, ent.end + Math.min(16, origBetween));
      if (suffix.length) {
        const found = resultText.indexOf(suffix, rStart);
        if (found >= 0) rEnd = found;
      }
    } else {
      // last entity: suffix is the tail of original after ent.end
      const tail = original.slice(ent.end);
      if (tail.length) {
        const found = resultText.indexOf(tail, rStart);
        rEnd = found >= 0 ? found : resultText.length;
      } else {
        rEnd = resultText.length;
      }
    }
    if (rEnd == null || rEnd < rStart) rEnd = rStart;
    const replacement = resultText.slice(rStart, rEnd);
    delta += (replacement.length - (ent.end - ent.start));

    const span = document.createElement('span');
    span.className = 'redacted-span';
    span.dataset.action = ent.action || 'redact';
    span.dataset.label = ent.label || '';
    span.title = `${ent.label} · ${ent.action}`;
    const lab = document.createElement('span');
    lab.className = 'lbl';
    lab.textContent = (ent.label || '').toLowerCase();
    const val = document.createElement('span');
    val.textContent = replacement || `[${ent.label}]`;
    span.appendChild(lab);
    span.appendChild(val);
    frag.appendChild(span);

    cursor = ent.end;
  }
  if (cursor < original.length) {
    frag.appendChild(document.createTextNode(original.slice(cursor)));
  }
  view.appendChild(frag);
}

// ─────────────────────────────────────────────────────────────
// UI helpers
// ─────────────────────────────────────────────────────────────
const ui = {
  disableActions(disabled) {
    [els.run, els.clear, els.upload, els.download].forEach(b => b && (b.disabled = disabled));
  },
  updateCharCount() {
    const n = (els.original.value || '').length;
    els.charCounter.textContent = `${n.toLocaleString()} chars`;
  },
  copyOutput() {
    const txt = state.resultText || els.deid.value || '';
    navigator.clipboard.writeText(txt).then(
      () => toast('Copied to clipboard', 'success'),
      () => toast('Copy failed', 'error'),
    );
  },
  downloadResult(name = 'redacted.txt') {
    const txt = state.resultText || els.deid.value || '';
    const blob = new Blob([txt], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = name; a.click();
    URL.revokeObjectURL(url);
  },
  setMetrics({ time_ms, entities }) {
    const count = (entities || []).length;
    els.metrics.textContent = `${time_ms ?? '—'}ms · ${count} entities`;
  },
  showEvalModal(data) {
    if (!data) { els.evalContent.textContent = 'No evaluation yet.'; els.evalModal.showModal(); return; }
    const f1 = data.f1 || {};
    const fmt = (x) => typeof x === 'number' ? x.toFixed(3) : (x ?? '—');
    const micro = fmt(f1.micro); const macro = fmt(f1.macro);
    const labels = Object.keys(f1).filter(k => k !== 'micro' && k !== 'macro').sort();
    let html = `<div>F1 micro: <strong>${micro}</strong> · F1 macro: <strong>${macro}</strong></div>`;
    if (labels.length) {
      html += '<div style="margin-top:8px"></div>';
      html += '<table class="ledger"><thead><tr><th>Label</th><th>F1</th></tr></thead><tbody>';
      for (const lab of labels) html += `<tr><td>${lab}</td><td>${fmt(f1[lab])}</td></tr>`;
      html += '</tbody></table>';
    }
    els.evalContent.innerHTML = html;
    els.evalModal.showModal();
  },
  closeEvalModal() { els.evalModal.close(); },
};

// ─────────────────────────────────────────────────────────────
// Known labels (for the filter dropdown)
// ─────────────────────────────────────────────────────────────
const KNOWN_LABELS = [
  'PERSON','ORG','GPE','LOC','ADDRESS','EMAIL',
  'PHONE_US','PHONE_INTL','SSN','SIN_CA','NPI','DEA','PASSPORT_US',
  'MRN','HICN','HEALTH_CARD_CA',
  'CREDIT_CARD','ROUTING','IBAN',
  'US_STREET','ZIP_US','POSTAL_CA','DATE','URL','IP',
];

const render = {
  refreshFilters() {
    const sel = els.labelFilter;
    const prev = Array.from(sel.selectedOptions).map(o => o.value).filter(Boolean);
    sel.innerHTML = '';
    const labels = Array.from(new Set([...KNOWN_LABELS, ...state.labels])).sort();
    const all = document.createElement('option'); all.value = ''; all.textContent = 'Labels: All'; sel.appendChild(all);
    labels.forEach(l => {
      const o = document.createElement('option');
      o.value = l; o.textContent = l;
      if (prev.includes(l)) o.selected = true;
      sel.appendChild(o);
    });
  },
  entitiesTable() {
    const body = els.entitiesBody; body.innerHTML = '';
    let items = state.entities.slice();
    const q = (els.search.value || '').toLowerCase().trim();
    const selectedLabels = Array.from(els.labelFilter.selectedOptions).map(o => o.value).filter(Boolean);
    const act = els.actionFilter.value || '';
    const minLen = parseInt(els.minLenRange.value || '0', 10);
    if (q) items = items.filter(e => (e.sample || '').toLowerCase().includes(q));
    if (selectedLabels.length) items = items.filter(e => selectedLabels.includes(e.label));
    if (act) items = items.filter(e => e.action === act);
    if (minLen > 0) items = items.filter(e => (e.sample || '').length >= minLen);
    const sortBy = els.sortBy.value || 'start';
    items.sort((a, b) =>
      sortBy === 'label'  ? a.label.localeCompare(b.label) :
      sortBy === 'length' ? (b.sample.length - a.sample.length) :
                            (a.start - b.start));

    const total = items.length;
    const pages = Math.max(1, Math.ceil(total / state.pageSize));
    if (state.page > pages) state.page = pages;
    if (state.page < 1) state.page = 1;
    const startIdx = (state.page - 1) * state.pageSize;
    const pageItems = items.slice(startIdx, startIdx + state.pageSize);
    els.pageInfo.textContent = `Page ${state.page} / ${pages}`;
    els.prevPage.disabled = state.page <= 1;
    els.nextPage.disabled = state.page >= pages;

    if (pageItems.length === 0) {
      const tr = document.createElement('tr'); tr.className = 'empty';
      const td = document.createElement('td'); td.colSpan = 5;
      td.textContent = total === 0 ? 'No entities detected. Paste text and press Redact.' : 'No entities match filters.';
      tr.appendChild(td); body.appendChild(tr);
      return;
    }
    pageItems.forEach((e, i) => {
      const tr = document.createElement('tr');
      const action = (e.action || 'redact');
      tr.innerHTML = `
        <td class="c-idx">${String(startIdx + i + 1).padStart(3, '0')}</td>
        <td class="c-label"><span class="tag ${action}">${e.label}</span></td>
        <td class="c-sample">${escapeHtml(e.sample || '')}</td>
        <td class="c-action">${action}</td>
        <td class="c-span">[${e.start}–${e.end}]</td>
      `;
      body.appendChild(tr);
    });
  },
  fileTabs(files) {
    if (!files || files.length === 0) {
      els.tabs.classList.add('hidden'); els.tablist.innerHTML = ''; els.panels.innerHTML = '';
      localStorage.removeItem('activeTabFile'); return;
    }
    els.tabs.classList.remove('hidden'); els.tablist.innerHTML = ''; els.panels.innerHTML = '';
    const stored = localStorage.getItem('activeTabFile');
    let activeIdx = files.findIndex(f => f.name === stored);
    if (activeIdx < 0) activeIdx = 0;
    files.forEach((res, idx) => {
      const id = `tab-${idx}`;
      const tab = document.createElement('button');
      tab.className = 'tab' + (idx === activeIdx ? ' active' : '');
      tab.setAttribute('role', 'tab');
      tab.dataset.target = id; tab.dataset.idx = String(idx);
      tab.innerHTML = `<span class="label">${res.name}</span><button class="close" aria-label="Close">×</button>`;
      tab.addEventListener('click', (ev) => {
        if (ev.target && ev.target.classList.contains('close')) return;
        setActiveTab(idx);
      });
      tab.querySelector('.close').addEventListener('click', (ev) => {
        ev.stopPropagation(); removeTab(idx);
      });
      els.tablist.appendChild(tab);
      const panel = document.createElement('div');
      panel.className = 'panel' + (idx === activeIdx ? ' active' : '');
      panel.id = id;
      panel.innerHTML = `<textarea readonly rows="12">${escapeHtml(res.result.result_text || '')}</textarea>`;
      els.panels.appendChild(panel);
    });
    updateFromFileIndex(activeIdx);
  },
};

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#039;');
}

function withSamples(entities, _origLen, originalText) {
  return (entities || []).map(e => {
    const [s, e2] = e.span || [e.start, e.end];
    const sample = (originalText || '').slice(s, e2);
    return { ...e, start: s, end: e2, sample };
  });
}

function debounce(fn, t = 250) { let h; return (...a) => { clearTimeout(h); h = setTimeout(() => fn(...a), t); }; }

// ─────────────────────────────────────────────────────────────
// Main action — run de-identification
// ─────────────────────────────────────────────────────────────
async function runDeidInline() {
  const text = els.original.value || '';
  if (!text.trim()) { toast('Paste some text or load a sample first', 'error'); return; }
  if (text.length > state.maxTextSize) { toast('Text exceeds client guard — please split', 'error'); return; }

  ui.disableActions(true);
  els.deidView.innerHTML = '<div class="ghost">Redacting…</div>';
  const runLabel = els.run.querySelector('span');
  const prevText = runLabel ? runLabel.textContent : '';
  els.run.classList.add('loading');
  if (runLabel) runLabel.textContent = 'Redacting…';

  try {
    const data = await api.deid(text, els.lang.value || null);
    const result = data.result_text || '';
    state.originalText = text;
    state.resultText = result;
    state.entities = withSamples(data.entities, data.original_len, text);
    state.labels = new Set(state.entities.map(e => e.label));
    els.deid.value = result;
    renderHighlightedOutput(text, result, state.entities);
    ui.setMetrics({ time_ms: data.time_ms, entities: data.entities });
    render.refreshFilters(); state.page = 1; render.entitiesTable();
    toast(`Redacted · ${state.entities.length} entities in ${data.time_ms}ms`, 'success');
  } catch (e) {
    const msg = String(e && e.message ? e.message : e);
    els.deidView.innerHTML = `<div class="ghost" style="color: var(--vermillion)">${escapeHtml(msg)}</div>`;
    if (msg.includes('401') || msg.toLowerCase().includes('unauthorized'))      toast('Unauthorized — check your API key', 'error');
    else if (msg.includes('413') || msg.toLowerCase().includes('payload too large')) toast('Payload too large — please split input', 'error');
    else                                                                         toast(msg, 'error');
  } finally {
    ui.disableActions(false);
    els.run.classList.remove('loading');
    if (runLabel) runLabel.textContent = prevText || 'Redact';
  }
}

async function runDeidFiles(fileList) {
  if (!fileList || fileList.length === 0) return;
  ui.disableActions(true);
  try {
    const data = await api.deidFiles(fileList, els.lang.value || null);
    const results = data.map((r, i) => ({ name: fileList[i]?.name || `file-${i+1}.txt`, result: r, original: '' }));
    await Promise.all(results.map(async (x, i) => { x.original = await fileList[i].text(); }));
    state.files = [...state.files, ...results];
    render.fileTabs(state.files);
    const newIdx = state.files.length - results.length;
    setActiveTab(newIdx);
    const totalDocs = results.length;
    const totalMs = results.reduce((a, b) => a + (b.result.time_ms || 0), 0);
    const dps = totalDocs && totalMs ? (totalDocs / (totalMs / 1000)).toFixed(1) : '—';
    els.metrics.textContent = `${totalMs}ms · ${totalDocs} docs (${dps}/s)`;
  } catch (e) {
    toast(String(e.message || e), 'error');
  } finally {
    ui.disableActions(false);
  }
}

function updateFromFileIndex(idx) {
  const f = state.files[idx]; if (!f) return;
  const result = f.result.result_text || '';
  state.originalText = f.original || '';
  state.resultText = result;
  state.entities = withSamples(f.result.entities, f.result.original_len, f.original);
  state.labels = new Set(state.entities.map(e => e.label));
  els.deid.value = result;
  renderHighlightedOutput(f.original || '', result, state.entities);
  render.refreshFilters(); state.page = 1; render.entitiesTable();
}

function setActiveTab(idx) {
  if (!state.files[idx]) return;
  $$('.tab', els.tablist).forEach((t, i) => t.classList.toggle('active', i === idx));
  $$('.panel', els.panels).forEach((p, i) => p.classList.toggle('active', i === idx));
  updateFromFileIndex(idx);
  localStorage.setItem('activeTabFile', state.files[idx].name);
}

function removeTab(idx) {
  if (!state.files[idx]) return;
  state.files.splice(idx, 1);
  if (state.files.length === 0) {
    els.tabs.classList.add('hidden');
    els.tablist.innerHTML = ''; els.panels.innerHTML = '';
    localStorage.removeItem('activeTabFile');
    return;
  }
  const nextIdx = Math.max(0, idx - 1);
  localStorage.setItem('activeTabFile', state.files[nextIdx].name);
  render.fileTabs(state.files);
  setActiveTab(nextIdx);
}

// ─────────────────────────────────────────────────────────────
// Event wiring
// ─────────────────────────────────────────────────────────────
function bindEvents() {
  // Config hydrate
  const hasAuth = () => (!!localStorage.getItem('apiKey') || document.cookie.includes('X-API-Key='));
  if (hasAuth()) {
    api.getConfig()
      .then(cfg => { if (cfg?.default_policy) els.policy.value = cfg.default_policy; })
      .catch(() => {});
  } else {
    // Dev-friendly default so the UI can hit the API out of the box
    localStorage.setItem('apiKey', 'change-me');
  }
  els.policy.addEventListener('change', (e) => {
    api.putConfig({ default_policy: e.target.value }).catch(() => {});
    localStorage.setItem('policy', e.target.value);
  });

  // Buttons
  els.run.addEventListener('click', (e) => { e.preventDefault(); runDeidInline(); });
  els.clear.addEventListener('click', (e) => {
    e.preventDefault();
    els.original.value = '';
    els.deid.value = '';
    state.entities = []; state.resultText = ''; state.originalText = '';
    els.deidView.innerHTML = '<div class="ghost">Redacted output will appear here once you click <strong>Redact</strong>.</div>';
    render.entitiesTable(); ui.updateCharCount();
  });
  els.copy.addEventListener('click', ui.copyOutput);

  function activeDownloadName() {
    const stored = localStorage.getItem('activeTabFile');
    if (stored && stored.trim()) return `${stored}.redacted.txt`;
    return 'redacted.txt';
  }
  els.download.addEventListener('click', () => ui.downloadResult(activeDownloadName()));
  els.paste.addEventListener('click', async () => {
    const txt = await navigator.clipboard.readText().catch(() => null);
    if (txt) { els.original.value = txt; ui.updateCharCount(); }
  });
  els.original.addEventListener('input', ui.updateCharCount);

  // Sample loaders
  $$('.sample-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const key = btn.dataset.sample;
      if (SAMPLES[key]) {
        els.original.value = SAMPLES[key];
        ui.updateCharCount();
        toast(`Loaded sample: ${btn.textContent}`, 'success', 1800);
      }
    });
  });

  // Drag & drop
  ['dragenter', 'dragover'].forEach(ev => els.dropzone.addEventListener(ev, (e) => {
    e.preventDefault(); e.stopPropagation();
    els.dropzone.classList.add('dragover');
  }));
  ['dragleave', 'drop'].forEach(ev => els.dropzone.addEventListener(ev, (e) => {
    e.preventDefault(); e.stopPropagation();
    els.dropzone.classList.remove('dragover');
  }));
  els.dropzone.addEventListener('drop', (e) => {
    const files = Array.from(e.dataTransfer.files || []).filter(f => /\.txt$/i.test(f.name));
    if (files.length) runDeidFiles(files);
    else toast('Only .txt files supported', 'error');
  });
  els.upload.addEventListener('click', () => els.fileInput.click());
  els.fileInput.addEventListener('change', () => {
    const files = Array.from(els.fileInput.files || []);
    if (files.length) runDeidFiles(files);
  });

  // Entities filters
  [els.search, els.labelFilter, els.actionFilter, els.minLenRange, els.sortBy].forEach(el =>
    el.addEventListener('input', debounce(() => { state.page = 1; render.entitiesTable(); }, 250))
  );
  els.minLenRange.addEventListener('input', () => { els.minLenValue.textContent = els.minLenRange.value; });
  $('#clear-filters').addEventListener('click', () => {
    els.search.value = '';
    Array.from(els.labelFilter.options).forEach(o => o.selected = false);
    els.actionFilter.value = '';
    els.minLenRange.value = '0'; els.minLenValue.textContent = '0';
    els.sortBy.value = 'start';
    state.page = 1; render.entitiesTable();
  });
  els.prevPage.addEventListener('click', () => { state.page = Math.max(1, state.page - 1); render.entitiesTable(); });
  els.nextPage.addEventListener('click', () => { state.page = state.page + 1; render.entitiesTable(); });

  // Eval modal
  els.lastEvalLink.addEventListener('click', async (e) => {
    e.preventDefault();
    const m = await api.lastMetrics().catch(() => null);
    ui.showEvalModal(m);
  });
  els.evalClose.addEventListener('click', ui.closeEvalModal);
  els.evalModal.addEventListener('click', (e) => { if (e.target === els.evalModal) ui.closeEvalModal(); });

  // Shortcuts
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'enter') { e.preventDefault(); runDeidInline(); }
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k')     { e.preventDefault(); els.search.focus(); }
    if (e.key === 'Escape' && els.evalModal.open) ui.closeEvalModal();
  });
}

document.addEventListener('DOMContentLoaded', async () => {
  bindEvents();
  ui.updateCharCount();
  render.refreshFilters();
  try {
    const hasAuth = () => (!!localStorage.getItem('apiKey') || document.cookie.includes('X-API-Key='));
    if (hasAuth()) {
      const last = await api.lastMetrics();
      if (last) els.lastEvalLink.classList.remove('hidden');
    }
  } catch (e) { /* ignore */ }
});
