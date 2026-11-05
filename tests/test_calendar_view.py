"""Calendar view of a month: month grid logic + GET /api/calendar."""

import os
import tempfile
from datetime import date

import pytest
from fastapi.testclient import TestClient

_TMP = tempfile.mkdtemp(prefix="mindcatch-calendar-")
os.environ["MINDCATCH_DB"] = os.path.join(_TMP, "test.db")

from app.main import app  # noqa: E402  (env must be set before import)
from app.logic import calendar_view  # noqa: E402


@pytest.fixture()
def client():
    db_path = os.environ["MINDCATCH_DB"]
    for suffix in ("", "-wal", "-shm"):
        p = db_path + suffix
        if os.path.exists(p):
            os.remove(p)
    with TestClient(app) as c:
        yield c


class TestMonthGrid:
    def test_november_2026_shape(self):
        weeks = calendar_view.month_grid(2026, 11)
        assert all(len(w) == 7 for w in weeks)
        flat = [c["date"] for w in weeks for c in w if c]
        # every in-month day present exactly once, in order
        in_month = [d for d in flat if d.startswith("2026-11")]
        assert in_month[0] == "2026-11-01" and in_month[-1] == "2026-11-30"
        assert len(in_month) == 30
        # padding days belong to October or December
        outside = [c["date"] for w in weeks for c in w
                   if c and not c["in_month"]]
        assert all(d[:7] in ("2026-10", "2026-12") for d in outside)

    def test_monday_first_weeks(self):
        weeks = calendar_view.month_grid(2026, 11)
        first_real = next(c for w in weeks for c in w if c)
        # 2026-11-01 is a Sunday -> it is the last cell of a week
        assert weeks[0][-1]["date"] == "2026-11-01"

    def test_february_leap_year(self):
        weeks = calendar_view.month_grid(2028, 2)
        in_month = [c["date"] for w in weeks for c in w if c]
        assert in_month[-1] == "2028-02-29"

    def test_bad_month_raises(self):
        with pytest.raises(ValueError):
            calendar_view.month_payload(2026, 13, [])


class TestItemsByDay:
    def test_due_date_and_remind_at_map_to_days(self):
        items = [
            {"id": 1, "text": "купити", "type": "task", "status": "today",
             "due_date": "2026-11-10", "remind_at": None},
            {"id": 2, "text": "нагадування", "type": "reminder",
             "status": "inbox", "due_date": None,
             "remind_at": "2026-11-05T15:00:00"},
            {"id": 3, "text": "думка", "type": "note", "status": "inbox",
             "due_date": None, "remind_at": None},
        ]
        by_day = calendar_view.items_by_day(items)
        assert [i["id"] for i in by_day["2026-11-10"]] == [1]
        assert [i["id"] for i in by_day["2026-11-05"]] == [2]
        assert len(by_day) == 2

    def test_done_items_are_skipped(self):
        items = [{"id": 1, "text": "x", "type": "task", "status": "done",
                  "due_date": "2026-11-10", "remind_at": None}]
        assert calendar_view.items_by_day(items) == {}


class TestCalendarApi:
    def test_grid_and_items(self, client):
        client.post("/api/quick", json={"text": "купити каву завтра"})
        r = client.get("/api/calendar", params={"year": 2026, "month": 11})
        assert r.status_code == 200
        data = r.json()
        assert data["year"] == 2026 and data["month"] == 11
        assert all(len(w) == 7 for w in data["weeks"])
        today_items = client.get("/api/items").json()
        due = today_items[0]["due_date"]
        assert [i["id"] for i in data["items"][due]] == [today_items[0]["id"]]

    def test_defaults_to_current_month(self, client):
        data = client.get("/api/calendar").json()
        t = date.today()
        assert (data["year"], data["month"]) == (t.year, t.month)

    def test_bad_month_400(self, client):
        assert client.get("/api/calendar",
                          params={"year": 2026, "month": 13}).status_code == 400
        assert client.get("/api/calendar",
                          params={"year": 2026, "month": 0}).status_code == 400

    def test_undated_items_do_not_crash(self, client):
        client.post("/api/quick", json={"text": "просто думка без дати"})
        r = client.get("/api/calendar")
        assert r.status_code == 200
        assert r.json()["items"] == {}

    def test_ui_has_calendar_view(self, client):
        html = client.get("/").text
        assert 'data-view="calendar"' in html
        js = client.get("/app.js").text
        assert "/api/calendar" in js
