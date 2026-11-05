# Contributing to Mindcatch

Дякуємо, що хочете допомогти! Mindcatch — локальний, offline-first
«виловлювач думок» для людей з ADHD: одне поле вводу, нуль хмари,
натуральні дати українською і англійською. Цей документ пояснює, як проєкт
влаштований, і як його розвивати без поломок.

## Як влаштований проєкт / Архітектура

**Backend: FastAPI + SQLite (один файл, local-first назавжди).**

```
app/
  main.py        — HTTP-слой FastAPI: /api/capture, /api/items, /api/today,
                   /api/search, /api/ocr, /api/export/... (тонкий: валідація
                   запиту -> виклик logic -> JSON)
  db.py          — SQLite-слой: SCHEMA, get_conn(), _migrate(), CRUD
  logic/         — чисті функції без I/O (легко тестувати)
    date_parser.py — природні дати UA/EN -> ParsedDate (remind_at, due_date)
    ocr_extract.py — евристики: сировий текст (скріншот/OCR) -> кандидати
                     задач (Tesseract опційний, текст працює і без нього)
    triage.py      — автомат станів inbox -> today/week/someday/done
    focus_timer.py — focus-сесії; focus_stats.py — статистика
    recurring.py   — повторення: щоденні/щотижневі/будні/кожні N днів;
                     при виконанні створюється наступний екземпляр
    markdown.py    — безпечний рендер нотаток (тільки дозволені теги)
    digest.py, review.py, tags.py, ics_export.py, csv_export.py,
    task_export.py, time_tracker.py — інші чисті модулі
  cli.py         — консольна точка входу mindcatch
static/          — фронтенд без збірників: index.html (CSS inline),
                   app.js (vanilla ES), i18n.json (словники UA/EN),
                   manifest.json (PWA), favicon.svg
  sw.js          — service worker: offline-first. При install пре-кешує
                   app shell: ["/", "index.html", "app.js", "i18n.json",
                   "manifest.json", "favicon.svg"] (константа SHELL).
                   /api/* НІКОЛИ не кешується — живі дані. Сторінки:
                   network-first з фолбеком на кеш; статика: cache-first
                   + оновлення у фоні. При зміні shell-файлів підніміть
                   версію кеша (CACHE = "mindcatch-vN")!
```

Ключовий принцип: **логіка живе в `app/logic/` як чисті функції**, HTTP-слой
в `app/main.py` тільки склеює, дані — в `app/db.py`. Тести викликають модулі
логіки напряму, без сервера.

## Гілки

- **`main`** — стабільна гілка: OSS-код, зелений pytest, документи.
  Кожен push у `main` має проходити тести локально.
- **`mobile/android-ios`** — мобільний порт (Capacitor 6 shell + нативні
  Android/iOS-проєкти, CI-збірки APK/.app). Розвивається паралельно;
  основа — `main` + mobile-комміти. Деталі: [MOBILE.md](MOBILE.md).
  Мержіте свіжий `main` у гілку регулярно, щоб не накопичувати розбіжності.
- Фічі робіть у локальних гілках або прямо в `main` (для маленьких,
  повністю тестованих змін) — проєкт одно-осібний, беруш не обовʼязковий,
  але комітьте атомарно.

## Середовище + тести

```bash
git clone https://github.com/bigpi/mindcatch.git
cd mindcatch
python -m pip install -r requirements.txt
python -m pytest tests/ -v        # все має бути зеленим (наразі 297)
python -m uvicorn app.main:app --reload --port 8000
```

- Python 3.12+, stdlib-first, жодних важких залежностей.
- База для тестів задається env-змінною `MINDCATCH_DB` (фікстури тестів
  самі створюють тимчасову базу і чистять її між тестами).
- Без Node-збірки: фронт просто лежить у `static/` і роздається FastAPI.
  Синтаксис JS перевіряйте `node --check static/app.js`.

## Як додати нову мову парсингу дат

Зараз парсер (`app/logic/date_parser.py`) розуміє UA і EN: відносні дні
(сьогодні/завтра/післязавтра, today/tomorrow), дні тижня («у пʼятницю»,
«next monday»), явні дати (2026-11-10, 31.12, 31.12.2027, 5/06), час
(15:00, «завтра о 9:30»), «наступного тижня / next week». Щоб додати
третю мову (наприклад, польську):

