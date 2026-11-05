# Contributing to Mindcatch

Дякуємо, що хочете допомогти! Mindcatch — локальний, offline-first
«виловлювач думок» для людей з ADHD. Нижче — правила, які тримають проєкт
простим і надійним.

Thanks for helping out! Mindcatch is a local-first, offline thought catcher
for people with ADHD. The rules below keep it simple and dependable.

## Ground rules / Основні правила

- **Мови інтерфейсу та документації: українська та англійська. Російську
  локалізацію не приймаємо** (рішення власника проєкту). / UI and docs are
  Ukrainian + English only. **Russian localization will not be accepted**
  (owner's policy decision).
- **Local-first назавжди**: жодних телеметрії, аналітики чи хмарних сервісів.
  Усі дані — в локальному SQLite. / Local-first forever: no telemetry, no
  analytics, no cloud. All data stays in a local SQLite file.
- Кожна фіча = окремий commit + тести. / One feature = one commit + tests.

## Getting started / Як почати

```bash
git clone https://github.com/bigpi/mindcatch.git
cd mindcatch
python -m pip install -r requirements.txt
python -m pytest tests/ -v        # все має бути зеленим
python -m uvicorn app.main:app --reload --port 8000
```

## Pull request checklist / Чекліст PR

1. Тести: `python -m pytest` — зелений; нова фіча = новий тест-файл або клас.
2. Один PR = одна фіча/фікса (легко ревʼювити і відкочувати).
3. Без приватних шляхів, токенів чи реальних користувацьких даних
   (CI/тести це перевіряють: `tests/test_docs.py::TestPrivacyHygiene`).
4. UI-рядки — тільки через словники `static/i18n.json` (UA і EN разом,
   з однаковими плейсхолдерами). Жодних хардкод-рядків у `app.js`.
5. A11y: нові кнопки/поля отримують `aria-label`; у фокусі має бути видно.
6. Оновіть `CHANGELOG.md` та, якщо потрібно, `README.md` + `README.en.md`.
7. Commit message: `feat(scope): ...` / `fix(scope): ...` / `docs: ...`.

## Reporting bugs / Про баги

Використовуйте шаблон [.github/ISSUE_TEMPLATE/bug_report.md]
(.github/ISSUE_TEMPLATE/bug_report.md). Для безпеки — [SECURITY.md]
(SECURITY.md), приватно, не в публічному issue.

## Code style / Стиль коду

- Python: stdlib-first, type hints, docstrings коротко і по суті.
- JS: без збірників і фреймворків —Vanilla ES, `node --check static/app.js`.
- CSS: у `index.html`, темна тема через CSS-змінні.

## License / Ліцензія

Вносячи зміни, ви погоджуєтеся, що вони ліцензуються під MIT разом із
проєктом. By contributing you agree your work is licensed under MIT.
