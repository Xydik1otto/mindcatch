"use strict";
// Mindcatch PWA frontend. Keyboard-first: N = focus capture, T = today view,
// F = focus mode, E = export, Esc = close focus.

const $ = id => document.getElementById(id);
let view = "inbox";
let tagFilter = "";   // active tag chip ("" = all)
let editingTags = null; // item id whose inline tag editor is open
let focusTimer = null;
let focusItem = null;
let focusState = null; // {phase, remaining, running}

// --- i18n: UA/EN dictionaries (/i18n.json), browser auto-detect, persisted ---
const LANG_KEY = "mc_lang";
let LANG = localStorage.getItem(LANG_KEY) ||
  ((navigator.language || "").toLowerCase().startsWith("uk") ? "ua" : "en");
let DICT = { ua: {}, en: {} };

function t(key, vars) {
  let s = (DICT[LANG] && DICT[LANG][key]) ?? DICT.ua[key] ?? key;
  if (vars) for (const k of Object.keys(vars)) s = s.split("{" + k + "}").join(String(vars[k]));
  return s;
}

function applyStatic() {
  document.documentElement.lang = LANG === "ua" ? "uk" : "en";
  $("subline").innerHTML = t("sub");
  $("captureInput").placeholder = t("capture_ph");
  $("searchInput").placeholder = t("search_ph");
  const ib = $("installBtn"); if (ib) ib.textContent = t("install");
  $("dropzone").textContent = t("dropzone");
  $("noteSave").textContent = t("save");
  $("noteClose").textContent = t("close");
  const lb = $("langBtn");
  if (lb) { lb.textContent = LANG === "ua" ? "EN" : "UA"; lb.setAttribute("aria-label", t("lang_btn_aria")); }
}

async function loadI18n() {
  try { DICT = await (await fetch("/i18n.json")).json(); }
  catch (e) { /* offline first paint: HTML keeps Ukrainian defaults */ }
  if (!DICT[LANG]) LANG = "ua";
  applyStatic();
}

function setLang(lang) {
  if (!DICT[lang]) return;
  LANG = lang;
  localStorage.setItem(LANG_KEY, LANG);
  applyStatic();
  loadView(); // re-render dynamic strings in the new language
}

async function api(path, opts) {
  const r = await fetch(path, opts);
  if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || r.statusText); }
  return r.json();
}

async function doCapture() {
  const text = $("captureInput").value.trim();
  if (!text) return;
  await api("/api/capture", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) });
  $("captureInput").value = "";
  loadView();
  ensureNotificationPermission(); // ask once, on the first capture gesture
}

// --- Local web notifications (reminders due today) ---
let notifiedToday = new Set(JSON.parse(localStorage.getItem("notifiedIds") || "[]"));
let notifiedDay = localStorage.getItem("notifiedDay") || "";

function ensureNotificationPermission() {
  if (!("Notification" in window) || Notification.permission === "default") {
    try { Notification.requestPermission(); } catch (e) { /* Safari */ }
  }
}

function notify(body) {
  if (!("Notification" in window) || Notification.permission !== "granted") return;
  try { new Notification("Mindcatch", { body }); } catch (e) {}
}

async function checkReminders() {
  try {
    const d = await api("/api/digest");
    // digest line
    const el = $("digest");
    if (el) el.textContent = t("digest", { tasks: d.tasks, reminders: d.reminders });
    // reset the notified set on a new day
    if (notifiedDay !== d.date) { notifiedDay = d.date; notifiedToday = new Set(); }
    for (const it of d.due_today) {
      if (notifiedToday.has(it.id)) continue;
      notifiedToday.add(it.id);
      notify(it.text);
    }
    localStorage.setItem("notifiedIds", JSON.stringify([...notifiedToday]));
    localStorage.setItem("notifiedDay", notifiedDay);
  } catch (e) { /* offline: SW shell still works */ }
}

setInterval(checkReminders, 60 * 1000);
document.addEventListener("visibilitychange", () => { if (!document.hidden) checkReminders(); });

