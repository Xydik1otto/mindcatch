"""i18n: UA/EN switcher — dictionaries complete, no Russian, UI wired up."""

import json
import os
import tempfile

import pytest
from fastapi.testclient import TestClient

_TMP = tempfile.mkdtemp(prefix="mindcatch-i18n-")
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


@pytest.fixture()
def dicts(client):
    return client.get("/i18n.json").json()


RUSSIAN_LETTERS = set("ыъэЫЪЭ")


class TestDictionaries:
    def test_i18n_json_served_and_valid(self, client):
        r = client.get("/i18n.json")
        assert r.status_code == 200
        d = r.json()
        assert set(d) == {"ua", "en"}

    def test_ua_and_en_have_identical_key_sets(self, dicts):
        assert set(dicts["ua"]) == set(dicts["en"])
        assert len(dicts["ua"]) >= 40, "every UI string must be in the dictionary"

    def test_no_russian_anywhere(self, dicts):
        blob = json.dumps(dicts, ensure_ascii=False)
        russian = RUSSIAN_LETTERS & set(blob)
        assert not russian, f"Russian letters found: {russian}"

    def test_ua_values_are_ukrainian(self, dicts):
        sample = dicts["ua"]["digest"]
        assert "Сьогодні" in sample  # Ukrainian 'і', not Russian 'ы'

    def test_en_values_have_no_cyrillic(self, dicts):
        blob = json.dumps(dicts["en"], ensure_ascii=False)
        assert not any("\u0400" <= ch <= "\u04FF" for ch in blob)

    def test_placeholders_match_between_languages(self, dicts):
        import re
        for key in dicts["ua"]:
            ua = set(re.findall(r"\{(\w+)\}", dicts["ua"][key]))
            en = set(re.findall(r"\{(\w+)\}", dicts["en"][key]))
            assert ua == en, f"placeholder mismatch in {key}: {ua} vs {en}"


class TestWiring:
    def test_index_has_language_switcher(self, client):
        html = client.get("/").text
        assert 'id="langBtn"' in html

    def test_sw_preaches_i18n_dict(self, client):
        sw = client.get("/sw.js").text
        assert '"/i18n.json"' in sw, "dictionary must be in the offline shell"

    def test_app_js_uses_dictionary_and_persists_choice(self, client):
        js = client.get("/app.js").text
        assert 'const LANG_KEY = "mc_lang"' in js
        assert "localStorage.getItem(LANG_KEY)" in js
        assert "localStorage.setItem(LANG_KEY" in js
        assert "navigator.language" in js  # browser auto-detect
        assert "function t(" in js

    def test_ukrainian_default_fallback_in_markup(self, client):
        html = client.get("/").text
        assert 'lang="uk"' in html, "no-JS first paint stays Ukrainian"
