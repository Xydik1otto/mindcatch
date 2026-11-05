# Security Policy / Політика безпеки

## Supported versions / Підтримувані версії

| Version | Supported |
|---------|-----------|
| 1.0.x   | ✅ |
| < 1.0   | ❌ |

## Reporting a vulnerability / Як повідомити про вразливість

**EN:** Mindcatch is a local-only application (no network calls beyond serving
localhost). If you find a security issue — XSS in the markdown renderer, path
traversal, dependency vulnerability — please report it **privately** via
GitHub "Report a vulnerability" (Security tab → Advisories) or email the
maintainer. Do **not** open a public issue.

**UA:** Mindcatch — локальний застосунок (мережевих викликів поза localhost
немає). Якщо знайшли проблему безпеки — XSS у markdown-рендері, path
traversal, вразливість залежностей — повідомте **приватно** через GitHub
«Report a vulnerability» (вкладка Security → Advisories). **Не створюйте
публічний issue.**

## What to include / Що додати

- Version (`pip show mindcatch` or the git tag).
- Steps to reproduce / Кроки відтворення.
- Impact assessment / Оцінка впливу.

## Response time / Час реакції

We aim to respond within 7 days and ship a fix within 30 days for
confirmed issues. / Маємо на меті відповісти протягом 7 днів і виправити
підтверджені проблеми протягом 30 днів.
