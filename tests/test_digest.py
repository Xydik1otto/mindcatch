"""Digest counts: what does 'today' look like? Pure logic over item dicts."""

from datetime import date

from app.logic.digest import digest_counts, due_today


def _item(**kw):
    base = {"id": 1, "type": "task", "text": "x", "status": "inbox",
            "remind_at": None, "due_date": None}
    base.update(kw)
    return base


TODAY = date(2026, 11, 5)
TODAY_ISO = "2026-11-05"


class TestDigestCounts:
    def test_counts_today_tasks(self):
        items = [_item(status="today"), _item(status="today"), _item(status="inbox")]
        assert digest_counts(items, TODAY)["tasks"] == 2

    def test_counts_reminders_due_today(self):
        items = [_item(type="reminder", remind_at=f"{TODAY_ISO}T15:00:00")]
        assert digest_counts(items, TODAY)["reminders"] == 1

    def test_reminder_other_day_not_counted(self):
        items = [_item(type="reminder", remind_at="2026-11-06T15:00:00")]
        assert digest_counts(items, TODAY)["reminders"] == 0

    def test_due_date_fallback_counts(self):
        items = [_item(type="reminder", due_date=TODAY_ISO)]
        assert digest_counts(items, TODAY)["reminders"] == 1

    def test_done_task_not_counted_as_today(self):
        items = [_item(status="done")]
        assert digest_counts(items, TODAY)["tasks"] == 0

    def test_date_and_shape(self):
        out = digest_counts([], TODAY)
        assert out == {"date": TODAY_ISO, "tasks": 0, "reminders": 0}


class TestDueToday:
    def test_returns_only_today_reminders(self):
        items = [
            _item(id=1, type="reminder", remind_at=f"{TODAY_ISO}T10:00:00"),
            _item(id=2, type="reminder", remind_at="2026-11-06T10:00:00"),
            _item(id=3, type="task", remind_at=f"{TODAY_ISO}T10:00:00"),
        ]
        due = due_today(items, TODAY)
        assert [i["id"] for i in due] == [1]

    def test_empty_when_nothing_due(self):
        assert due_today([_item()], TODAY) == []
