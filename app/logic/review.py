"""Weekly review: what got done this week, what carried over.

Pure logic over item dicts; week starts Monday (GTD habit).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta


def week_start(today: date | None = None) -> date:
    """Monday of the current week."""
    d = today or date.today()
    return d - timedelta(days=d.weekday())


def _as_date(iso: str | None) -> date | None:
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso).date()
    except ValueError:
        return None


def weekly_review(items: list[dict], today: date | None = None) -> dict:
    today = today or date.today()
    start = week_start(today)

    done_this_week = [
        it for it in items
        if it.get("status") == "done" and _as_date(it.get("updated_at"))
        and start <= _as_date(it["updated_at"]) <= today
    ]
    carried_over = [
        it for it in items
        if it.get("status") != "done" and _as_date(it.get("created_at"))
        and _as_date(it["created_at"]) < start
    ]
    return {
        "week_start": start.isoformat(),
        "today": today.isoformat(),
        "done_this_week": done_this_week,
        "carried_over": carried_over,
        "counts": {
            "done": len(done_this_week),
            "carried": len(carried_over),
            "created_this_week": sum(
                1 for it in items
                if _as_date(it.get("created_at")) and _as_date(it["created_at"]) >= start
            ),
        },
    }
