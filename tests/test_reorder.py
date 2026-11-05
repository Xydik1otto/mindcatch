"""Drag-reorder in Today: sort_order column, POST /api/today/reorder,
manual order wins over insertion order."""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

_TMP = tempfile.mkdtemp(prefix="mindcatch-reorder-")
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


def make_today(client, text):
    item = client.post("/api/quick", json={"text": text}).json()
    client.post(f"/api/items/{item['id']}/move", json={"status": "today"})
    return item["id"]


@pytest.fixture()
def three_today(client):
    return [make_today(client, t) for t in ("задача А", "задача Б", "задача В")]


class TestReorderApi:
    def test_reorder_persists_order(self, client, three_today):
        r = client.post("/api/today/reorder",
                        json={"order": [three_today[2], three_today[0],
                                        three_today[1]]})
        assert r.status_code == 200
        assert [i["id"] for i in r.json()] == [three_today[2], three_today[0],
                                               three_today[1]]
        # order survives a fresh read
        again = client.get("/api/today").json()
        assert [i["id"] for i in again] == [three_today[2], three_today[0],
                                            three_today[1]]

    def test_partial_order_appends_the_rest(self, client, three_today):
        r = client.post("/api/today/reorder",
                        json={"order": [three_today[1]]}).json()
        assert [i["id"] for i in r] == [three_today[1], three_today[0],
                                        three_today[2]]

    def test_new_today_item_sorts_last(self, client, three_today):
        client.post("/api/today/reorder", json={"order": [three_today[2]]})
        fresh = make_today(client, "нова задача")
        ids = [i["id"] for i in client.get("/api/today").json()]
        assert ids == [three_today[2], three_today[0], three_today[1], fresh]

    def test_unknown_id_400(self, client, three_today):
        r = client.post("/api/today/reorder", json={"order": [99999]})
        assert r.status_code == 400
        assert "not in Today" in r.json()["detail"]

    def test_duplicate_ids_400(self, client, three_today):
        r = client.post("/api/today/reorder",
                        json={"order": [three_today[0], three_today[0]]})
        assert r.status_code == 400
        assert "duplicate" in r.json()["detail"]

    def test_inbox_item_cannot_be_reordered_into_today(self, client, three_today):
        other = client.post("/api/quick", json={"text": "ще в інбоксі"}).json()
        r = client.post("/api/today/reorder", json={"order": [other["id"]]})
        assert r.status_code == 400

    def test_other_views_keep_insertion_order(self, client, three_today):
        client.post("/api/today/reorder",
                    json={"order": [three_today[2], three_today[0],
                                    three_today[1]]})
        inbox = client.post("/api/quick", json={"text": "inbox item"}).json()
        items = client.get("/api/items").json()
        today_block = [i["id"] for i in items if i["status"] == "today"]
        assert today_block == [three_today[2], three_today[0], three_today[1]]


class TestReorderUi:
    def test_today_items_are_draggable(self, client):
        js = client.get("/app.js").text
        assert 'view === "today"' in js
        assert "draggable" in js
        assert "/api/today/reorder" in js

    def test_index_links_app_js(self, client):
        assert "/app.js" in client.get("/").text
