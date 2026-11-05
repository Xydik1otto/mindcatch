"""ICS (iCalendar) export: tasks with dates become calendar events.

RFC 5545 text/calendar — importable into Google Calendar, Outlook, Apple
Calendar, Thunderbird. Every item with a due_date or remind_at gets a VEVENT.
Recurring items carry an RRULE so the calendar keeps up with repetitions.
"""

from __future__ import annotations

from datetime import datetime, timezone

PRODID = "-//mindcatch//mindcatch 1.0//EN"


def _ics_escape(text: str) -> str:
    """RFC 5545 §3.3.11 TEXT escaping."""
    out = (text or "").replace("\\", "\\\\").replace(";", r"\;")
    out = out.replace(",", r"\,").replace("\r\n", "\\n").replace("\n", "\\n")
    return out


def _fold(line: str, limit: int = 75) -> list[str]:
    """RFC 5545 §3.1 content lines must be <=75 octets; fold with CRLF + space."""
    if len(line) <= limit:
        return [line]
    parts, cur = [], line[:limit]
    rest = line[limit:]
    while len(rest) > limit - 1:
        parts.append(cur)
        cur = " " + rest[: limit - 1]
        rest = rest[limit - 1:]
    parts.extend([cur, " " + rest] if rest else [cur])
    return parts


def _dtstamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _rrule(recurrence: str | None) -> str | None:
    """Map our recurrence strings onto RFC 5545 RRULE (None = one-off)."""
    if not recurrence:
        return None
    if recurrence == "daily":
        return "FREQ=DAILY"
    if recurrence == "weekly":
        return "FREQ=WEEKLY"
    if recurrence == "weekdays":
        return "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR"
    if recurrence.startswith("every:"):
        try:
            n = int(recurrence.split(":", 1)[1])
        except ValueError:
            return None
        if n >= 2:
            return f"FREQ=DAILY;INTERVAL={n}"
    return None


def _event_lines(item: dict, dtstamp: str) -> list[str]:
    """One VEVENT from an item: all-day for due_date, timed for remind_at."""
    uid = f"mindcatch-{item['id']}@localhost"
    lines = ["BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{dtstamp}"]
    due = item.get("due_date")
    remind = item.get("remind_at")
    if due:
        lines.append(f"DTSTART;VALUE=DATE:{due.replace('-', '')}")
    elif remind:
        # floating local time (user's own machine, no tz DB dependency)
        lines.append("DTSTART:" + remind.replace("-", "").replace(":", "")[:15])
    summary = item["text"]
    if item.get("tags"):
        summary += " " + " ".join("#" + t.strip() for t in item["tags"].split(",") if t.strip())
    lines.append(f"SUMMARY:{_ics_escape(summary)}")
    if item.get("body"):
        lines.append(f"DESCRIPTION:{_ics_escape(item['body'][:800])}")
    rrule = _rrule(item.get("recurrence"))
    if rrule:
        lines.append(f"RRULE:{rrule}")
    lines.append("END:VEVENT")
    return lines


def items_to_ics(items: list[dict], dtstamp: str | None = None) -> str:
    """Build a complete VCALENDAR from items that have dates."""
    dtstamp = dtstamp or _dtstamp()
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", f"PRODID:{PRODID}",
             "CALSCALE:GREGORIAN", "METHOD:PUBLISH"]
    for item in items:
        if item.get("due_date") or item.get("remind_at"):
            lines.extend(_event_lines(item, dtstamp))
    lines.append("END:VCALENDAR")
    out = []
    for line in lines:
        out.extend(_fold(line))
    return "\r\n".join(out) + "\r\n"
