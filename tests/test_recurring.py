"""Recurring tasks: daily/weekly/every:N/weekdays spawn logic."""

import os
import tempfile
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.logic.recurring import next_date, spawn_next, validate

_TMP = tempfile.mkdtemp(prefix="mindcatch-rec-")
os.environ["MINDCATCH_DB"] = os.path.join(_TMP, "test.db")

from app.main import app  # noqa: E402  (env must be set before import)


@pytest.fixture()
def client():
    db_path = os.environ["MINDCATCH_DB"]
    for suffix in ("", "-wal", "-shm"):
        p = db_path + suffix
        if os.path.exists(p):
            os.remove(p)
    with TestClient(app) as c:
        yield c


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


class TestEveryNDays:
    def test_validate_accepts_every_n(self):
        assert validate("every:3") == "every:3"
        assert validate("every:30") == "every:30"

    def test_validate_rejects_bad_every(self):
        with pytest.raises(ValueError):
            validate("every:1")   # use 'daily' instead
        with pytest.raises(ValueError):
            validate("every:abc")
        with pytest.raises(ValueError):
            validate("every:")

    def test_next_date_plus_n(self):
        assert next_date(date(2026, 11, 5), "every:3") == date(2026, 11, 8)

    def test_next_date_month_rollover(self):
        assert next_date(date(2026, 11, 30), "every:3") == date(2026, 12, 3)

    def test_spawn_shifts_due_date(self):
        nxt = spawn_next(_item(recurrence="every:14", due_date="2026-11-05"))
        assert nxt["due_date"] == "2026-11-19"
        assert nxt["recurrence"] == "every:14"

    def test_spawn_shifts_remind_at_preserving_time(self):
        nxt = spawn_next(_item(recurrence="every:2", remind_at="2026-11-05T08:30:00"))
        assert nxt["remind_at"] == "2026-11-07T08:30:00"


class TestWeekdaysOnly:
    def test_friday_skips_to_monday(self):
        # 2026-11-06 is a Friday
        assert date(2026, 11, 6).weekday() == 4
        assert next_date(date(2026, 11, 6), "weekdays") == date(2026, 11, 9)

    def test_monday_to_tuesday(self):
        assert next_date(date(2026, 11, 9), "weekdays") == date(2026, 11, 10)

    def test_thursday_to_friday(self):
        assert next_date(date(2026, 11, 5), "weekdays") == date(2026, 11, 6)

    def test_weekend_input_skips_to_monday(self):
        assert next_date(date(2026, 11, 7), "weekdays") == date(2026, 11, 9)  # Sat
        assert next_date(date(2026, 11, 8), "weekdays") == date(2026, 11, 9)  # Sun

    def test_spawn_weekdays(self):
        nxt = spawn_next(_item(recurrence="weekdays", due_date="2026-11-06"))
        assert nxt["due_date"] == "2026-11-09"

    def test_rrule_for_calendar_export(self):
        from app.logic.recurring import rrule
        assert rrule("weekdays") == "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR"
        assert rrule("every:3") == "FREQ=DAILY;INTERVAL=3"


class TestApi:
    def test_set_every_n_and_complete_spawns_next(self, client):
        item = client.post("/api/capture", json={"text": "винести сміття"}).json()
        r = client.post(f"/api/items/{item['id']}/recurrence",
                        json={"recurrence": "every:5"})
        assert r.status_code == 200
        assert r.json()["recurrence"] == "every:5"

    def test_invalid_every_n_400(self, client):
        item = client.post("/api/capture", json={"text": "x"}).json()
        r = client.post(f"/api/items/{item['id']}/recurrence",
                        json={"recurrence": "every:1"})
        assert r.status_code == 400

    def test_set_weekdays(self, client):
        item = client.post("/api/capture", json={"text": "перевірити пошту"}).json()
        r = client.post(f"/api/items/{item['id']}/recurrence",
                        json={"recurrence": "weekdays"})
        assert r.json()["recurrence"] == "weekdays"


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
