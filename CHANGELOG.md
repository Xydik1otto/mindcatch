# Changelog

Усі значні зміни проєкту Mindcatch документуються тут.
Формат — [Keep a Changelog](https://keepachangelog.com/uk/1.1.0/),
версіонування — [SemVer](https://semver.org/lang/uk/).

## [0.4.0] - 2026-11-05

### Додано
- **Теги/проєкти** на items: `#хештеги` витягуються автоматично при capture,
  `PUT /api/items/{id}/tags`, фільтр `GET /api/items?tag=`, підказки з історії
  (`GET /api/tags` — ранжовані за частотою), фільтр-чіпси та інлайн-редактор тегів в UI.
- **Quick capture API**: `POST /api/quick {text}` — capture без UI для curl,
  лаунчерів і ярликів (у README — приклад curl + shell-аліас `mc`).
- **Пошук + архів**: `GET /api/search?q=` — substrings-пошук по title і body
  (без урахування регістру, кирилиця включно); `GET /api/archive` — виконані items,
  свіжі зверху; поле пошуку в UI з живими результатами.
- **Статистика фокусу**: `GET /api/stats/focus?days=7` — хвилини закритих
  фокус-сесій по днях + SVG bar chart; вкладка Stats у UI.
- **PWA**: кнопка «Встановити застосунок» (beforeinstallprompt), SVG favicon
  іконки в manifest, service worker v3 — реєстрація SW, network-first навігація
  з offline-фолбеком, повний precache shell.

## [0.3.0] - 2026-11-05

### Додано
- Weekly review view: зроблено за тиждень / перенеслось / створено (`GET /api/review/weekly`).
- Естимации часу + таймер на задачу з історією сесій (`time_logs`).
- Повний текст нотатки + markdown preview (XSS-безпечний рендер, `/api/md/preview`).
- Повторювані задачі (daily/weekly) з автопородженням наступного разу при виконанні.

## [0.2.0] - 2026-11-05

### Додано
- Повторювані задачі: цикл «немає → щоденна → щотижнева», spawn при complete.
- Markdown-нотатки: редактор з живим preview.
- Таймер фокусу: pomodoro-сесії з історією.

## [0.1.0] - 2026-11-05 (alpha)

### Додано
- Швидкий capture: одне поле → item в inbox, auto-класифікація task/reminder/note.
- Парсинг дат UA + EN («завтра», «next monday», «31.12») → remind_at / due_date.
- Локальні Web Notification нагадування + daily digest.
- Triage: inbox / Today / Week / Someday / Done; focus pomodoro 25/5.
- OCR скріншотів (опційно, graceful fallback без Tesseract), export у JSON,
  PWA-маніфест + offline shell.
