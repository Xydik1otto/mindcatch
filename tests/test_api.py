"""API tests: capture date parsing, digest, recurring complete (TestClient)."""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

_TMP = tempfile.mkdtemp(prefix="mindcatch-test-")
os.environ["MINDCATCH_DB"] = os.path.join(_TMP, "test.db")

from app.main import app  # noqa: E402  (env must be set before import)


@pytest.fixture()
def client():
    # fresh DB per test
    db_path = os.environ["MINDCATCH_DB"]
    for suffix in ("", "-wal", "-shm"):
        p = db_path + suffix
        if os.path.exists(p):
            os.remove(p)
    with TestClient(app) as c:
        yield c


class TestCaptureParsing:
    def test_ua_reminder_parses_remind_at(self, client):
        r = client.post("/api/capture", json={"text": "подзвонити мамі завтра 15:00"}).json()
        assert r["type"] == "reminder"
        assert r["remind_at"].endswith("T15:00:00")
        assert r["due_date"]

    def test_plain_note_has_no_dates(self, client):
        r = client.post("/api/capture", json={"text": "просто думка про проєкт"}).json()
        assert r["type"] == "note"
        assert r["remind_at"] is None and r["due_date"] is None

    def test_empty_text_400(self, client):
        assert client.post("/api/capture", json={"text": "  "}).status_code == 400


class TestDigest:
    def test_digest_shape(self, client):
        d = client.get("/api/digest").json()
        assert set(d) >= {"date", "tasks", "reminders", "due_today"}

    def test_digest_counts_today_tasks(self, client):
        item = client.post("/api/capture", json={"text": "написати звіт"}).json()
        client.post(f"/api/items/{item['id']}/move", json={"status": "today"})
        d = client.get("/api/digest").json()
        assert d["tasks"] >= 1


class TestTimeTracker:
    def test_estimate_set_and_get(self, client):
        item = client.post("/api/capture", json={"text": "написати звіт"}).json()
        r = client.post(f"/api/items/{item['id']}/estimate", json={"minutes": 45}).json()
        assert r["estimate_minutes"] == 45

    def test_negative_estimate_400(self, client):
        item = client.post("/api/capture", json={"text": "задача"}).json()
        assert client.post(f"/api/items/{item['id']}/estimate",
                           json={"minutes": -1}).status_code == 400

    def test_timer_start_stop_history(self, client):
        item = client.post("/api/capture", json={"text": "робота з фокусом"}).json()
        iid = item["id"]
        assert client.post(f"/api/items/{iid}/timer/start").json()["running"] is True
        # double start -> 409
        assert client.post(f"/api/items/{iid}/timer/start").status_code == 409
        stop = client.post(f"/api/items/{iid}/timer/stop").json()
        assert stop["running"] is False
        state = client.get(f"/api/items/{iid}/timer").json()
        assert state["running"] is False
        assert len(state["logs"]) == 1
        assert state["total_minutes"] >= 0

    def test_stop_without_start_409(self, client):
        item = client.post("/api/capture", json={"text": "ще задача"}).json()
        assert client.post(f"/api/items/{item['id']}/timer/stop").status_code == 409

    def test_items_list_includes_spent_and_running(self, client):
        item = client.post("/api/capture", json={"text": "з таймером"}).json()
        client.post(f"/api/items/{item['id']}/timer/start")
        items = client.get("/api/items").json()
        row = [i for i in items if i["id"] == item["id"]][0]
        assert row["spent_minutes"] is not None or row["timer_running"]


class TestNoteBody:
    def test_save_and_read_body(self, client):
        item = client.post("/api/capture", json={"text": "ідея для поста"}).json()
        r = client.put(f"/api/items/{item['id']}/body",
                       json={"body": "# Заголовок\n- пункт"})
        assert r.status_code == 200
        assert r.json()["body"] == "# Заголовок\n- пункт"
        items = client.get("/api/items").json()
        assert items[0]["body"].startswith("# Заголовок")

    def test_md_preview_renders(self, client):
        r = client.post("/api/md/preview", json={"body": "**жирний**"}).json()
        assert "<strong>жирний</strong>" in r["html"]

    def test_md_preview_escapes_html(self, client):
        r = client.post("/api/md/preview", json={"body": "<script>x</script>"}).json()
        assert "<script>" not in r["html"]

    def test_body_missing_404(self, client):
        assert client.put("/api/items/99999/body", json={"body": "x"}).status_code == 404


class TestRecurring:
    def test_set_recurrence_and_complete_spawns_next(self, client):
        item = client.post("/api/capture", json={"text": "винести сміття"}).json()
        r = client.post(f"/api/items/{item['id']}/recurrence",
                        json={"recurrence": "daily"}).json()
        assert r["recurrence"] == "daily"

        done = client.post(f"/api/items/{item['id']}/complete").json()
        assert done["completed"]["status"] == "done"
        nxt = done["next"]
        assert nxt["text"] == "винести сміття"
        assert nxt["recurrence"] == "daily"
        assert nxt["status"] == "inbox"

    def test_complete_non_recurring_no_spawn(self, client):
        item = client.post("/api/capture", json={"text": "разова задача"}).json()
        done = client.post(f"/api/items/{item['id']}/complete").json()
        assert done["next"] is None
        assert done["completed"]["status"] == "done"

    def test_invalid_recurrence_400(self, client):
        item = client.post("/api/capture", json={"text": "щось"}).json()
        r = client.post(f"/api/items/{item['id']}/recurrence",
                        json={"recurrence": "monthly"})
        assert r.status_code == 400

    def test_complete_missing_404(self, client):
        assert client.post("/api/items/99999/complete").status_code == 404
