"""Morning warm-up templates (PLAN.md roadmap v0.3: «шаблони ранкової
розгінки»). Ready-made task sets that seed Today with one tap — pure data +
pure functions, no I/O, fully testable.

100% free (OSS roadmap): every template is available to everyone.
"""

from __future__ import annotations

TEMPLATES: dict[str, dict] = {
    "warmup": {
        "id": "warmup",
        "name_ua": "Ранковий розгін",
        "name_en": "Morning warm-up",
        "steps": [
            {"text": "Склянка води", "type": "task"},
            {"text": "15 хв руху або розминки", "type": "task"},
            {"text": "Перевірити календар на сьогодні", "type": "task"},
            {"text": "Вибрати 3 головні задачі дня", "type": "task"},
        ],
    },
    "deep-work": {
        "id": "deep-work",
        "name_ua": "День глибокої роботи",
        "name_en": "Deep-work day",
        "steps": [
            {"text": "Закрити всі сторонні вкладки й месенджери", "type": "task"},
            {"text": "Одна головна задача на фокус (pomodoro 25 хв)", "type": "task"},
            {"text": "Вимкнути сповіщення до обіду", "type": "task"},
        ],
    },
    "reset": {
        "id": "reset",
        "name_ua": "Перезавантаження (день розвалився)",
        "name_en": "Reset (the day fell apart)",
        "steps": [
            {"text": "Видихнути: минуле не рахується", "type": "note"},
            {"text": "Вибрати ОДНУ мікрозадачу на 10 хвилин", "type": "task"},
            {"text": "Зробити її — і тільки потім дивитись на решту", "type": "task"},
        ],
    },
}


def list_templates() -> list[dict]:
    """Catalogue for the UI: id, localized name, step count."""
    return [
        {
            "id": t["id"],
            "name_ua": t["name_ua"],
            "name_en": t["name_en"],
            "steps": len(t["steps"]),
        }
        for t in TEMPLATES.values()
    ]


def get_template(template_id: str) -> dict | None:
    return TEMPLATES.get(template_id)


def template_steps(template_id: str) -> list[dict] | None:
    """Steps of a template ({text, type}), or None for an unknown id."""
    t = get_template(template_id)
    return [dict(s) for s in t["steps"]] if t else None
