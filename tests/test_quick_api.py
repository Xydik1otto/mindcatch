"""POST /api/quick — headless capture for curl/launchers/shortcuts."""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

_TMP = tempfile.mkdtemp(prefix="mindcatch-quick-")
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


class TestQuickCapture:
    def test_quick_captures_item(self, client):
        r = client.post("/api/quick", json={"text": "швидка думка"}).json()
        assert r["type"] == "note"
        assert r["status"] == "inbox"
        items = client.get("/api/items").json()
        assert [i["id"] for i in items] == [r["id"]]

    def test_quick_parses_dates_and_hashtags(self, client):
        r = client.post("/api/quick",
                        json={"text": "подзвонити мамі завтра 15:00 #сімʼя"}).json()
        assert r["type"] == "reminder"
        assert r["remind_at"].endswith("T15:00:00")
        assert "сімʼя" in r["tags"]

    def test_quick_accepts_tags_param(self, client):
        r = client.post("/api/quick",
                        json={"text": "замовити домен", "tags": ["side"]}).json()
        assert r["tags"] == "side"

    def test_quick_empty_text_400(self, client):
        assert client.post("/api/quick", json={"text": "   "}).status_code == 400

    def test_quick_same_pipeline_as_capture(self, client):
        a = client.post("/api/capture", json={"text": "купити каву завтра"}).json()
        b = client.post("/api/quick", json={"text": "купити каву завтра"}).json()
        assert a["type"] == b["type"] and a["due_date"] == b["due_date"]
