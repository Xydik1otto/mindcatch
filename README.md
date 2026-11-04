# Mindcatch — ADHD Mental-Load Capture

Offline-first «виловлювач думок»: одне велике поле → задача, нуль тертя.

## Проблема

- Пост на r/ADHD: *«app that would take the mental load of having to remember everything»* — **2 411 upvotes, 205 коментарів**. Люди з ADHD тонуть у «тримати все в голові»: будь-який застосунок із формами, полями і налаштуваннями додає навантаження замість того, щоб знімати його.
- Запити на r/ProductivityApps на **об'єднання calendar + tasks + notes** в одному місці.
- **Subscription fatigue**: користувачі втомилися від щомісячних підписок на «хмарні productivity» — запит на **one-time purchase, local-first**.

## Що це

- **Швидкий capture**: головний екран = одне велике поле + Enter → item в inbox (GTD-style).
- Типи auto-класифікуються: **task** (дієслово-дія), **reminder** (дата/час у тексті), **note** (все інше).
- **Імпорт скріншота**: drag&drop зображення → якщо встановлений Tesseract (`pytesseract`), OCR → евристика витягує рядки, схожі на задачі (дієслова, дати) → кандидати на підтвердження одним кліком. **Якщо Tesseract немає — graceful fallback на ручний ввід** (API відповідає `ocr_available: false`, UI показує підказку).
- **Огляд/triage**: inbox → перетягнути (select) в Today / Week / Someday / Done.
- **Today view + focus mode**: одна задача, таймер pomodoro 25/5 хв (довга перерва 15 хв після кожних 4).
- **Keyboard-first**: `N` — новий capture, `T` — Today, `F` — focus, `E` — export, `Esc` — вийти з focus.
- **Дані**: SQLite локально; export у JSON. PWA-manifest + service worker (offline shell).

## Швидкий старт

```bash
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
# відкрити http://localhost:8000

# Тести
python -m pytest tests/ -v
```

OCR (опційно): встановіть Tesseract (https://github.com/UB-Mannheim/tesseract/wiki) та `pip install pytesseract pillow` — імпорт скріншотів запрацює сам; без нього — ручний ввід.

## Структура

```
mindcatch/
├── app/
│   ├── main.py            # FastAPI: /api/capture, /api/items, /api/ocr, /api/export
│   ├── db.py              # SQLite (stdlib sqlite3, WAL)
│   └── logic/
│       ├── ocr_extract.py # евристика задач з тексту + optional pytesseract
│       ├── triage.py      # стан-машина inbox/today/week/someday/done
│       └── focus_timer.py # pomodoro 25/5/15, injected clock
├── static/                # PWA-фронтенд (index.html, app.js, sw.js)
└── tests/
```
