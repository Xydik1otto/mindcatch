"""Search (LIKE over text/body, Cyrillic-safe) + archive of Done items."""

import os
import sqlite3
import tempfile

import pytest
from fastapi.testclient import TestClient

_TMP = tempfile.mkdtemp(prefix="mindcatch-search-")
DB_PATH = os.path.join(_TMP, "test.db")
os.environ["MINDCATCH_DB"] = DB_PATH

from app.db import search_items  # noqa: E402
from app.main import app  # noqa: E402  (env must be set before import)


@pytest.fixture()
def client():
    db_path = os.environ["MINDCATCH_DB"]  # active shared test DB
    for suffix in ("", "-wal", "-shm"):
        p = db_path + suffix
        if os.path.exists(p):
            os.remove(p)
    with TestClient(app) as c:
        yield c


def _seed(client, texts):
    return [client.post("/api/capture", json={"text": t}).json() for t in texts]


class TestSearch:
    def test_search_by_title(self, client):
        a, b = _seed(client, ["купити каву", "подати звіт"])
        hits = client.get("/api/search", params={"q": "каву"}).json()
        assert [i["id"] for i in hits] == [a["id"]]

    def test_search_case_insensitive_cyrillic(self, client):
        a, = _seed(client, ["Підготувати ЗВІТ"])
        hits = client.get("/api/search", params={"q": "звіт"}).json()
        assert [i["id"] for i in hits] == [a["id"]]

    def test_search_note_body(self, client):
        a, = _seed(client, ["нотатка про проєкт"])
        client.put(f"/api/items/{a['id']}/body", json={"body": "деталі: сервер на Raspberry Pi"})
        hits = client.get("/api/search", params={"q": "raspberry"}).json()
        assert [i["id"] for i in hits] == [a["id"]]

    def test_search_found_in_done_archive_too(self, client):
        a, = _seed(client, ["стара виконана задача про каву"])
        client.post(f"/api/items/{a['id']}/complete")
        hits = client.get("/api/search", params={"q": "каву"}).json()
        assert [i["id"] for i in hits] == [a["id"]]

    def test_empty_query_returns_empty_list(self, client):
        _seed(client, ["щось"])
        assert client.get("/api/search", params={"q": "  "}).json() == []

    def test_no_match(self, client):
        _seed(client, ["щось"])
        assert client.get("/api/search", params={"q": "відсутнєслово"}).json() == []

    def test_db_layer_direct(self, monkeypatch, tmp_path):
        monkeypatch.setenv("MINDCATCH_DB", str(tmp_path / "x.db"))
        conn = sqlite3.connect(str(tmp_path / "x.db"))
        conn.row_factory = sqlite3.Row
        from app.db import init_db
        init_db(conn)
        conn.execute("INSERT INTO items (type, text, status, created_at, updated_at) VALUES ('task','Купити каву','inbox','2026-01-01','2026-01-01')")
        conn.commit()
        assert [i["text"] for i in search_items(conn, "каву")] == ["Купити каву"]
        assert search_items(conn, "відсутнєслово") == []
        conn.close()


class TestArchive:
    def test_archive_returns_done_newest_first(self, client):
        a, b = _seed(client, ["перша", "друга"])
        client.post(f"/api/items/{a['id']}/complete")
        client.post(f"/api/items/{b['id']}/complete")
        arch = client.get("/api/archive").json()
        assert [i["id"] for i in arch] == [b["id"], a["id"]]
        assert all(i["status"] == "done" for i in arch)

    def test_archive_excludes_active_items(self, client):
        _seed(client, ["активна в inbox"])
        assert client.get("/api/archive").json() == []

    def test_search_and_archive_endpoints_200(self, client):
        assert client.get("/api/search?q=x").status_code == 200
        assert client.get("/api/archive").status_code == 200
