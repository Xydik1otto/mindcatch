"""Time tracking on tasks: estimates + timer sessions with history.

Pure functions; DB layer stores time_logs rows. All arithmetic is testable
with explicit datetimes.
"""

from __future__ import annotations

from datetime import datetime


def elapsed_minutes(started_at: str, ended_at: str) -> int:
    """Whole minutes between two ISO timestamps (0 for inverted/negative)."""
    start = datetime.fromisoformat(started_at)
    end = datetime.fromisoformat(ended_at)
    return max(0, round((end - start).total_seconds() / 60))


def total_minutes(logs: list[dict]) -> int:
    """Sum of closed log minutes (open logs with minutes=None count as 0)."""
    return sum(int(l.get("minutes") or 0) for l in logs)


def format_minutes(total: int) -> str:
    """'95' -> '1 год 35 хв' (UA), minutes-only below an hour."""
    h, m = divmod(int(total), 60)
    return f"{h} год {m} хв" if h else f"{m} хв"


def validate_estimate(minutes: int | None) -> int | None:
    if minutes is None:
        return None
    minutes = int(minutes)
    if minutes < 0:
        raise ValueError("estimate must be >= 0")
    if minutes > 24 * 60:
        raise ValueError("estimate over 24h is not a task, it is a lifestyle")
    return minutes


def estimate_status(estimate: int | None, spent: int) -> str:
    """'ok' | 'over' — did we blow the estimate?"""
    if estimate is None:
        return "no_estimate"
    return "over" if spent > estimate else "ok"