1. **Словник днів тижня.** Додайте `_WEEKDAY_PL = {...}` — префікси форм
   слова -> номер дня (0=понеділок). Префікси короткі навмисно: вони мають
   покривати відмінки («у пʼятницю» і «пʼятниця» — один префікс).
2. **Відносні дні.** Розширте `_RELATIVE` регулярками нової мови
   (`dziś` -> 0, `jutro` -> 1 тощо). Порядок у списку має значення:
   довші фрази (типу «післязавтра», «day after tomorrow») йдуть перед
   коротшими («завтра»), інакше коротша зʼїсть довшу.
3. **Регулярка днів тижня.** За патерном `_UA_WEEKDAY_RE` / `_EN_WEEKDAY_RE`
   додайте `_PL_WEEKDAY_RE` і функцію `_weekday_from_pl(word) -> int | None`
   (за патерном `_weekday_from_ua`). Не забудьте про апострофи —
   `_normalize()` вже уніфікує `ʼ ' \` у `'`.
4. **Далі в `parse()`.** Додайте блок «if result_date is None» з вашою
   регуляркою **до** фолбека «next week» і **після** EN/UA — так явні дати
   і вже підтримані мови залишаться пріоритетними.
5. **Час і формати дат.** `_TIME_RE` і `_DMY_DATE_RE` мовонезалежні;
   якщо ваша мова пише дати інакше (m/d замість d.m) — додайте окрему
   регулярку і обробку за патерном блоків 1–2 у `parse()`.
6. **Тести.** Створіть `tests/test_date_parser_pl.py` за патерном
   `tests/test_date_parser.py`: константа `TODAY = date(2026, 11, 4)`
   (середа — детермінізм!), класи `TestRelativeDays`, `TestWeekdays`,
   `TestExplicitDates`, `TestTimeExtraction`, `TestNoFalsePositives`.
   Кожен тест викликає `parse(text, TODAY)` і порівнює `p.date` / `p.time`.
   **Обовʼязково: тест, що фраза нової мови НЕ парситься як UA/EN
   хибнопозитив**, і тест на середину тексту («нагадай завтра о 09:05…»).
7. Оновіть докстрінг модуля (список підтриманого) і `CHANGELOG.md`.

## Як додати поле в items

SQLite тут без Alembic — міграції handwritten у `app/db.py::_migrate()`.
Патерн простий і перевірений тестами на «старих» базах:

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
        # "нове_поле": "ТВИП",      <- 1. додайте сюди
    }
    for name, decl in additions.items():
        if name not in cols:
            conn.execute(f"ALTER TABLE items ADD COLUMN {name} {decl}")
    conn.execute("CREATE TABLE IF NOT EXISTS time_logs (...)")
    conn.commit()
