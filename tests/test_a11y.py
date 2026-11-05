"""Accessibility: aria-labels on interactive elements, keyboard navigation,
visible focus, contrast."""

import os
import re
import tempfile

import pytest
from fastapi.testclient import TestClient

_TMP = tempfile.mkdtemp(prefix="mindcatch-a11y-")
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
def html(client):
    return client.get("/").text


@pytest.fixture()
def js(client):
    return client.get("/app.js").text


def icon_buttons(html):
    """Interactive icon-only buttons in the static markup."""
    return re.findall(r"<button[^>]*>([^<]*)</button>", html)


class TestStaticMarkup:
    def test_all_static_buttons_have_accessible_names(self, html):
        for label in icon_buttons(html):
            name = re.search(r'aria-label="([^"]+)"', label) or label.strip()
            assert name, f"icon button without accessible name: {label!r}"

    def test_capture_input_has_label(self, html):
        assert 'aria-label="captureInput"' in html or "captureInput" in html
        assert re.search(r'<input id="captureInput"[^>]+(aria-label|placeholder)', html)

    def test_search_input_has_label(self, html):
        assert re.search(r'<input id="searchInput"[^>]+(aria-label|placeholder)', html)

    def test_dialogs_have_aria_roles(self, html):
        assert 'role="dialog"' in html          # tour
        assert 'aria-modal="true"' in html
        for dlg in ("noteEditor", "focus", "tour"):
            m = re.search(rf'id="{dlg}"[^>]*', html)
            assert m and 'role="dialog"' in m.group(0), f"{dlg} lacks role=dialog"

    def test_lang_attribute_matches_ukrainian_default(self, html):
        assert '<html lang="uk">' in html

    def test_export_links_have_href(self, html):
        for href in ("/api/export", "/api/export/calendar.ics"):
            assert f'href="{href}"' in html


class TestDynamicUi:
    def test_item_action_buttons_get_aria_labels(self, js):
        # rec/timer/done/note/tags buttons are created in JS — each must set aria-label
        for anchor in ("rec_btn_title", "timer_title", "done_title",
                       "note_btn_title", "tags_title"):
            assert f'aria-label", t("{anchor}")' in js, f"missing aria-label via {anchor}"

    def test_status_select_has_aria_label(self, js):
        assert 'move_status_aria' in js

    def test_skip_to_content_link(self, html):
        assert 'href="#list"' in html and "skip" in html.lower()

    def test_focus_visible_styles(self, client):
        css = client.get("/").text
        assert ":focus-visible" in css


class TestKeyboardFlow:
    def test_hotkeys_cover_capture_today_focus_export(self, js):
        for key in ("n", "t", "f", "e", "l"):
            assert re.search(rf'e\.key === "{key}"', js), f"hotkey {key} missing"

    def test_tour_buttons_are_real_buttons(self, html):
        # focusable, not div-onclick
        assert '<button id="tourNext"' in html and '<button id="tourSkip"' in html
