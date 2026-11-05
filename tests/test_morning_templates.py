"""Morning warm-up templates (roadmap v0.3 «шаблони ранкової розгінки»):
pure logic + API endpoints that seed Today."""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

_TMP = tempfile.mkdtemp(prefix="mindcatch-morning-")
os.environ["MINDCATCH_DB"] = os.path.join(_TMP, "test.db")

from app.main import app  # noqa: E402  (env must be set before import)
from app.logic import morning_templates  # noqa: E402


@pytest.fixture()
def client():
    db_path = os.environ["MINDCATCH_DB"]
    for suffix in ("", "-wal", "-shm"):
        p = db_path + suffix
        if os.path.exists(p):
            os.remove(p)
    with TestClient(app) as c:
        yield c


class TestTemplatesLogic:
    def test_catalogue_has_localized_names_and_steps(self):
        tpls = morning_templates.list_templates()
        assert len(tpls) >= 2
        for t in tpls:
            assert t["id"] and t["name_ua"] and t["name_en"]
            assert t["steps"] >= 1

    def test_unknown_template_returns_none(self):
        assert morning_templates.template_steps("no-such") is None

    def test_steps_are_text_and_type_only(self):
        for s in morning_templates.template_steps("warmup"):
            assert set(s) == {"text", "type"}
            assert s["type"] in ("task", "note", "reminder")

    def test_no_russian_in_templates(self):
        import json
        blob = json.dumps(morning_templates.TEMPLATES, ensure_ascii=False)
        assert not (set("ыъэЫЪЭ") & set(blob))


class TestTemplatesApi:
    def test_list_endpoint(self, client):
        r = client.get("/api/morning/templates").json()
        ids = [t["id"] for t in r]
        assert "warmup" in ids and "reset" in ids

    def test_apply_seeds_today(self, client):
        r = client.post("/api/morning/apply",
                        json={"template_id": "warmup"}).json()
        assert len(r["items"]) == 4
        assert all(i["status"] == "today" for i in r["items"])
        today = client.get("/api/today").json()
        assert [i["id"] for i in today] == [i["id"] for i in r["items"]]

    def test_apply_can_be_rerun_after_a_bad_day(self, client):
        first = client.post("/api/morning/apply",
                            json={"template_id": "reset"}).json()
        second = client.post("/api/morning/apply",
                             json={"template_id": "reset"}).json()
        ids = {i["id"] for i in first["items"]} | \
              {i["id"] for i in second["items"]}
        assert len(ids) == 6  # fresh set appended, no overwrite

    def test_apply_unknown_template_400(self, client):
        r = client.post("/api/morning/apply", json={"template_id": "zzz"})
        assert r.status_code == 400
        assert "unknown template" in r.json()["detail"]

    def test_applied_items_render_in_today_view(self, client):
        client.post("/api/morning/apply", json={"template_id": "deep-work"})
        today = client.get("/api/today").json()
        texts = [i["text"] for i in today]
        assert any("головна задача" in t for t in texts)