```

Чому саме так: `PRAGMA table_info(items)` дає фактичні колонки поточної
бази; `ALTER TABLE ... ADD COLUMN` виконується тільки для відсутніх — тому
одна й та сама база безболісно мігрує кілька разів підряд, а свіжа база,
створена зі `SCHEMA`, просто пропускає міграції. `init_db()` завжди викликає
`_migrate()` після `executescript(SCHEMA)`.

Кроки для нового поля `foo TEXT`:

1. Додайте рядок у `additions` у `_migrate()` (і, якщо це нова **таблиця**,
   — окремий `CREATE TABLE IF NOT EXISTS` поруч з `time_logs`).
2. Оновіть `SCHEMA` (нова база одразу з полем) — ініціалізація і міграція
   мають давати ідентичний результат.
3. CRUD: прийміть параметр у `create_item()` / додайте підтримку в
   `update_fields()` (він генеричний — `**fields` уже працює) або напишіть
   вузький helper як `update_status()`.
4. Ендпоінт у `app/main.py` (PUT/PATCH на `/api/items/{id}/...` або поле
   у `create`-запиті) + бізнес-логіка в `app/logic/`, якщо є правила.
5. Фронт: поле в payload у `static/app.js` (якщо редагується з UI).
6. Тест: створіть тимчасову базу **без** нового поля (вручну `ALTER TABLE`
   в зворотний бік або sqlite-фікстура зі старим SCHEMA), викличте
   `init_db()` і перевірте, що колонка зʼявилася і дані не втратилися.
   Також тест API-ендпоінта через `TestClient`.

## i18n: правила (критично)

- Усі UI-рядки — тільки через словники `static/i18n.json`: секції `"ua"`
  і `"en"`, **ключі ідентичні в обох**, плейсхолдери `{n}`, `{q}` — теж.
  Жодних хардкод-рядків у `static/app.js` і `index.html`.
- Service worker пре-кешує `i18n.json` (він у `SHELL` у `sw.js`), тож
  переклад працює офлайн. Якщо додаєте ключі — памʼятайте про версію кеша.
- **НІКОЛИ російської.** Російську локалізацію не приймаємо — рішення
  власника проєкту, не обговорюється. Це захищено тест-гардами:
  `tests/test_i18n.py::test_no_russian_anywhere` (гард шукає в словниках
  три літери російської абетки, яких немає в українській) та
  `tests/test_oss_hygiene.py::test_no_russian_in_any_community_file`
  (усі doc-файли). Український текст ці гарди проходить, але перед коммітом
  перечитайте текст: жодних російських слів і запозичень.
- UA-значення мають бути живою українською (гард перевіряє «Сьогодні»
  з українською «і»), EN — без жодної кирилиці взагалі.
- Новий ключ = обидві мови в одному комміті; тест перевіряє
  `set(ua) == set(en)` і мінімум 40 ключів.

## Pull request процес і стиль комітів

1. Тести: `python -m pytest` — зелений; нова фіча = новий тест-файл або клас.
2. Один PR = одна фіча/фікса (легко ревʼювити і відкочувати).
3. Без приватних шляхів, токенів чи реальних користувацьких даних
   (CI/тести це перевіряють: `tests/test_docs.py::TestPrivacyHygiene`).
4. A11y: нові кнопки/поля отримують `aria-label`; у фокусі має бути видно.
5. Оновіть `CHANGELOG.md` та, якщо потрібно, `README.md` + `README.en.md`.
6. Commit message (Conventional Commits, коротко і по суті):
   - `feat(scope): ...` — нова функціональність
   - `fix(scope): ...` — виправлення
   - `docs: ...` / `ci: ...` / `mobile: ...` / `chore: ...`
   - scope — зона: `(date_parser)`, `(i18n)`, `(db)`, `(pwa)`…
   - приклади з історії: `feat(packaging): pyproject.toml 1.0.0...`,
     `fix(oss): secret scanner excludes its own pattern literals`
7. PR опис: що і навіщо + як перевіряли (команда pytest, сценарій руками).

## Мобільний порт

Мобільні застосунки — **тонка оболонка (Capacitor 6), яка підключається до
СВОГО сервера**: UI не вбудований у застосунок, адреса сервера вводиться
на splash-екрані при першому запуску, перевіряється `GET /api/tags` і
зберігається нативно (Preferences). Дані не залишають ваш сервер.
Повна інструкція (sideload Android, AltStore iOS, Tailscale, локальна
збірка) — **[MOBILE.md](MOBILE.md)**. CI-збірки: `.github/workflows/
android-build.yml` (debug APK) і `ios-build.yml` (unsigned .app).
Зміни фронтенда робіть у `static/` — мобільний shell показує саме його.

## Reporting bugs / Про баги

Використовуйте шаблон
[.github/ISSUE_TEMPLATE/bug_report.md](.github/ISSUE_TEMPLATE/bug_report.md).
Для безпеки — [SECURITY.md](SECURITY.md), приватно, не в публічному issue.

## Code style / Стиль коду

- Python: stdlib-first, type hints, docstrings коротко і по суті.
- JS: без збірників і фреймворків — vanilla ES, `node --check static/app.js`.
- CSS: у `index.html`, темна тема через CSS-змінні.

## License / Ліцензія

Вносячи зміни, ви погоджуєтеся, що вони ліцензуються під MIT разом із
проєктом. By contributing you agree your work is licensed under MIT.