// --- Tags: filter chips + history hints + inline editor ---
async function loadTagChips() {
  const sug = await api("/api/tags").catch(() => []);
  const box = $("tagChips"), dl = $("tagDatalist");
  box.innerHTML = ""; dl.innerHTML = "";
  const mk = (label, tag, active) => {
    const c = document.createElement("button");
    c.className = "chip" + (active ? " active" : "");
    c.textContent = label;
    c.onclick = () => { tagFilter = active ? "" : tag; loadView(); };
    box.appendChild(c);
  };
  mk(t("tag_all"), "", !tagFilter);
  for (const s of sug) {
    mk(`#${s.tag} (${s.count})`, s.tag, tagFilter === s.tag);
    const o = document.createElement("option"); o.value = s.tag; dl.appendChild(o);
  }
  box.style.display = sug.length ? "flex" : "none";
}

function tagList(item) { return (item.tags || "").split(",").filter(Boolean); }

async function loadView() {
  if (view === "review") return loadReview();
  if (view === "stats") return loadStats();
  await loadTagChips();
  const tagQ = tagFilter ? "&tag=" + encodeURIComponent(tagFilter) : "";
  const items = await api("/api/items?status=" + view + tagQ);
  const el = $("list");
  el.innerHTML = "";
  if (!items.length) { el.innerHTML = `<p class='muted'>${t("empty")}</p>`; return; }
  renderItems(items, el);
}

function renderItems(items, el) {
  for (const it of items) {
    const div = document.createElement("div");
    div.className = "item";
    const statuses = ["inbox", "today", "week", "someday", "done"];
    div.innerHTML = `<div><div class="type">${it.type}${it.recurrence ? " · " + recName(it.recurrence) : ""}${it.estimate_minutes ? " · ⏱ " + (it.spent_minutes || 0) + "/" + it.estimate_minutes + " " + t("min_short") : ""}${it.due_date ? " · 📅 " + it.due_date : ""}${tagList(it).length ? " · " + tagList(it).map(t2 => "#" + escapeHtml(t2)).join(" ") : ""}</div><div>${escapeHtml(it.text)}</div></div>`;
    const right = document.createElement("div");
    right.style.cssText = "display:flex;gap:6px;align-items:center";
    const rec = document.createElement("button");
    rec.className = "ghost"; rec.title = t("rec_btn_title");
    rec.textContent = "↻" + recLabel(it.recurrence);
    rec.setAttribute("aria-label", t("rec_btn_title"));
    rec.onclick = async () => {
      const cycle = { "": "daily", "daily": "weekly", "weekly": "weekdays", "weekdays": "every" };
      let next = cycle[it.recurrence || ""] ?? "";
      if (next === "every") {
        const n = parseInt(prompt(t("rec_prompt"), "3"), 10);
        if (!n || n < 2 || n > 365) return;
        next = "every:" + n;
      }
      await api(`/api/items/${it.id}/recurrence`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ recurrence: next || null }) });
      loadView();
    };
    right.appendChild(rec);
    const tm = document.createElement("button");
    tm.className = "ghost"; tm.textContent = "⏱"; tm.title = t("timer_title");
    tm.onclick = async () => {
      try {
        const r = await api(`/api/items/${it.id}/timer/${tm.dataset.running ? "stop" : "start"}`, { method: "POST" });
        loadView();
      } catch (e) { alert(e.message); }
    };
    tm.dataset.running = it.timer_running ? "1" : "";
    if (it.timer_running) tm.style.color = "var(--accent)";
    right.appendChild(tm);
    const cb = document.createElement("button");
    cb.className = "ghost"; cb.textContent = "✓"; cb.title = t("done_title");
    cb.onclick = async () => { await api(`/api/items/${it.id}/complete`, { method: "POST" }); loadView(); };
    right.appendChild(cb);
    if (it.type === "note") {
      const nb = document.createElement("button");
      nb.className = "ghost"; nb.textContent = "📝"; nb.title = t("note_btn_title");
      nb.onclick = () => openNoteEditor(it);
      right.appendChild(nb);
    }
    const tb = document.createElement("button");
    tb.className = "ghost"; tb.textContent = "🏷"; tb.title = t("tags_title");
    tb.onclick = () => { editingTags = editingTags === it.id ? null : it.id; loadView(); };
    right.appendChild(tb);
    const sel = document.createElement("select");
    for (const s of statuses) {
      const o = document.createElement("option"); o.value = s; o.textContent = s;
      if (s === it.status) o.selected = true; sel.appendChild(o);
    }
    sel.onchange = async () => {
      try {
        if (sel.value === "done" && it.status !== "done" && !confirm(t("archive_confirm"))) { sel.value = it.status; return; }
        await api(`/api/items/${it.id}/move`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status: sel.value }) }); loadView(); }
      catch (e) { alert(e.message); sel.value = it.status; }
    };
    right.appendChild(sel);
    if (it.status === "today") {
      const fb = document.createElement("button"); fb.className = "ghost"; fb.textContent = "▶"; fb.title = "Focus (pomodoro)";
      fb.onclick = () => openFocus(it); right.appendChild(fb);
    }
    div.appendChild(right);
    if (editingTags === it.id) {
      div.style.flexWrap = "wrap";
      const ed = document.createElement("div");
      ed.className = "tagedit";
      ed.innerHTML = `<input id="tagInput" list="tagDatalist" placeholder="${t("tags_ph")}" value="${escapeHtml(it.tags || "")}">`;
      const save = document.createElement("button"); save.textContent = "OK"; save.title = "Зберегти теги";
      save.onclick = async () => {
        await api(`/api/items/${it.id}/tags`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tags: $("tagInput").value }) });
        editingTags = null; loadView();
      };
      const cancel = document.createElement("button"); cancel.className = "ghost"; cancel.textContent = "✕";
      cancel.onclick = () => { editingTags = null; loadView(); };
      ed.appendChild(save); ed.appendChild(cancel);
      div.appendChild(ed);
    }
    el.appendChild(div);
  }
}

