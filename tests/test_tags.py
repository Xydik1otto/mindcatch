"""Tags/projects: hashtag extraction, normalization, history hints, filter."""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

_TMP = tempfile.mkdtemp(prefix="mindcatch-tags-")
os.environ["MINDCATCH_DB"] = os.path.join(_TMP, "test.db")

from app.logic import tags as tags_logic  # noqa: E402
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


class TestTagLogic:
    def test_extract_hashtags_strips_and_normalizes(self):
        clean, tags = tags_logic.extract_hashtags("купити хліб #покупки #Home")
        assert clean == "купити хліб"
        assert tags == ["покупки", "home"]

    def test_markdown_heading_is_not_a_tag(self):
        clean, tags = tags_logic.extract_hashtags("# Заголовок звіту")
        assert clean == "# Заголовок звіту"
        assert tags == []

    def test_normalize_dedupes_and_caps(self):
        assert tags_logic.normalize(["#A", "a", " b c ", ""]) == ["a", "b-c"]
        assert len(tags_logic.normalize([f"t{i}" for i in range(50)])) == tags_logic.MAX_TAGS

    def test_roundtrip_column(self):
        col = tags_logic.join_tags(["Проєкт-X", "home"])
        assert tags_logic.parse_column(col) == ["проєкт-x", "home"]


class TestTagsAPI:
    def test_capture_extracts_hashtags(self, client):
        r = client.post("/api/capture", json={"text": "подзвонити бухгалтерії #робота"}).json()
        assert r["tags"] == "робота"
        assert "#" not in r["text"]
        assert "бухгалтерії" in r["text"]

    def test_hash_space_stays_in_text(self, client):
        r = client.post("/api/capture", json={"text": "# заголовок не тег"}).json()
        assert r["tags"] in ("", None)
        assert "# заголовок" in r["text"]

    def test_capture_explicit_tags_param(self, client):
        r = client.post("/api/capture",
                        json={"text": "придбати полицю", "tags": ["Home", "#home"]}).json()
        assert r["tags"] == "home"

    def test_set_and_clear_tags(self, client):
        item = client.post("/api/capture", json={"text": "задача"}).json()
        r = client.put(f"/api/items/{item['id']}/tags", json={"tags": ["Робота", "urgent"]}).json()
        assert r["tags"] == "робота,urgent"
        r = client.put(f"/api/items/{item['id']}/tags", json={"tags": []}).json()
        assert r["tags"] in ("", None)

    def test_set_tags_string_form(self, client):
        item = client.post("/api/capture", json={"text": "задача"}).json()
        r = client.put(f"/api/items/{item['id']}/tags", json={"tags": "a, b ,#c"}).json()
        assert r["tags"] == "a,b,c"

    def test_set_tags_missing_404(self, client):
        assert client.put("/api/items/99999/tags", json={"tags": ["x"]}).status_code == 404

    def test_suggestions_rank_by_usage(self, client):
        for text in ("раз #work", "два #work #home", "три #home"):
            client.post("/api/capture", json={"text": text})
        sug = client.get("/api/tags").json()
        by_tag = {s["tag"]: s["count"] for s in sug}
        assert by_tag["work"] == 2 and by_tag["home"] == 2
        assert sug[0]["count"] >= sug[-1]["count"]

    def test_filter_by_tag(self, client):
        a = client.post("/api/capture", json={"text": "з tag", "tags": ["work"]}).json()
        b = client.post("/api/capture", json={"text": "без tag"}).json()
        client.post(f"/api/items/{b['id']}/move", json={"status": "today"})
        inbox = client.get("/api/items?status=inbox&tag=work").json()
        assert [i["id"] for i in inbox] == [a["id"]]
        everything = client.get("/api/items?tag=WORK").json()  # case-insensitive
        assert [i["id"] for i in everything] == [a["id"]]
        assert client.get("/api/items?tag=work&status=today").json() == []
