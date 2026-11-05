# Mindcatch — ADHD Mental-Load Capture

![CI](https://github.com/bigpi/mindcatch/actions/workflows/tests.yml/badge.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Version](https://img.shields.io/badge/version-1.0.0-purple.svg)

Offline-first «виловлювач думок»: одне велике поле → задача, нуль тертя.

> English docs: [README.en.md](README.en.md). Мова інтерфейсу перемикається в застосунку (кнопка вгорі або клавіша <kbd>L</kbd>).

## Чому це існує

- Пост на r/ADHD: *«app that would take the mental load of having to remember everything»* — **2 411 upvotes, 205 коментарів**. Люди з ADHD тонуть у «тримати все в голові»: будь-який застосунок із формами, полями і налаштуваннями додає навантаження замість того, щоб знімати його.
- Запити на r/ProductivityApps на **об'єднання calendar + tasks + notes** в одному місці.
- **Subscription fatigue**: користувачі втомилися від щомісячних підписок на «хмарні productivity» — Mindcatch відповідає: **local-first і безкоштовний опенсорс**.

## Що це

- **Швидкий capture**: головний екран = одне велике поле + Enter → item в inbox (GTD-style).
- Типи auto-класифікуються: **task** (дієслово-дія), **reminder** (дата/час у тексті), **note** (все інше).
- **Парсинг дат (UA + EN)**: «завтра», «післязавтра», «у пʼятницю», «next monday», «tomorrow 15:00», «2026-11-10», «31.12» → автоматично заповнюють `remind_at` / `due_date`.
- **Локальні нагадування**: Web Notification API — дозвіл запитується при першому capture; reminders на поточний день показуються, поки вкладка відкрита.
- **Daily digest**: «Сьогодні: N задач, M нагадувань» на Today view.
- **Імпорт скріншота**: drag&drop зображення → якщо встановлений Tesseract (`pytesseract`), OCR → евристика витягує рядки, схожі на задачі → кандидати на підтвердження одним кліком. **Без Tesseract — graceful fallback на ручний ввід** (`ocr_available: false`, UI показує підказку).
- **Огляд/triage**: inbox → перетягнути (select) в Today / Week / Someday / Done.
- **Теги/проєкти**: `#теги` у capture чіпляються автоматично; 🏷 на item — редагування з підказками з історії; фільтр-чіпси над списком (`?tag=`, `GET /api/tags`).
- **Пошук + архів**: поле пошуку шукає substring по title і body (без регістру, кирилиця включно) по всіх статусах; `/api/archive` — виконане, свіже зверху.
- **Статистика фокусу**: вкладка Stats — SVG bar chart хвилин помодоро/таймера за 7 днів (`/api/stats/focus`).
- **Quick capture API**: `POST /api/quick {text}` — capture з curl/лаунчера без UI (див. нижче).
- **Today view + focus mode**: одна задача, таймер pomodoro 25/5 хв (довга перерва 15 хв після кожних 4).
- **Повторювані задачі**: «↻» на задачі — цикл немає → щоденна → щотижнева; «✓» виконує задачу й одразу створює наступне повторення в inbox (зсув `remind_at`/`due_date`).
- **Нотатки з markdown**: «📝» на нотатці → редактор з живим preview (безпечний мінімальний рендер: заголовки, **жирний**, `код`, списки, посилання http(s) only).
- **Естимации часу + таймер**: «⏱» старт/стоп на задачі; історія сесій (`time_logs`), витрачений час проти естимации («⏱ 12/45 хв»).
- **Weekly review**: вкладка Review — що зроблено за тиждень (з понеділка), що перенеслось, скільки створено.
- **Дані**: SQLite локально; one-click експорт JSON / CSV / ICS / Todoist / Markdown. PWA-manifest + service worker (offline shell).
- **Календар (ICS)**: `/api/export/calendar.ics` — задачі з датами стають подіями у вашому календарі (Google/Outlook/Apple), повторювані — як RRULE.
- **Todoist/Markdown**: `/api/export/todoist.md` вставляється прямо в Todoist (`@мітки`, `p1`-`p4`, 📅 дати); `/api/export/markdown` — повний експорт за статусами.
- **Onboarding tour**: 3 підказки при першому вході (localStorage — показуються один раз).
- **i18n UA/EN**: перемикач у шапці (клавіша <kbd>L</kbd>), авто-детект мови браузера.

## Швидкий старт

```bash
git clone https://github.com/bigpi/mindcatch.git
cd mindcatch
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
# відкрити http://localhost:8000
```

Тести:

```bash
python -m pytest tests/ -v
bash scripts/smoke.sh   # smoke: піднімає сервер на випадковому порті, перевіряє головні ендпоінти
```

## Quick capture з командного рядка

Сервер приймає думки і без UI — `POST /api/quick`, зручний для curl, Alfred/Raycast-style лаунчерів і ярликів:

```bash
curl -s http://localhost:8000/api/quick \
  -H 'Content-Type: application/json' \
  -d '{"text":"подзвонити мамі завтра 15:00 #сімʼя"}'
```

Приклад аліасу (додайте у `~/.bashrc` або PowerShell `$PROFILE`):

```bash
mc() { curl -s http://localhost:8000/api/quick -H 'Content-Type: application/json' -d "{\"text\":\"$*\"}"; }
# тепер у терміналі:  mc передзвонити в банк завтра #фінанси
```

Дата парситься так само, як в UI («завтра», «next monday», «31.12»), `#теги` чіпляються автоматично.

OCR (опційно): встановіть Tesseract (https://github.com/UB-Mannheim/tesseract/wiki) та `pip install pytesseract pillow` — імпорт скріншотів запрацює сам; без нього — ручний ввід.

## Встановлення як PWA

1. Відкрийте `http://localhost:8000` у Chrome/Edge.
2. Адресний рядок → іконка «Встановити» (або меню ⋮ → «Встановити застосунок Mindcatch»).
3. Застосунок відкриється у власному вікні й працює офлайн (service worker кешує shell; дані — у локальному SQLite).

На Android: Chrome → меню → «Додати на головний екран».

## Keyboard shortcuts

| Клавіша | Дія |
|---|---|
| <kbd>N</kbd> | фокус на поле capture |
| <kbd>Enter</kbd> | зберегти capture |
| <kbd>T</kbd> | Today view |
| <kbd>F</kbd> | focus mode (для задач у Today) |
| <kbd>E</kbd> | export JSON |
| <kbd>Esc</kbd> | закрити focus / редактор нотатки |

## Що нового у v1.0.0

- ICS-експорт у календар (RFC 5545, RRULE для повторюваних).
- Повторення «кожні N днів» і «лише будні» (пн-пт).
- Todoist-сумісний і Markdown-експорт задач.
- Onboarding tour: 3 підказки при першому вході.
- UA/EN перемикач мови + авто-детект (без російської — політичне рішення).
- README.en.md, INSTALL.md, packaging (`pip install -e .`, команда `mindcatch`).
- Data safety: one-click CSV + підтвердження перед архівуванням.
- A11y: aria-labels, skip-link, focus-visible, dialog-ролі.

Див. [CHANGELOG.md](CHANGELOG.md) для повної історії.

## Структура

```
mindcatch/
├── app/
│   ├── main.py            # FastAPI: /api/capture, /api/quick, /api/search, /api/stats/focus, /api/export
│   ├── db.py              # SQLite (stdlib sqlite3, WAL) + міграції
│   └── logic/
│       ├── date_parser.py # UA+EN дати → remind_at / due_date
│       ├── digest.py      # «Сьогодні: N задач, M нагадувань»
│       ├── ocr_extract.py # евристика задач з тексту + optional pytesseract
│       ├── triage.py      # стан-машина inbox/today/week/someday/done
│       └── focus_timer.py # pomodoro 25/5/15, injected clock
├── static/                # PWA-фронтенд (index.html, app.js, sw.js)
├── tests/                 # pytest: чиста логіка + API (TestClient)
└── .github/workflows/     # CI: pytest на Python 3.12/3.13
```

## Roadmap

- ~~v0.1 (alpha)~~: capture, парсинг дат, локальні нагадування, digest, triage, focus pomodoro, export JSON.
- ~~v0.3~~: повторювані задачі, markdown-нотатки, естимации часу + таймер, weekly review.
- ~~v0.4~~: теги/проєкти + фільтр-чіпси, quick-capture API, пошук + архів, статистика фокусу, PWA install + offline shell v3.
- ~~v1.0 (зараз)~~: ICS-календар, every-N/weekdays повторення, Todoist/Markdown експорт, onboarding tour, i18n UA/EN, INSTALL.md + packaging, a11y, open-source hygiene.
- **Далі**: шаблони ранкової розгінки, інсталятор Windows exe (див. PLAN.md).

## Мобільні застосунки (Android / iOS)

Capacitor 6-оболонка, яка підключається до **свого сервера**: адреса вводиться
на splash-екрані при першому запуску і зберігається в пристрої. Android —
sideload APK з [Releases](https://github.com/bigpi/mindcatch/releases)
(повністю безкоштовно); iOS — unsigned збірка через AltStore/Sideloadly
(App Store потребує Apple Developer $99/рік — не в бюджеті). Віддалений
доступ — Tailscale/WireGuard. Деталі: [MOBILE.md](MOBILE.md).

## Contributing

PRs вітаються! Дивіться [CONTRIBUTING.md](CONTRIBUTING.md) (правила, чекліст
PR). Баги — через шаблон issue; безпека — приватно, див. [SECURITY.md](SECURITY.md).
Проєкт піде в опенсорс — рекомендовані GitHub topics:
`adhd`, `productivity`, `gtd`, `pomodoro`, `pwa`, `fastapi`, `local-first`.

## Ліцензія

MIT — див. [LICENSE](LICENSE).