function escapeHtml(s) { const d = document.createElement("div"); d.textContent = s; return d.innerHTML; }

// Recurrence labels: short badge on the ↻ button + full label on the item line
function recLabel(r) {
  if (r === "daily") return t("rec_b_daily");
  if (r === "weekly") return t("rec_b_weekly");
  if (r === "weekdays") return t("rec_b_weekdays");
  if (r && r.startsWith("every:")) return t("rec_b_every", { n: r.slice(6) });
  return "";
}
function recName(r) {
  if (r === "daily") return t("rec_daily");
  if (r === "weekly") return t("rec_weekly");
  if (r === "weekdays") return t("rec_weekdays");
  if (r && r.startsWith("every:")) return t("rec_every", { n: r.slice(6) });
  return r;
}

// --- Weekly review view ---
async function loadReview() {
  const r = await api("/api/review/weekly");
  const el = $("list");
  el.innerHTML = `
    <p class="muted">${t("review_summary", { week_start: r.week_start, today: r.today, done: r.counts.done, carried: r.counts.carried, created: r.counts.created_this_week })}</p>
    <h3 style="margin:10px 0 6px">${t("review_done", { n: r.counts.done })}</h3>
    <div id="reviewDone"></div>
    <h3 style="margin:10px 0 6px">${t("review_carried", { n: r.counts.carried })}</h3>
    <div id="reviewCarried"></div>`;
  const fill = (container, arr) => {
    const box = $(container);
    if (!arr.length) { box.innerHTML = `<p class='muted'>${t("empty")}</p>`; return; }
    for (const it of arr) {
      const div = document.createElement("div");
      div.className = "item";
      div.innerHTML = `<div><div class="type">${it.type}</div><div>${escapeHtml(it.text)}</div></div>`;
      box.appendChild(div);
    }
  };
  fill("reviewDone", r.done_this_week);
  fill("reviewCarried", r.carried_over);
}

document.querySelectorAll("nav button").forEach(b => b.onclick = () => {
  document.querySelectorAll("nav button").forEach(x => x.classList.remove("active"));
  b.classList.add("active"); view = b.dataset.view;
  $("searchInput").value = "";
  loadView();
});

// --- Search (server-side LIKE over text+body, archive included) ---
let searchTimer = null;
$("searchInput").addEventListener("input", e => {
  clearTimeout(searchTimer);
  const q = e.target.value.trim();
  searchTimer = setTimeout(() => {
    if (!q) { view = "inbox"; setActiveNav("inbox"); loadView(); return; }
    loadSearch(q);
  }, 250);
});

function setActiveNav(name) {
  document.querySelectorAll("nav button").forEach(x => x.classList.toggle("active", x.dataset.view === name));
}

