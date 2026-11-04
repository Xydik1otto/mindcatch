"use strict";
// Mindcatch PWA frontend. Keyboard-first: N = focus capture, T = today view,
// F = focus mode, E = export, Esc = close focus.

const $ = id => document.getElementById(id);
let view = "inbox";
let focusTimer = null;
let focusItem = null;
let focusState = null; // {phase, remaining, running}

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
}

async function loadView() {
  const items = await api("/api/items?status=" + view);
  const el = $("list");
  if (!items.length) { el.innerHTML = "<p class='muted'>Порожньо.</p>"; return; }
  el.innerHTML = "";
  for (const it of items) {
    const div = document.createElement("div");
    div.className = "item";
    const statuses = ["inbox", "today", "week", "someday", "done"];
    div.innerHTML = `<div><div class="type">${it.type}</div><div>${escapeHtml(it.text)}</div></div>`;
    const right = document.createElement("div");
    right.style.cssText = "display:flex;gap:6px;align-items:center";
    const sel = document.createElement("select");
    for (const s of statuses) {
      const o = document.createElement("option"); o.value = s; o.textContent = s;
      if (s === it.status) o.selected = true; sel.appendChild(o);
    }
    sel.onchange = async () => {
      try { await api(`/api/items/${it.id}/move`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status: sel.value }) }); loadView(); }
      catch (e) { alert(e.message); sel.value = it.status; }
    };
    right.appendChild(sel);
    if (it.status === "today") {
      const fb = document.createElement("button"); fb.className = "ghost"; fb.textContent = "▶"; fb.title = "Focus (pomodoro)";
      fb.onclick = () => openFocus(it); right.appendChild(fb);
    }
    div.appendChild(right);
    el.appendChild(div);
  }
}

function escapeHtml(s) { const d = document.createElement("div"); d.textContent = s; return d.innerHTML; }

document.querySelectorAll("nav button").forEach(b => b.onclick = () => {
  document.querySelectorAll("nav button").forEach(x => x.classList.remove("active"));
  b.classList.add("active"); view = b.dataset.view; loadView();
});

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
  $("focusBtn").textContent = focusState.running ? "Пауза" : "Продовжити";
}

function focusAction() {
  focusState.running = !focusState.running;
  updateFocusUI();
}

function closeFocus() {
  clearInterval(focusTimer); focusTimer = null;
  $("focus").classList.add("hidden"); focusItem = null; focusState = null;
}

// --- OCR dropzone ---
const dz = $("dropzone");
["dragover", "dragenter"].forEach(ev => dz.addEventListener(ev, e => { e.preventDefault(); dz.classList.add("over"); }));
["dragleave", "drop"].forEach(ev => dz.addEventListener(ev, e => { e.preventDefault(); dz.classList.remove("over"); }));
dz.addEventListener("drop", async e => {
  const f = e.dataTransfer.files[0]; if (!f) return;
  dz.textContent = "Обробка…";
  const fd = new FormData(); fd.append("file", f);
  const res = await api("/api/ocr", { method: "POST", body: fd });
  if (!res.ocr_available) { dz.textContent = res.message + " (Перетягніть скріншот або введіть текст вручну)"; return; }
  dz.textContent = `Знайдено ${res.candidates.length} кандидатів`;
  for (const c of res.candidates.slice(0, 10)) {
    const div = document.createElement("div"); div.className = "item";
    div.innerHTML = `<div><div class="type">candidate · score ${c.score}</div><div>${escapeHtml(c.text)}</div></div>`;
    const btn = document.createElement("button"); btn.textContent = "+ Inbox";
    btn.onclick = async () => { await api("/api/capture", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: c.text }) }); div.remove(); loadView(); };
    div.appendChild(btn); $("list").appendChild(div);
  }
});

// --- Hotkeys ---
document.addEventListener("keydown", e => {
  if (e.key === "Escape") { closeFocus(); return; }
  const typing = document.activeElement && document.activeElement.tagName === "INPUT";
  if (e.key === "Enter" && document.activeElement === $("captureInput")) { doCapture(); return; }
  if (typing) return;
  if (e.key === "n" || e.key === "N") { $("captureInput").focus(); e.preventDefault(); }
  else if (e.key === "t" || e.key === "T") { document.querySelector("nav button[data-view=today]").click(); }
  else if (e.key === "f" || e.key === "F") {
    const first = document.querySelector("#list .item");
    if (first && view === "today") { /* open focus on first item */ }
    else alert("Focus доступний для задач у Today");
  }
  else if (e.key === "e" || e.key === "E") { location.href = "/api/export"; }
});

loadView();
