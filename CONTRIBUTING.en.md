# Contributing to Mindcatch

Thanks for helping out! Mindcatch is a local-first, offline thought catcher
for people with ADHD: one input field, zero cloud, natural-language dates in
Ukrainian and English. This document explains how the project is built and
how to extend it without breaking things.

## Project structure / Architecture

**Backend: FastAPI + SQLite (single file, local-first forever).**

```
app/
  main.py        — FastAPI HTTP layer: /api/capture, /api/items, /api/today,
                   /api/search, /api/ocr, /api/export/... (thin: validate
                   request -> call logic -> JSON)
  db.py          — SQLite layer: SCHEMA, get_conn(), _migrate(), CRUD
  logic/         — pure functions, no I/O (easy to test)
    date_parser.py — natural-language dates UA/EN -> ParsedDate
                     (remind_at, due_date)
    ocr_extract.py — heuristics: raw text (screenshot/OCR) -> task
                     candidates (Tesseract is optional; plain text works
                     without it)
    triage.py      — state machine inbox -> today/week/someday/done
    focus_timer.py — focus sessions; focus_stats.py — statistics
    recurring.py   — recurrence: daily/weekly/weekdays/every N days;
                     completing an item spawns the next instance
    markdown.py    — safe note rendering (allow-listed tags only)
    digest.py, review.py, tags.py, ics_export.py, csv_export.py,
    task_export.py, time_tracker.py — other pure modules
  cli.py         — mindcatch console entry point
static/          — no-build frontend: index.html (inline CSS),
                   app.js (vanilla ES), i18n.json (UA/EN dictionaries),
                   manifest.json (PWA), favicon.svg
  sw.js          — service worker: offline-first. On install it precaches
                   the app shell: ["/", "index.html", "app.js", "i18n.json",
                   "manifest.json", "favicon.svg"] (the SHELL constant).
                   /api/* is NEVER cached — live data only. Pages:
                   network-first with a cache fallback; static assets:
                   cache-first + background refresh. When you change a
                   shell file, bump the cache version
                   (CACHE = "mindcatch-vN")!
```

Key principle: **logic lives in `app/logic/` as pure functions**, the HTTP
layer in `app/main.py` only glues things together, and data lives in
`app/db.py`. Tests call the logic modules directly, without a server.

## Branches

- **`main`** — the stable branch: OSS code, green pytest, documentation.
  Every push to `main` must pass the tests locally.
- **`mobile/android-ios`** — the mobile port (Capacitor 6 shell + native
  Android/iOS projects, CI builds of APK/.app). Developed in parallel;
  based on `main` + mobile commits. Details: [MOBILE.md](MOBILE.md).
  Merge fresh `main` into the branch regularly so divergence doesn't pile
  up.
- Do features on local branches, or directly on `main` (for small, fully
  tested changes) — the project is a one-person effort, branches are not
  mandatory, but keep commits atomic.

## Environment + tests

```bash
git clone https://github.com/bigpi/mindcatch.git
cd mindcatch
python -m pip install -r requirements.txt
python -m pytest tests/ -v        # everything must be green (297 now)
python -m uvicorn app.main:app --reload --port 8000
```

- Python 3.12+, stdlib-first, no heavy dependencies.
- The test database is set via the `MINDCATCH_DB` env variable (test
  fixtures create a temporary database themselves and clean it up between
  tests).
- No Node build: the frontend simply sits in `static/` and is served by
  FastAPI. Check JS syntax with `node --check static/app.js`.

## How to add a new date-parsing language

The parser (`app/logic/date_parser.py`) currently understands UA and EN:
relative days (сьогодні/завтра/післязавтра, today/tomorrow), weekdays
(«у пʼятницю», «next monday»), explicit dates (2026-11-10, 31.12,
31.12.2027, 5/06), time of day (15:00, «завтра о 9:30»), «наступного
тижня / next week». To add a third language (say, Polish):

1. **Weekday vocabulary.** Add `_WEEKDAY_PL = {...}` — word-form prefixes
   -> weekday number (0=Monday). Prefixes are intentionally short: they
   must cover grammatical cases («у пʼятницю» and «пʼятниця» share one
   prefix).
2. **Relative days.** Extend `_RELATIVE` with regexes for the new language
   (`dziś` -> 0, `jutro` -> 1, etc.). Order matters: longer phrases
   («післязавтра», «day after tomorrow») come before shorter ones
   («завтра»), otherwise the short one swallows the long one.
3. **Weekday regex.** Following the `_UA_WEEKDAY_RE` / `_EN_WEEKDAY_RE`
   pattern, add `_PL_WEEKDAY_RE` and a `_weekday_from_pl(word) -> int | None`
   function (modeled on `_weekday_from_ua`). Mind apostrophes —
   `_normalize()` already unifies `ʼ ' \` into `'`.
4. **Then in `parse()`.** Add an "if result_date is None" block with your
   regex **before** the "next week" fallback and **after** EN/UA — so
   explicit dates and already-supported languages keep priority.
5. **Time and date formats.** `_TIME_RE` and `_DMY_DATE_RE` are
   language-agnostic; if your language writes dates differently (m/d
   instead of d.m), add a separate regex and handling following the
   pattern of blocks 1–2 in `parse()`.
6. **Tests.** Create `tests/test_date_parser_pl.py` modeled on
   `tests/test_date_parser.py`: a constant `TODAY = date(2026, 11, 4)`
   (a Wednesday — determinism!), classes `TestRelativeDays`,
   `TestWeekdays`, `TestExplicitDates`, `TestTimeExtraction`,
   `TestNoFalsePositives`. Each test calls `parse(text, TODAY)` and
   compares `p.date` / `p.time`. **Required: a test that a phrase in the
   new language does NOT parse as a false-positive UA/EN match**, and a
   mid-text test («нагадай завтра о 09:05…»).