async function loadSearch(q) {
  view = "search"; setActiveNav("");
  $("tagChips").style.display = "none";
  const items = await api("/api/search?q=" + encodeURIComponent(q));
  const el = $("list");
  if (!items.length) { el.innerHTML = `<p class='muted'>${t("nothing")}</p>`; return; }
  el.innerHTML = `<p class="muted">${t("found", { n: items.length, q: escapeHtml(q) })}</p>`;
  renderItems(items, el);
}

// --- Focus statistics (SVG bar chart from /api/stats/focus) ---
async function loadStats() {
  $("tagChips").style.display = "none";
  const s = await api("/api/stats/focus?days=7");
  const h = Math.round(s.total_minutes / 60);
  $("list").innerHTML =
    `<h3 style="margin:6px 0 10px">${t("stats_head", { minutes: s.total_minutes })}${h ? " " + t("stats_hours", { hours: h }) : ""}</h3>` +
    s.svg +
    `<p class="muted" style="margin-top:8px">${t("stats_note")}</p>`;
}

// --- Focus mode (pomodoro 25/5) ---
async function openFocus(item) {
  focusItem = item;
  $("focusTask").textContent = item.text;
  $("focus").classList.remove("hidden");
  focusState = { phase: "work", remaining: 25 * 60, running: true };
  updateFocusUI();
  clearInterval(focusTimer);
  focusTimer = setInterval(focusTick, 1000);
}

function focusTick() {
  if (focusState.running) {
    focusState.remaining--;
    if (focusState.remaining <= 0) {
      // phase finished: work -> break, break -> work (simple client mirror of the backend logic)
      if (focusState.phase === "work") { focusState.phase = "short_break"; focusState.remaining = 5 * 60; }
      else { focusState.phase = "work"; focusState.remaining = 25 * 60; }
    }
    updateFocusUI();
  }
}

function updateFocusUI() {
  const m = Math.floor(focusState.remaining / 60), s = focusState.remaining % 60;
  $("focusTimer").textContent = `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}` + (focusState.phase === "work" ? "" : " ☕");
  $("focusBtn").textContent = focusState.running ? t("pause") : t("resume");
}

function focusAction() {
  focusState.running = !focusState.running;
  updateFocusUI();
}

function closeFocus() {
  clearInterval(focusTimer); focusTimer = null;
  $("focus").classList.add("hidden"); focusItem = null; focusState = null;
}

// --- Note editor (markdown body + live preview) ---
let noteItem = null;
let notePreviewTimer = null;

function openNoteEditor(item) {
  noteItem = item;
  $("noteTitle").textContent = item.text;
  $("noteBody").value = item.body || "";
  $("noteEditor").classList.remove("hidden");
  updateNotePreview();
}

function closeNoteEditor() {
  $("noteEditor").classList.add("hidden");
  noteItem = null;
}

async function saveNoteBody() {
  if (!noteItem) return;
  await api(`/api/items/${noteItem.id}/body`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ body: $("noteBody").value }) });
  closeNoteEditor();
  loadView();
}

function updateNotePreview() {
  clearTimeout(notePreviewTimer);
  notePreviewTimer = setTimeout(async () => {
    const r = await api("/api/md/preview", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ body: $("noteBody").value }) });
    $("notePreview").innerHTML = r.html || "<span class='muted'>—</span>";
  }, 300);
}

// --- Onboarding tour: 3 tips on the first visit (localStorage) ---
const TOUR_KEY = "mc_tour_done";
const TOUR_STEPS = [
  { sel: "#captureInput", title: "tour1_title", text: "tour1_text" },
  { sel: "nav", title: "tour2_title", text: "tour2_text" },
  { sel: ".sub", title: "tour3_title", text: "tour3_text" },
];
let tourIdx = 0;

function tourShow() {
  const step = TOUR_STEPS[tourIdx];
  document.querySelectorAll(".tour-hl").forEach(el => el.classList.remove("tour-hl"));
  const target = document.querySelector(step.sel);
  if (target) target.classList.add("tour-hl");
  $("tourStep").textContent = t("tour_step", { n: tourIdx + 1, total: TOUR_STEPS.length });
  $("tourTitle").textContent = t(step.title);
  $("tourText").textContent = t(step.text);
  $("tourNext").textContent = tourIdx === TOUR_STEPS.length - 1 ? t("tour_finish") : t("tour_next");
  $("tourSkip").textContent = t("tour_skip");
  $("tour").classList.remove("hidden");
  $("tourNext").focus();
}

