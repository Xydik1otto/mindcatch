"""ICS calendar export: pure logic + API endpoint."""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

_TMP = tempfile.mkdtemp(prefix="mindcatch-ics-")
os.environ["MINDCATCH_DB"] = os.path.join(_TMP, "test.db")

from app.logic.ics_export import _ics_escape, _rrule, items_to_ics  # noqa: E402
from app.main import app  # noqa: E402  (env must be set before import)

DTSTAMP = "20261105T120000Z"


@pytest.fixture()
def client():
    db_path = os.environ["MINDCATCH_DB"]
    for suffix in ("", "-wal", "-shm"):
        p = db_path + suffix
        if os.path.exists(p):
            os.remove(p)
    with TestClient(app) as c:
        yield c


def _capture(client, text, **fields):
    r = client.post("/api/capture", json={"text": text}).json()
    if "recurrence" in fields:
        client.post(f"/api/items/{r['id']}/recurrence", json={"recurrence": fields["recurrence"]})
    return r


class TestPureLogic:
    def test_escape_text_specials(self):
        assert _ics_escape("a,b;c") == r"a\,b\;c"
        assert _ics_escape("line1\nline2") == r"line1\nline2"

    def test_rrule_mapping(self):
        assert _rrule("daily") == "FREQ=DAILY"
        assert _rrule("weekly") == "FREQ=WEEKLY"
        assert _rrule("weekdays") == "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR"
        assert _rrule("every:3") == "FREQ=DAILY;INTERVAL=3"
        assert _rrule(None) is None

    def test_structure_and_all_day_event(self):
        items = [{"id": 1, "text": "здати звіт", "type": "task", "tags": "робота",
                  "body": None, "due_date": "2026-11-10", "remind_at": None,
                  "recurrence": None}]
        ics = items_to_ics(items, dtstamp=DTSTAMP)
        assert ics.startswith("BEGIN:VCALENDAR")
        assert "VERSION:2.0" in ics and "PRODID:-//mindcatch//" in ics
        assert "BEGIN:VEVENT" in ics and "END:VEVENT" in ics
        assert "UID:mindcatch-1@localhost" in ics
        assert "DTSTART;VALUE=DATE:20261110" in ics
        assert "SUMMARY:здати звіт #робота" in ics
        assert ics.endswith("END:VCALENDAR\r\n")

    def test_dated_items_only(self):
        items = [{"id": 1, "text": "з датою", "due_date": "2026-11-10",
                  "remind_at": None, "recurrence": None, "tags": "", "body": None},
                 {"id": 2, "text": "без дати", "due_date": None,
                  "remind_at": None, "recurrence": None, "tags": "", "body": None}]
        ics = items_to_ics(items, dtstamp=DTSTAMP)
        assert ics.count("BEGIN:VEVENT") == 1

    def test_remind_at_becomes_timed_event(self):
        items = [{"id": 3, "text": "подзвонити", "due_date": None,
                  "remind_at": "2026-11-10T15:00:00", "recurrence": None,
                  "tags": "", "body": None}]
        ics = items_to_ics(items, dtstamp=DTSTAMP)
        assert "DTSTART:20261110T150000" in ics

    def test_crlf_line_endings(self):
        items = [{"id": 1, "text": "x", "due_date": "2026-11-10", "remind_at": None,
                  "recurrence": None, "tags": "", "body": None}]
        assert "\r\n" in items_to_ics(items, dtstamp=DTSTAMP)


class TestApi:
    def test_endpoint_serves_calendar(self, client):
        client.post("/api/capture", json={"text": "здати звіт завтра"})
        r = client.get("/api/export/calendar.ics")
        assert r.status_code == 200
        assert "text/calendar" in r.headers["content-type"]
        assert "attachment" in r.headers["content-disposition"]
        assert r.text.startswith("BEGIN:VCALENDAR")
        assert "BEGIN:VEVENT" in r.text

    def test_empty_db_still_valid_calendar(self, client):
        r = client.get("/api/export/calendar.ics")
        assert r.status_code == 200
        assert "BEGIN:VCALENDAR" in r.text
        assert "BEGIN:VEVENT" not in r.text
