# Mindcatch — ADHD Mental-Load Capture

![CI](https://github.com/bigpi/mindcatch/actions/workflows/tests.yml/badge.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Version](https://img.shields.io/badge/version-1.0.0-purple.svg)

Offline-first thought catcher: one big field → a task, zero friction.

> Ukrainian interface? See [README.md](README.md) (the app itself has a UA/EN switch — press <kbd>L</kbd>).

## Why it exists

- A post on r/ADHD: *"app that would take the mental load of having to remember everything"* — **2,411 upvotes, 205 comments**. People with ADHD drown in "keeping everything in their head": any app with forms, fields and settings adds load instead of removing it.
- r/ProductivityApps requests for **combining calendar + tasks + notes** in one place.
- **Subscription fatigue**: users are tired of monthly subscriptions to "cloud productivity" — they want a **one-time purchase, local-first** tool.

## What it does

- **Fast capture**: the main screen is one big field + Enter → item in the inbox (GTD-style).
- Types are auto-classified: **task** (action verb), **reminder** (date/time in the text), **note** (everything else).
- **Date parsing (UA + EN)**: "завтра", "післязавтра", "у пʼятницю", "next monday", "tomorrow 15:00", "2026-11-10", "31.12" → automatically fill `remind_at` / `due_date`.
- **Local reminders**: Web Notification API — permission is requested at the first capture; reminders for the current day show while the tab is open.
- **Daily digest**: "Today: N tasks, M reminders" on the Today view.
- **Screenshot import**: drag & drop an image → if Tesseract (`pytesseract`) is installed, OCR → heuristics extract task-like lines → candidates to confirm with one click. **Without Tesseract — graceful fallback to manual input** (`ocr_available: false`).
- **Triage**: inbox → drag (select) into Today / Week / Someday / Done.
- **Tags/projects**: `#hashtags` in a capture attach automatically; 🏷 on an item opens an editor with history hints; filter chips above the list (`?tag=`, `GET /api/tags`).
- **Search + archive**: the search field does a substring search over title and body (case-insensitive, Cyrillic included) across all statuses; `/api/archive` — completed items, newest first.
- **Focus statistics**: the Stats tab — an SVG bar chart of pomodoro/timer minutes over 7 days (`/api/stats/focus`).
- **Quick capture API**: `POST /api/quick {text}` — capture from curl/launchers without UI (see below).
- **Today view + focus mode**: one task, pomodoro timer 25/5 min (long break 15 min after every 4).
- **Recurring tasks**: "↻" on a task cycles none → daily → weekly → weekdays-only → every N days; "✓" completes the task and immediately spawns the next occurrence in the inbox (shifting `remind_at`/`due_date`).
- **ICS calendar export**: `/api/export/calendar.ics` — every dated item becomes an event (all-day for `due_date`, timed for `remind_at`) with RFC 5545 RRULEs; import into Google Calendar, Outlook, Apple Calendar.
- **Markdown / Todoist export**: `/api/export/todoist.md` — a flat checklist that pastes straight into Todoist (`@labels`, `p1`–`p4` priorities, 📅 due dates); `/api/export/markdown` — the full export grouped by status.
- **CSV export**: `/api/export/items.csv` — UTF-8 with BOM, opens in Excel/Sheets.
- **Notes with markdown**: "📝" on a note → editor with live preview (safe minimal render: headings, **bold**, `code`, lists, http(s)-only links).
- **Time estimates + timer**: "⏱" start/stop on a task; session history (`time_logs`), spent vs estimated ("⏱ 12/45 min").
- **Weekly review**: the Review tab — what was done this week (since Monday), what carried over, how much was created.
- **Onboarding tour**: 3 tips on the first visit (capture, triage, exports), remembered in localStorage.
- **i18n**: UA/EN switch in the header (or press <kbd>L</kbd>); auto-detected from the browser language; your choice persists.
- **Data**: SQLite locally; one-click export to JSON / CSV / ICS / Todoist / Markdown. PWA manifest + service worker (offline shell).

## Quick start

```bash
git clone https://github.com/bigpi/mindcatch.git
cd mindcatch
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
# open http://localhost:8000
```

Or with packaging: `pip install -e .` then run the `mindcatch` command.
Step-by-step instructions for non-programmers: [INSTALL.md](INSTALL.md).

Tests:

```bash
python -m pytest tests/ -v
bash scripts/smoke.sh   # smoke: boots a server on a random port, checks the main endpoints
```

## Quick capture from the command line

The server accepts thoughts without UI — `POST /api/quick`, handy for curl, Alfred/Raycast-style launchers and shortcuts:

```bash
curl -s http://localhost:8000/api/quick \
  -H 'Content-Type: application/json' \
  -d '{"text":"call mom tomorrow 15:00 #family"}'
```

Example alias (add to `~/.bashrc` or PowerShell `$PROFILE`):

```bash
mc() { curl -s http://localhost:8000/api/quick -H 'Content-Type: application/json' -d "{\"text\":\"$*\"}"; }
# now in a terminal:  mc call the bank tomorrow #finance
```

Dates parse the same way as in the UI ("tomorrow", "next monday", "31.12"); `#tags` attach automatically.

OCR (optional): install Tesseract (https://github.com/UB-Mannheim/tesseract/wiki) and `pip install pytesseract pillow` — screenshot import starts working on its own; without it — manual input.

## Install as a PWA

1. Open `http://localhost:8000` in Chrome/Edge.
2. Address bar → "Install" icon (or ⋮ menu → "Install Mindcatch").
3. The app opens in its own window and works offline (the service worker caches the shell; data lives in a local SQLite file).

On Android: Chrome → menu → "Add to Home screen".

## Keyboard shortcuts

| Key | Action |
|---|---|
| <kbd>N</kbd> | focus the capture field |
| <kbd>Enter</kbd> | save the capture |
| <kbd>T</kbd> | Today view |
| <kbd>F</kbd> | focus mode (for tasks in Today) |
| <kbd>E</kbd> | export JSON |
| <kbd>L</kbd> | switch UA/EN |
| <kbd>Esc</kbd> | close focus / note editor / tour |

## Contributing

PRs and issues are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for the
workflow (tests required for every feature, `pytest` must stay green).
Found a security issue? See [SECURITY.md](SECURITY.md) — please use private
reporting, not a public issue.

This project deliberately ships **Ukrainian and English only** — no Russian
localization will be accepted (owner's policy decision).

## Structure

```
mindcatch/
├── app/
│   ├── main.py            # FastAPI: /api/capture, /api/quick, /api/search, /api/export/*
│   ├── db.py              # SQLite (stdlib sqlite3, WAL) + migrations
│   └── logic/
│       ├── date_parser.py # UA+EN dates → remind_at / due_date
│       ├── ics_export.py  # RFC 5545 calendar export
│       ├── task_export.py # Markdown / Todoist checklist
│       ├── csv_export.py  # CSV with UTF-8 BOM
│       ├── recurring.py   # daily/weekly/every:N/weekdays spawn logic
│       ├── digest.py      # "Today: N tasks, M reminders"
│       ├── ocr_extract.py # task heuristics + optional pytesseract
│       ├── triage.py      # inbox/today/week/someday/done state machine
│       └── focus_timer.py # pomodoro 25/5/15, injected clock
├── static/                # PWA frontend (index.html, app.js, sw.js, i18n.json)
├── tests/                 # pytest: pure logic + API (TestClient)
└── .github/workflows/     # CI: pytest on Python 3.12/3.13
```

## Roadmap

- ~~v0.1 (alpha)~~: capture, date parsing, local reminders, digest, triage, focus pomodoro, JSON export.
- ~~v0.3~~: recurring tasks, markdown notes, time estimates + timer, weekly review.
- ~~v0.4~~: tags/projects + filter chips, quick-capture API, search + archive, focus statistics, PWA install + offline shell.
- ~~v1.0 (current)~~: ICS calendar export, every-N-days & weekdays-only recurrence, Todoist/Markdown export, onboarding tour, UA/EN switcher, INSTALL.md + packaging, a11y pass.
- **Next**: morning-ramp templates, Windows exe installer (see PLAN.md).

## License

MIT — see [LICENSE](LICENSE).
