# Mindcatch — ADHD Mental-Load Capture

![CI](https://github.com/bigpi/mindcatch/actions/workflows/tests.yml/badge.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Version](https://img.shields.io/badge/version-0.1.0--alpha-purple.svg)

Offline-first «виловлювач думок»: одне велике поле → задача, нуль тертя.

## Проблема

- Пост на r/ADHD: *«app that would take the mental load of having to remember everything»* — **2 411 upvotes, 205 коментарів**. Люди з ADHD тонуть у «тримати все в голові»: будь-який застосунок із формами, полями і налаштуваннями додає навантаження замість того, щоб знімати його.
- Запити на r/ProductivityApps на **об'єднання calendar + tasks + notes** в одному місці.
- **Subscription fatigue**: користувачі втомилися від щомісячних підписок на «хмарні productivity» — запит на **one-time purchase, local-first**.

## Що це

- **Швидкий capture**: головний екран = одне велике поле + Enter → item в inbox (GTD-style).
- Типи auto-класифікуються: **task** (дієслово-дія), **reminder** (дата/час у тексті), **note** (все інше).
- **Парсинг дат (UA + EN)**: «завтра», «післязавтра», «у пʼятницю», «next monday», «tomorrow 15:00», «2026-11-10», «31.12» → автоматично заповнюють `remind_at` / `due_date`.
- **Локальні нагадування**: Web Notification API — дозвіл запитується при першому capture; reminders на поточний день показуються, поки вкладка відкрита.
- **Daily digest**: «Сьогодні: N задач, M нагадувань» на Today view.
- **Імпорт скріншота**: drag&drop зображення → якщо встановлений Tesseract (`pytesseract`), OCR → евристика витягує рядки, схожі на задачі → кандидати на підтвердження одним кліком. **Без Tesseract — graceful fallback на ручний ввід** (`ocr_available: false`, UI показує підказку).
- **Огляд/triage**: inbox → перетягнути (select) в Today / Week / Someday / Done.
- **Today view + focus mode**: одна задача, таймер pomodoro 25/5 хв (довга перерва 15 хв після кожних 4).
- **Дані**: SQLite локально; export у JSON. PWA-manifest + service worker (offline shell).

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
```

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
| <kbd>Esc</kbd> | закрити focus mode |

## Структура

```
mindcatch/
├── app/
│   ├── main.py            # FastAPI: /api/capture, /api/items, /api/ocr, /api/digest, /api/export
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

- **v0.1 (alpha, зараз)**: capture, парсинг дат, локальні нагадування, digest, triage, focus pomodoro, export JSON.
- **Далі**: повторювані задачі, markdown-нотатки, естимации часу, weekly review (див. PLAN.md).

## Ліцензія

MIT — див. [LICENSE](LICENSE).
