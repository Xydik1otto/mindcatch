# Changelog

Усі значні зміни проєкту Mindcatch документуються тут.
Формат — [Keep a Changelog](https://keepachangelog.com/uk/1.1.0/),
версіонування — [SemVer](https://semver.org/lang/uk/).

## [Unreleased]

### Додано
- **Мобільні порти (Capacitor 6)**: Android (minSdk 24, targetSdk 35,
  sideload APK з Releases) та iOS 14 (unsigned збірка через
  AltStore/Sideloadly). Splash-екран з полем «Адреса сервера» (збереження в
  Preferences); CI-збірки `android-build.yml` / `ios-build.yml` (артефакти
  30 днів, attach до Release на тег). Гайд — [MOBILE.md](MOBILE.md).

### Видалено
- Removed: monetization scaffolding — `.github/FUNDING.yml`, секція «Монетизація»
  з PLAN.md, згадки one-time purchase/Pro з README (100% free OSS).

## [1.0.0] - 2026-11-05

### Додано
- **ICS-експорт у календар**: `GET /api/export/calendar.ics` (RFC 5545) — задачі
  з датами стають подіями (all-day для `due_date`, таймовані для `remind_at`),
  повторювані переносяться як RRULE. Імпортується в Google Calendar, Outlook,
  Apple Calendar (запит з r/ProductivityApps: combined calendar+tasks).
- **Повторення every-N-days і weekdays-only**: нові типи повторення
  (`every:N`, N≥2; `weekdays` — пн-пт, пропускає вихідні). Цикл в UI:
  немає → щоденна → щотижнева → будні → кожні N днів.
- **Markdown/Todoist-сумісний експорт**: `GET /api/export/todoist.md` — чекліст,
  який вставляється прямо в Todoist (`@мітки`, `p1`-`p4`, 📅 дати);
  `GET /api/export/markdown` — повний експорт, згрупований за статусами.
- **Onboarding tour**: 3 підказки при першому вході (capture → triage →
  експорти), з підсвіткою реальних елементів UI; «Пропустити»/Esc завершують;
  переглянутість зберігається в localStorage.
- **i18n UA/EN**: перемикач мови в шапці (клавіша <kbd>L</kbd>), авто-детект
  мови браузера, вибір зберігається. Словники — `static/i18n.json`.
  Російську локалізацію не додано (політичне рішення власника).
- **README.en.md** — англійська версія документації для міжнародної аудиторії.
- **INSTALL.md** — покрокова інструкція для не-програміста: Windows
  (`scripts/start.bat`, автозапуск через папку Startup), Linux (systemd user
  unit), оновлення, резервне копіювання.
- **Packaging**: `pyproject.toml` з метаданими, консольна команда `mindcatch`,
  `pip install -e .` працює.
- **Data safety**: one-click експорт JSON/CSV/ICS/Todoist/Markdown; CSV з UTF-8
  BOM відкривається в Excel без майстра імпорту; підтвердження перед
  переміщенням в архів.
- **A11y**: aria-labels на всіх інтерактивних елементах, skip-link,
  `:focus-visible`, роль `dialog` у модальних вікнах, клавіатурна навігація.

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
