"""Task export to Markdown / Todoist-compatible format.

Two flavours:
  - ``to_markdown(items)``  — grouped by status, plain Markdown checklists.
  - ``to_todoist(items)``   — one flat checklist that Todoist understands:
    ``- [ ] task @tag p1 📅 2026-11-10``. When pasted into Todoist (or added
    via quick add), ``@tag`` becomes a label, ``p1..p4`` a priority and
    ``📅 YYYY-MM-DD`` a due date — no data is lost in the transfer.
"""

from __future__ import annotations

STATUS_TITLES = ("inbox", "today", "week", "someday", "done")

_PRIORITIES = {1: "p1", 2: "p2", 3: "p3", 4: "p4"}


def _line(item: dict) -> str:
    """One Todoist-compatible checklist line for an item."""
    parts = [f"- [{'x' if item['status'] == 'done' else ' '}] {item['text']}"]
    for tag in (item.get("tags") or "").split(","):
        tag = tag.strip()
        if tag:
            parts.append(f"@{tag.replace(' ', '-')}")  # Todoist labels: no spaces
    prio = _PRIORITIES.get(item.get("priority") or 4)
    if prio and prio != "p4":
        parts.append(prio)
    if item.get("due_date"):
        parts.append(f"📅 {item['due_date']}")
    if item.get("recurrence"):
        parts.append(f"↻ {_recurrence_hint(item['recurrence'])}")
    return " ".join(parts)


def _recurrence_hint(recurrence: str) -> str:
    """Human hint Todoist keeps as text (its own RRULE lives in ICS export)."""
    if recurrence == "daily":
        return "every day"
    if recurrence == "weekly":
        return "every week"
    if recurrence == "weekdays":
        return "every weekday"
    if recurrence.startswith("every:"):
        return f"every {recurrence.split(':', 1)[1]} days"
    return recurrence


def to_todoist(items: list[dict]) -> str:
    """Flat checklist, open tasks first, done last."""
    ordered = [i for i in items if i["status"] != "done"] + \
              [i for i in items if i["status"] == "done"]
    lines = ["# Mindcatch tasks", ""]
    lines.extend(_line(i) for i in ordered)
    return "\n".join(lines) + "\n"


def to_markdown(items: list[dict]) -> str:
    """Markdown export grouped by status (inbox → done)."""
    lines = ["# Mindcatch export", ""]
    for status in STATUS_TITLES:
        group = [i for i in items if i["status"] == status]
        if not group:
            continue
        title = {"inbox": "📥 Inbox", "today": "☀️ Today", "week": "🗓 Week",
                 "someday": "🔮 Someday", "done": "✅ Done"}[status]
        lines.append(f"## {title} ({len(group)})")
        lines.append("")
        for item in group:
            line = _line(item)
            extra = []
            if item.get("remind_at") and not item.get("due_date"):
                extra.append(f"🔔 {item['remind_at'][:16]}")
            if item.get("body"):
                extra.append("> " + item["body"].replace("\n", "\n> "))
            lines.append(line + (" — " + " · ".join(extra) if extra else ""))
        lines.append("")
    return "\n".join(lines)