7. Update the module docstring (list of supported features) and
   `CHANGELOG.md`.

## How to add a field to items

SQLite here uses no Alembic — migrations are handwritten in
`app/db.py::_migrate()`. The pattern is simple and proven by tests
against "old" databases:

```python
def _migrate(conn: sqlite3.Connection) -> None:
    """Add columns introduced after the MVP schema to existing databases."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(items)").fetchall()}
    additions = {
        "due_date": "TEXT",
        "recurrence": "TEXT",
        "body": "TEXT",
        "estimate_minutes": "INTEGER",
        "tags": "TEXT",
        # "new_field": "TYPE",      <- 1. add it here
    }
    for name, decl in additions.items():
        if name not in cols:
            conn.execute(f"ALTER TABLE items ADD COLUMN {name} {decl}")
    conn.execute("CREATE TABLE IF NOT EXISTS time_logs (...)")
    conn.commit()
```

Why it works this way: `PRAGMA table_info(items)` gives the actual columns
of the current database; `ALTER TABLE ... ADD COLUMN` runs only for
missing ones — so the same database migrates repeatedly without pain, and
a fresh database created from `SCHEMA` simply skips the migrations.
`init_db()` always calls `_migrate()` after `executescript(SCHEMA)`.

Steps for a new field `foo TEXT`:

1. Add a line to `additions` in `_migrate()` (and, for a new **table**,
   a separate `CREATE TABLE IF NOT EXISTS` next to `time_logs`).
2. Update `SCHEMA` (a fresh database has the field right away) —
   initialization and migration must produce identical results.
3. CRUD: accept the parameter in `create_item()` / add support in
   `update_fields()` (it is generic — `**fields` already works) or write
   a narrow helper like `update_status()`.
4. An endpoint in `app/main.py` (PUT/PATCH on `/api/items/{id}/...` or a
   field in the create request) + business logic in `app/logic/` if there
   are rules.
5. Frontend: the field in the payload in `static/app.js` (if editable
   from the UI).
6. Test: create a temporary database **without** the new field (a manual
   reverse `ALTER TABLE`, or a sqlite fixture with the old SCHEMA), call
   `init_db()` and verify the column appears and no data is lost. Also an
   API-endpoint test via `TestClient`.

## i18n rules (critical)

- Every UI string goes through the `static/i18n.json` dictionaries only:
  `"ua"` and `"en"` sections, **identical keys in both**, and identical
  placeholders (`{n}`, `{q}`). No hardcoded strings in `static/app.js` or
  `index.html`.
- The service worker precaches `i18n.json` (it is in `SHELL` in `sw.js`),
  so the translation works offline. When adding keys, remember the cache
  version.
- **NEVER Russian.** Russian localization will not be accepted — the
  owner's policy decision, not up for discussion. This is enforced by
  test guards: `tests/test_i18n.py::test_no_russian_anywhere` (the guard
  scans the dictionaries for three letters unique to the Russian alphabet,
  absent from Ukrainian) and
  `tests/test_oss_hygiene.py::test_no_russian_in_any_community_file`
  (all doc files). Ukrainian text passes these guards, but re-read your
  text before committing: no Russian words or loanwords.
- UA values must be living Ukrainian (the guard checks «Сьогодні» with the
  Ukrainian «і»), EN must contain no Cyrillic at all.
- A new key = both languages in one commit; a test verifies
  `set(ua) == set(en)` and a minimum of 40 keys.

## Pull request process and commit style

1. Tests: `python -m pytest` — green; a new feature = a new test file or
   class.
2. One PR = one feature/fix (easy to review and to revert).
3. No private paths, tokens or real user data (CI/tests check this:
   `tests/test_docs.py::TestPrivacyHygiene`).
4. A11y: new buttons/inputs get an `aria-label`; visible focus state.
5. Update `CHANGELOG.md` and, if needed, `README.md` + `README.en.md`.
6. Commit message (Conventional Commits, short and to the point):
   - `feat(scope): ...` — new functionality
   - `fix(scope): ...` — a fix
   - `docs: ...` / `ci: ...` / `mobile: ...` / `chore: ...`
   - scope — the area: `(date_parser)`, `(i18n)`, `(db)`, `(pwa)`…
   - examples from history: `feat(packaging): pyproject.toml 1.0.0...`,
     `fix(oss): secret scanner excludes its own pattern literals`
7. PR description: what and why + how you verified it (the pytest command,
   a manual scenario).

## Mobile port

The mobile apps are a **thin shell (Capacitor 6) that connects to YOUR OWN
server**: the UI is not embedded in the app, the server address is entered
on the splash screen at first launch, verified with `GET /api/tags`, and
stored natively (Preferences). Data never leaves your server.
The full guide (Android sideload, AltStore for iOS, Tailscale, local
build) is in **[MOBILE.md](MOBILE.md)**. CI builds:
`.github/workflows/android-build.yml` (debug APK) and `ios-build.yml`
(unsigned .app). Make frontend changes in `static/` — the mobile shell
displays exactly that.

## Reporting bugs

Use the
[.github/ISSUE_TEMPLATE/bug_report.md](.github/ISSUE_TEMPLATE/bug_report.md)
template. For security, see [SECURITY.md](SECURITY.md) — privately, not in
a public issue.

## Code style

- Python: stdlib-first, type hints, docstrings short and to the point.
- JS: no bundlers or frameworks — vanilla ES, `node --check static/app.js`.
- CSS: in `index.html`, dark theme via CSS variables.

## License

By contributing you agree your work is licensed under MIT together with
the project.
