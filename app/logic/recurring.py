"""Recurring tasks: daily / weekly / every-N-days / weekdays-only.

Pure logic: given a completed item, produce the next occurrence (same text,
type and recurrence; remind_at/due_date shifted forward; back to inbox).

Recurrence strings:
  - ``daily``    — every day
  - ``weekly``   — every 7 days
  - ``every:N``  — every N days (N >= 2)
  - ``weekdays`` — Monday..Friday only (skips weekends)
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

RECURRENCES = ("daily", "weekly", "weekdays")


def validate(recurrence: str | None) -> str | None:
    if recurrence is None or recurrence == "":
        return None
    if recurrence in RECURRENCES:
        return recurrence
    if recurrence.startswith("every:"):
        try:
            n = int(recurrence.split(":", 1)[1])
        except ValueError:
            raise ValueError(
                f"unknown recurrence: {recurrence} (use daily|weekly|every:N|weekdays)")
        if n < 2:
            raise ValueError("every:N needs N >= 2 (use 'daily' for every day)")
        return recurrence
    raise ValueError(
        f"unknown recurrence: {recurrence} (use daily|weekly|every:N|weekdays)")


def next_date(d: date, recurrence: str) -> date:
    """Next occurrence date strictly after ``d``."""
    validate(recurrence)
    if recurrence == "daily":
        return d + timedelta(days=1)
    if recurrence == "weekly":
        return d + timedelta(days=7)
    if recurrence == "weekdays":
        nxt = d + timedelta(days=1)
        while nxt.weekday() >= 5:  # Sat=5, Sun=6
            nxt += timedelta(days=1)
        return nxt
    # every:N (validated above)
    return d + timedelta(days=int(recurrence.split(":", 1)[1]))


def rrule(recurrence: str | None) -> str | None:
    """RFC 5545 RRULE representation (for calendar exports)."""
    if not recurrence:
        return None
    if recurrence == "daily":
        return "FREQ=DAILY"
    if recurrence == "weekly":
        return "FREQ=WEEKLY"
    if recurrence == "weekdays":
        return "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR"
    if recurrence.startswith("every:"):
        return f"FREQ=DAILY;INTERVAL={recurrence.split(':', 1)[1]}"
    return None


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
