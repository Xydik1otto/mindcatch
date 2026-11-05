"""Focus statistics: minutes per day from time_logs + SVG bar chart."""

import os
import sqlite3
import tempfile
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

_TMP = tempfile.mkdtemp(prefix="mindcatch-stats-")
os.environ["MINDCATCH_DB"] = os.path.join(_TMP, "test.db")

from app.logic import focus_stats  # noqa: E402
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


def _log(day: date, minutes: int, open_session: bool = False) -> dict:
    return {"started_at": f"{day.isoformat()}T10:00:00+00:00",
            "ended_at": None if open_session else f"{day.isoformat()}T11:00:00+00:00",
            "minutes": None if open_session else minutes}


class TestMinutesByDay:
    def test_sums_per_day_within_range(self):
        today = date(2026, 11, 5)
        logs = [_log(date(2026, 11, 5), 25), _log(date(2026, 11, 5), 30),
                _log(date(2026, 11, 3), 50),
                _log(date(2026, 10, 20), 999)]  # outside the window
        bars = focus_stats.minutes_by_day(logs, days=7, today=today)
        by_date = {b["date"]: b["minutes"] for b in bars}
        assert by_date["2026-11-05"] == 55
        assert by_date["2026-11-03"] == 50
        assert len(bars) == 7
        assert bars[-1]["date"] == "2026-11-05"
        assert bars[0]["date"] == "2026-10-30"

    def test_open_logs_ignored(self):
        today = date(2026, 11, 5)
        bars = focus_stats.minutes_by_day([_log(today, 0, open_session=True)], days=1, today=today)
        assert bars[0]["minutes"] == 0

    def test_empty_logs(self):
        bars = focus_stats.minutes_by_day([], days=3, today=date(2026, 11, 5))
        assert len(bars) == 3 and all(b["minutes"] == 0 for b in bars)


class TestSvg:
    def test_svg_contains_bars_and_labels(self):
        bars = [{"date": "2026-11-04", "minutes": 25}, {"date": "2026-11-05", "minutes": 50}]
        svg = focus_stats.bar_chart_svg(bars)
        assert svg.startswith("<svg")
        assert svg.count("<rect") == 2
        assert "04.11" in svg and "05.11" in svg
        assert ">50<" in svg

    def test_svg_zero_minutes_renders_frame(self):
        svg = focus_stats.bar_chart_svg([{"date": "2026-11-05", "minutes": 0}])
        assert "<rect" not in svg and "</svg>" in svg


class TestStatsAPI:
    def _insert_log(self, db_path, started, minutes):
        conn = sqlite3.connect(db_path)
        conn.execute("INSERT INTO time_logs (item_id, started_at, ended_at, minutes) "
                     "VALUES (1, ?, ?, ?)", (started, started, minutes))
        conn.commit()
        conn.close()

    def test_endpoint_shape_and_svg(self, client):
        item = client.post("/api/capture", json={"text": "фокус"}).json()
        client.post(f"/api/items/{item['id']}/timer/start")
        client.post(f"/api/items/{item['id']}/timer/stop")
        r = client.get("/api/stats/focus").json()
        assert set(r) == {"days", "total_minutes", "svg"}
        assert len(r["days"]) == 7
        assert "<svg" in r["svg"]
        assert r["days"][-1]["minutes"] >= 0

    def test_days_param_clamped(self, client):
        assert len(client.get("/api/stats/focus", params={"days": 0}).json()["days"]) == 1
        assert len(client.get("/api/stats/focus", params={"days": 500}).json()["days"]) == 90

    def test_counts_real_minutes_from_db(self, client):
        item = client.post("/api/capture", json={"text": "робота"}).json()
        self._insert_log(os.environ["MINDCATCH_DB"],
                         date.today().isoformat() + "T09:00:00", 90)
        r = client.get("/api/stats/focus").json()
        assert r["total_minutes"] >= 90
        assert r["days"][-1]["minutes"] >= 90