function tourEnd(done) {
  document.querySelectorAll(".tour-hl").forEach(el => el.classList.remove("tour-hl"));
  $("tour").classList.add("hidden");
  if (done) localStorage.setItem(TOUR_KEY, "1");
  $("captureInput").focus();
}

function maybeStartTour() {
  if (!localStorage.getItem(TOUR_KEY)) { tourIdx = 0; tourShow(); }
}
$("tourNext").onclick = () => { tourIdx += 1; tourIdx < TOUR_STEPS.length ? tourShow() : tourEnd(true); };
$("tourSkip").onclick = () => tourEnd(true);

// --- PWA install prompt ---
let deferredInstall = null;
window.addEventListener("beforeinstallprompt", e => {
  e.preventDefault();              // keep our own button instead of the mini-infobar
  deferredInstall = e;
  const b = $("installBtn"); if (b) b.style.display = "";
});
window.addEventListener("appinstalled", () => {
  deferredInstall = null;
  const b = $("installBtn"); if (b) b.style.display = "none";
});
async function installApp() {
  if (!deferredInstall) return;
  deferredInstall.prompt();
  await deferredInstall.userChoice; // {outcome: "accepted"|"dismissed"}
  deferredInstall = null;
  $("installBtn").style.display = "none";
}

// --- OCR dropzone ---
const dz = $("dropzone");
["dragover", "dragenter"].forEach(ev => dz.addEventListener(ev, e => { e.preventDefault(); dz.classList.add("over"); }));
["dragleave", "drop"].forEach(ev => dz.addEventListener(ev, e => { e.preventDefault(); dz.classList.remove("over"); }));
dz.addEventListener("drop", async e => {
  const f = e.dataTransfer.files[0]; if (!f) return;
  dz.textContent = t("dropzone_busy");
  const fd = new FormData(); fd.append("file", f);
  const res = await api("/api/ocr", { method: "POST", body: fd });
  if (!res.ocr_available) { dz.textContent = t("ocr_fallback"); return; }
  dz.textContent = t("dropzone_found", { n: res.candidates.length });
  for (const c of res.candidates.slice(0, 10)) {
    const div = document.createElement("div"); div.className = "item";
    div.innerHTML = `<div><div class="type">candidate · score ${c.score}</div><div>${escapeHtml(c.text)}</div></div>`;
    const btn = document.createElement("button"); btn.textContent = "+ Inbox";
    btn.onclick = async () => { await api("/api/capture", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: c.text }) }); div.remove(); loadView(); };
    div.appendChild(btn); $("list").appendChild(div);
  }
});

// --- Hotkeys ---
$("noteBody").addEventListener("input", updateNotePreview);
document.addEventListener("keydown", e => {
  if (e.key === "Escape") {
    if (!$("tour").classList.contains("hidden")) { tourEnd(true); return; }
    closeFocus(); closeNoteEditor(); return;
  }
  const typing = document.activeElement && document.activeElement.tagName === "INPUT";
  if (e.key === "Enter" && document.activeElement === $("captureInput")) { doCapture(); return; }
  if (typing) return;
  if (e.key === "n" || e.key === "N") { $("captureInput").focus(); e.preventDefault(); }
  else if (e.key === "t" || e.key === "T") { document.querySelector("nav button[data-view=today]").click(); }
  else if (e.key === "f" || e.key === "F") {
    const first = document.querySelector("#list .item");
    if (first && view === "today") { /* open focus on first item */ }
    else alert(t("focus_alert"));
  }
  else if (e.key === "e" || e.key === "E") { location.href = "/api/export"; }
  else if (e.key === "l" || e.key === "L") { setLang(LANG === "ua" ? "en" : "ua"); }
});

// --- Service worker registration (offline shell) ---
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => { /* file:// or SW unsupported */ });
  });
}

$("langBtn").onclick = () => setLang(LANG === "ua" ? "en" : "ua");

(async function init() {
  await loadI18n();
  loadView();
  checkReminders();
  maybeStartTour();
})();
