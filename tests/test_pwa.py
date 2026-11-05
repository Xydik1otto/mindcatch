"""PWA assets: manifest with icons, favicon, service worker shell."""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

_TMP = tempfile.mkdtemp(prefix="mindcatch-pwa-")
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


class TestPwaAssets:
    def test_manifest_has_icons(self, client):
        m = client.get("/manifest.json").json()
        assert m["icons"], "manifest must list at least one icon for installability"
        assert m["display"] == "standalone"

    def test_favicon_served(self, client):
        r = client.get("/favicon.svg")
        assert r.status_code == 200
        assert "<svg" in r.text

    def test_sw_preaches_full_shell(self, client):
        sw = client.get("/sw.js").text
        for shell_path in ('"/index.html"', '"/app.js"', '"/favicon.svg"'):
            assert shell_path in sw, f"shell missing {shell_path}"

    def test_index_links_favicon_and_manifest(self, client):
        html = client.get("/").text
        assert '/favicon.svg' in html
        assert '/manifest.json' in html
