"""Daily digest counts: what does 'today' look like?

Pure logic over item dicts so it is testable without a database.
"""

from __future__ import annotations

from datetime import date, datetime


def _day_of(iso: str | None) -> str | None:
    """'2026-11-05T15:00:00' / '2026-11-05' -> '2026-11-05'; None-safe."""
    if not iso:
        return None
    return iso[:10]


def digest_counts(items: list[dict], today: date | None = None) -> dict:
    """Counts for the Today view digest line: N задач, M нагадувань.

    - tasks: items in the 'today' status (the GTD today list)
    - reminders: items of type 'reminder' whose remind_at/due_date falls on
      ``today`` (regardless of status — a done reminder is still history)
    """
    today = today or date.today()
    today_iso = today.isoformat()
    tasks = sum(1 for it in items if it.get("status") == "today")
    reminders = sum(
        1 for it in items
        if it.get("type") == "reminder"
        and (_day_of(it.get("remind_at")) == today_iso or _day_of(it.get("due_date")) == today_iso)
    )
    return {"date": today_iso, "tasks": tasks, "reminders": reminders}


def due_today(items: list[dict], today: date | None = None) -> list[dict]:
    """Reminder items due today (for local web notifications)."""
    today_iso = (today or date.today()).isoformat()
    return [
        it for it in items
        if it.get("type") == "reminder"
        and (_day_of(it.get("remind_at")) == today_iso or _day_of(it.get("due_date")) == today_iso)
    ]
