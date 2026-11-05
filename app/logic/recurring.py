"""Recurring tasks: daily / weekly.

Pure logic: given a completed item, produce the next occurrence (same text,
type and recurrence; remind_at/due_date shifted forward; back to inbox).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

RECURRENCES = ("daily", "weekly")


def validate(recurrence: str | None) -> str | None:
    if recurrence is None or recurrence == "":
        return None
    if recurrence not in RECURRENCES:
        raise ValueError(f"unknown recurrence: {recurrence} (use daily|weekly)")
    return recurrence


def next_date(d: date, recurrence: str) -> date:
    """Next occurrence date after ``d``."""
    validate(recurrence)
    if recurrence == "daily":
        return d + timedelta(days=1)
    return d + timedelta(days=7)  # weekly


def _shift(iso: str | None, recurrence: str) -> str | None:
    if not iso:
        return None
    dt = datetime.fromisoformat(iso)
    nxt = next_date(dt.date(), recurrence)
    return nxt.isoformat() + iso[10:]


def spawn_next(item: dict, today: date | None = None) -> dict | None:
    """The next occurrence of a completed recurring item, or None when the
    item is not recurring. The copy goes back to the inbox; ids/timestamps
    are reset by the DB layer."""
    recurrence = validate(item.get("recurrence"))
    if recurrence is None:
        return None
    anchor = item.get("due_date") or item.get("remind_at")
    if anchor:
        # shift from the scheduled date so occurrences never drift forward
        base = datetime.fromisoformat(anchor[:10] + "T00:00:00").date()
    else:
        base = today or date.today()
    nxt = next_date(base, recurrence)
    if item.get("remind_at"):
        remind_at = _shift(item.get("remind_at"), recurrence)
    elif item.get("due_date"):
        remind_at = nxt.isoformat() + "T09:00:00"
    else:
        # recurring item with no dates: remind next occurrence at 09:00
        remind_at = nxt.isoformat() + "T09:00:00"
    return {
        "text": item["text"],
        "type": item["type"],
        "status": "inbox",
        "recurrence": recurrence,
        "due_date": nxt.isoformat() if item.get("due_date") else None,
        "remind_at": remind_at,
    }
