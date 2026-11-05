"""Recurring tasks: daily/weekly spawn logic."""

from datetime import date

import pytest

from app.logic.recurring import next_date, spawn_next, validate


def _item(**kw):
    base = {"id": 7, "text": "винести сміття", "type": "task", "status": "today",
            "remind_at": None, "due_date": None, "recurrence": None}
    base.update(kw)
    return base


class TestValidate:
    def test_daily_weekly_ok(self):
        assert validate("daily") == "daily"
        assert validate("weekly") == "weekly"

    def test_none_and_empty_ok(self):
        assert validate(None) is None
        assert validate("") is None

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="unknown recurrence"):
            validate("monthly")


class TestNextDate:
    def test_daily_plus_one(self):
        assert next_date(date(2026, 11, 5), "daily") == date(2026, 11, 6)

    def test_weekly_plus_seven(self):
        assert next_date(date(2026, 11, 5), "weekly") == date(2026, 11, 12)

    def test_daily_month_rollover(self):
        assert next_date(date(2026, 11, 30), "daily") == date(2026, 12, 1)

    def test_weekly_year_rollover(self):
        assert next_date(date(2026, 12, 28), "weekly") == date(2027, 1, 4)


class TestSpawnNext:
    def test_non_recurring_returns_none(self):
        assert spawn_next(_item()) is None

    def test_daily_copies_text_type_and_resets_status(self):
        nxt = spawn_next(_item(recurrence="daily"))
        assert nxt["text"] == "винести сміття"
        assert nxt["type"] == "task"
        assert nxt["status"] == "inbox"
        assert nxt["recurrence"] == "daily"

    def test_daily_shifts_due_date(self):
        nxt = spawn_next(_item(recurrence="daily", due_date="2026-11-05"))
        assert nxt["due_date"] == "2026-11-06"

    def test_weekly_shifts_remind_at_preserving_time(self):
        nxt = spawn_next(_item(recurrence="weekly", remind_at="2026-11-05T15:00:00"))
        assert nxt["remind_at"] == "2026-11-12T15:00:00"

    def test_anchored_to_due_date_not_today(self):
        # scheduled in the past -> next occurrence follows the schedule
        nxt = spawn_next(_item(recurrence="weekly", due_date="2026-10-01"))
        assert nxt["due_date"] == "2026-10-08"

    def test_without_dates_uses_today(self):
        # no dates at all -> next occurrence reminds at 09:00 next day
        nxt = spawn_next(_item(recurrence="daily"), today=date(2026, 11, 5))
        assert nxt["due_date"] is None
        assert nxt["remind_at"] == "2026-11-06T09:00:00"

    def test_reminder_type_preserved(self):
        nxt = spawn_next(_item(type="reminder", recurrence="daily",
                               remind_at="2026-11-05T08:00:00"))
        assert nxt["type"] == "reminder"
        assert nxt["remind_at"] == "2026-11-06T08:00:00"
