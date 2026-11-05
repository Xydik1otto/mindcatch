"""Onboarding tour: 3 first-run tips driven by localStorage."""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

_TMP = tempfile.mkdtemp(prefix="mindcatch-tour-")
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


class TestTourMarkup:
    def test_index_has_tour_dialog(self, client):
        html = client.get("/").text
        assert 'id="tour"' in html
        assert 'role="dialog"' in html and "aria-modal" in html

    def test_tour_has_next_and_skip_buttons(self, client):
        html = client.get("/").text
        assert 'id="tourNext"' in html
        assert 'id="tourSkip"' in html

    def test_tour_step_counters_in_markup(self, client):
        html = client.get("/").text
        for el in ("tourStep", "tourTitle", "tourText"):
            assert f'id="{el}"' in html


class TestTourLogic:
    def test_app_js_defines_three_steps(self, client):
        js = client.get("/app.js").text
        assert js.count("title: \"") >= 3, "tour must have exactly 3+ titled steps"
        assert "TOUR_STEPS = [" in js

    def test_app_js_persists_completion_in_localstorage(self, client):
        js = client.get("/app.js").text
        assert '"mc_tour_done"' in js
        assert "localStorage.getItem(TOUR_KEY)" in js
        assert "localStorage.setItem(TOUR_KEY" in js

    def test_tour_starts_only_for_first_visit(self, client):
        js = client.get("/app.js").text
        assert "maybeStartTour" in js
        # the gate: tour shown only when the key is missing
        assert 'if (!localStorage.getItem(TOUR_KEY))' in js

    def test_tour_targets_real_ui_elements(self, client):
        js = client.get("/app.js").text
        html = client.get("/").text
        import re
        sels = re.findall(r'sel: "([^"]+)"', js)
        assert len(sels) >= 3
        for sel in sels:
            # every tour target must exist in the served page markup
            assert sel.lstrip("#.") in html, f"tour target {sel} missing in index.html"
