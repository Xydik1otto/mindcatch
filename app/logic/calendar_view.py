"""Calendar view of a month (roadmap: «calendar view»): pure logic that
builds a Monday-first month grid and maps dated items onto days.

No I/O — the API layer feeds it items and serializes the payload.
"""

from __future__ import annotations

import calendar as _cal
from datetime import date


def month_grid(year: int, month: int) -> list[list[dict | None]]:
    """Weeks of a month (Monday-first). Each week has exactly 7 cells;
    cells outside the month are None (padding)."""
    weeks: list[list[dict | None]] = []
    for week in _cal.Calendar(firstweekday=0).monthdatescalendar(year, month):
        weeks.append([
            {"date": d.isoformat(), "in_month": d.month == month}
            if d.month == month else None
            for d in week
        ])
    return weeks


def day_key(item: dict) -> str | None:
    """The calendar day an item belongs to: due_date, else the date part
    of remind_at. Undated items do not appear on the calendar."""
    if item.get("due_date"):
        return item["due_date"][:10]
    if item.get("remind_at"):
        return item["remind_at"][:10]
    return None


def items_by_day(items: list[dict]) -> dict[str, list[dict]]:
    """Group items by their day; done items are skipped (the calendar is
    about what is ahead)."""
    out: dict[str, list[dict]] = {}
    for it in items:
        if it.get("status") == "done":
            continue
        key = day_key(it)
        if not key:
            continue
        out.setdefault(key, []).append({
            "id": it["id"], "text": it["text"], "type": it["type"],
        })
    return out


def validate_month(year: int, month: int) -> None:
    if not 1 <= month <= 12:
        raise ValueError(f"month must be 1..12, got {month}")
    if not 1 <= year <= 9999:
        raise ValueError(f"year must be 1..9999, got {year}")


def month_payload(year: int, month: int, items: list[dict]) -> dict:
    validate_month(year, month)
    return {
        "year": year,
        "month": month,
        "weeks": month_grid(year, month),
        "items": items_by_day(items),
        "today": date.today().isoformat(),
    }
