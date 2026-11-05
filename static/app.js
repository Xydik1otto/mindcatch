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
    if (el) el.textContent = `Сьогодні: ${d.tasks} задач, ${d.reminders} нагадувань`;
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

async function loadView() {
  const items = await api("/api/items?status=" + view);
  const el = $("list");
  if (!items.length) { el.innerHTML = "<p class='muted'>Порожньо.</p>"; return; }
  el.innerHTML = "";
  for (const it of items) {
    const div = document.createElement("div");
    div.className = "item";
    const statuses = ["inbox", "today", "week", "someday", "done"];
    div.innerHTML = `<div><div class="type">${it.type}${it.recurrence ? " · " + (it.recurrence === "daily" ? "щоденна" : "щотижнева") : ""}${it.estimate_minutes ? " · ⏱ " + (it.spent_minutes || 0) + "/" + it.estimate_minutes + " хв" : ""}${it.due_date ? " · 📅 " + it.due_date : ""}</div><div>${escapeHtml(it.text)}</div></div>`;
    const right = document.createElement("div");
    right.style.cssText = "display:flex;gap:6px;align-items:center";
    const rec = document.createElement("button");
    rec.className = "ghost"; rec.title = "Повторення: немає → щоденна → щотижнева";
    rec.textContent = "↻" + (it.recurrence === "daily" ? "1" : it.recurrence === "weekly" ? "7" : "");
    rec.onclick = async () => {
      const cycle = { "": "daily", "daily": "weekly", "weekly": "" };
      const next = cycle[it.recurrence || ""] ?? "daily";
      await api(`/api/items/${it.id}/recurrence`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ recurrence: next || null }) });
      loadView();
    };
    right.appendChild(rec);
    const tm = document.createElement("button");
    tm.className = "ghost"; tm.textContent = "⏱"; tm.title = "Таймер: старт/стоп (історія на задачі)";
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
    cb.className = "ghost"; cb.textContent = "✓"; cb.title = "Виконано (повторювані створять наступний раз)";
    cb.onclick = async () => { await api(`/api/items/${it.id}/complete`, { method: "POST" }); loadView(); };
    right.appendChild(cb);
    if (it.type === "note") {
      const nb = document.createElement("button");
      nb.className = "ghost"; nb.textContent = "📝"; nb.title = "Редагувати нотатку (markdown)";
      nb.onclick = () => openNoteEditor(it);
      right.appendChild(nb);
    }
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
$("noteBody").addEventListener("input", updateNotePreview);
document.addEventListener("keydown", e => {
  if (e.key === "Escape") { closeFocus(); closeNoteEditor(); return; }
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
checkReminders();
