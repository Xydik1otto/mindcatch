"""Data safety: one-click CSV export + delete/archive warnings in UI."""

import csv
import io
import os
import tempfile

import pytest
from fastapi.testclient import TestClient

_TMP = tempfile.mkdtemp(prefix="mindcatch-csv-")
os.environ["MINDCATCH_DB"] = os.path.join(_TMP, "test.db")

from app.logic.csv_export import items_to_csv  # noqa: E402
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


class TestCsvLogic:
    def test_header_and_rows(self):
        items = [{"id": 1, "type": "task", "text": "здати звіт", "status": "today",
                  "due_date": "2026-11-10", "remind_at": None, "tags": "робота",
                  "estimate_minutes": 45, "spent_minutes": 12,
                  "created_at": "2026-11-05T10:00:00+00:00",
                  "updated_at": "2026-11-05T10:00:00+00:00"}]
        csv_text = items_to_csv(items)
        rows = list(csv.reader(io.StringIO(csv_text)))
        assert rows[0][2] == "text" and rows[0][3] == "status"
        assert rows[1][2] == "здати звіт" and rows[1][4] == "2026-11-10"

    def test_comma_in_text_is_escaped(self):
        items = [{"id": 1, "type": "note", "text": "купити: хліб, молоко",
                  "status": "inbox", "due_date": None, "remind_at": None,
                  "tags": None, "estimate_minutes": None, "spent_minutes": None,
                  "created_at": "", "updated_at": ""}]
        rows = list(csv.reader(io.StringIO(items_to_csv(items))))
        assert rows[1][2] == "купити: хліб, молоко"  # quoting keeps it one field

    def test_utf8_bom_for_excel(self):
        assert items_to_csv([]).startswith("﻿")


class TestCsvApi:
    def test_endpoint(self, client):
        client.post("/api/capture", json={"text": "здати звіт завтра #робота"})
        r = client.get("/api/export/items.csv")
        assert r.status_code == 200
        assert "text/csv" in r.headers["content-type"]
        assert "attachment" in r.headers["content-disposition"]
        body = r.content.decode("utf-8-sig")  # BOM-aware decode
        assert "здати звіт" in body

    def test_empty_db_has_header_only(self, client):
        body = client.get("/api/export/items.csv").content.decode("utf-8-sig")
        assert body.count("\r\n") == 1  # header row only (with trailing newline)


class TestSafetyUi:
    def test_index_links_all_export_formats(self, client):
        html = client.get("/").text
        for href in ("/api/export", "/api/export/items.csv",
                     "/api/export/calendar.ics", "/api/export/todoist.md",
                     "/api/export/markdown"):
            assert href in html, f"one-click export link missing: {href}"

    def test_archive_move_asks_confirmation(self, client):
        js = client.get("/app.js").text
        assert "archive_confirm" in js
        assert 'confirm(' in js
