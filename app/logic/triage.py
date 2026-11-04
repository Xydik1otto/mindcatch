"""Triage state machine: inbox -> today/week/someday/done (GTD-style)."""

from __future__ import annotations

STATUSES = ("inbox", "today", "week", "someday", "done")

# Allowed transitions. Everything can reach "done"; anything can be re-opened
# back to a live bucket or pushed back to inbox.
ALLOWED_TRANSITIONS = {
    "inbox": {"today", "week", "someday", "done"},
    "today": {"week", "someday", "inbox", "done"},
    "week": {"today", "someday", "inbox", "done"},
    "someday": {"today", "week", "inbox", "done"},
    "done": {"today", "week", "someday", "inbox"},
}


def can_move(current: str, target: str) -> bool:
    if current not in STATUSES or target not in STATUSES:
        return False
    if current == target:
        return False
    return target in ALLOWED_TRANSITIONS[current]


def move(item: dict, target: str) -> dict:
    """Return a new item dict with the updated status.

    Raises ValueError with a clear message for invalid transitions or unknown
    statuses — the API layer maps this to HTTP 400.
    """
    current = item.get("status")
    if current not in STATUSES:
        raise ValueError(f"unknown status: {current!r}")
    if target not in STATUSES:
        raise ValueError(f"unknown target status: {target!r}")
    if current == target:
        raise ValueError(f"item is already in {target!r}")
    if not can_move(current, target):
        raise ValueError(f"transition {current!r} -> {target!r} is not allowed")
    return {**item, "status": target}
