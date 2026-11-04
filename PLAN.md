# PLAN — Mindcatch

## 1. Аудиторія

- Хто: дорослі з ADHD (діагностованим або self-suspected), а також широка аудиторія «розум перевантажений, треба виловити думку швидко».
- Біль: **mental load** — тримати в голові 30 дрібниць; звичайні таск-менеджери вимагають структурування (проєкти, теги, дати) — це саме те навантаження, від якого треба позбутися. Evidence: пост r/ADHD «app that would take the mental load of having to remember everything» — 2 411 upvotes, 205 коментарів; запити на об'єднання calendar+tasks+notes на r/ProductivityApps.
- Вторинний сегмент: всі, хто втомився від subscription-софту і хмари; цінує local-first і one-time purchase.

## 2. MVP scope (поточний реліз)

Включено:
- Швидкий capture: одне поле + Enter → inbox (класифікація task/reminder/note за евристиками).
- Імпорт скріншота: drag&drop → pytesseract (якщо встановлений) → евристика витягу кандидатів → підтвердження; **fallback на ручний ввід**, якщо Tesseract немає.
- Triage: inbox → Today / Week / Someday / Done (валідовані переходи, 400 на невалідні).
- Today view + focus mode: одна задача, pomodoro 25 хв, коротка перерва 5 хв, довга 15 хв після 4 циклів (pause/resume/stop).
- Keyboard-first: N / T / F / E / Esc.
- SQLite локально (WAL), export JSON.
- PWA: manifest + service worker (offline shell), FastAPI разом обслуговує фронт.

Не включено (свідомо, для MVP):
- Справжній парсинг дат у remind_at (зараз reminder зберігає текст; тип визначено).
- Синхронізація між пристроями, повторювані задачі, calendar view.
- Push-нагадування.

## 3. Архітектура

- **Бекенд**: Python + FastAPI (localhost, uvicorn), SQLite через stdlib `sqlite3` — нуль зовнішніх сервісів, дані не залишають машину.
- **Чиста логіка** (`app/logic/`) відділена від I/O і БД — саме вона покрита тестами:
  - `ocr_extract.py`: евристика (дієслова EN/UA, патерни дат/часу, відсікання URL і «болтовні», дедуплікація, поріг score ≥ 2); `ocr_image()` повертає `None`, якщо Tesseract недоступний.
  - `triage.py`: стан-машина переходів, `move()` повертає копію item або ValueError.
  - `focus_timer.py`: PomodoroTimer з injected clock (`now` передається явно) — детерміновані тести.
- **Фронт**: vanilla JS, один app.js; SW кешує shell, API ніколи не кешується.

## 4. Roadmap

- **v0.1 (MVP, зараз)**: capture, OCR-евристика з fallback, triage, focus pomodoro, export JSON.
- **v0.2**: парсинг дат → remind_at (dateparser, UA+EN), локальні нативні нагадування (web notifications), повторювані задачі.
- **v0.3**: статистика mental load (скільки capture/день), теги-хештеги в тексті, шаблони ранкової розгінки.
- **v1.0**: GitHub-реліз інсталятора (Windows exe через PyInstaller), сторінка-лендінг, live demo.

## 5. Монетизація

**One-time purchase** (без підписок — прямо відповідає subscription fatigue з evidence):
- **Free**: повний capture/triage/focus, SQLite локально, export JSON.
- **Pro ($15–25 разово)**: OCR-скріншоти в комплекті з інсталятором (без ручної установки Tesseract), теми, резервні копії в локальну папку на вибір, статистика.
- Позиціювання: «Купи раз — твій мозок спокійний назавжди». Продаж через Gumroad/самописну сторінку; просування — той самий пост-формат на r/ADHD, r/productivity, TikTok/Shorts «ADHD capture demo».

## 6. Ризики

| Ризик | Імовірність | Мітигація |
|---|---|---|
| Користувач очікує «повноцінний» таск-менеджер | Висока | Чітке позиціювання: capture-first, не конкурент Todoist |
| OCR якість на скріншотах | Середня | Евристика з порогом + підтвердження людини; fallback на ручний ввід |
| Tesseract установка — бар'єр | Висока | graceful fallback зараз; у Pro — bundled binary |
| Один пристрій без синку | Середня | Export JSON зараз; у v0.3 — опційний sync через локальну папку (Syncthing-friendly) |
| Ринок захоплений безкоштовними додатками | Середня | One-time низька ціна; унікальність — ADHD-фокус і тертя нуль |

## 7. Метрики успіху

- Час від відкриття додатку до першого збереженого capture < 5 с.
- Retention D7 ≥ 30% (локальний лічильник, без телеметрії в free).
- Конверсія в Pro ≥ 5% серед активних.
