"""Markdown / Todoist-compatible task export: pure logic + API."""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from app.logic.task_export import to_markdown, to_todoist

_TMP = tempfile.mkdtemp(prefix="mindcatch-mdexp-")
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


def _item(**kw):
    base = {"id": 1, "text": "здати звіт", "type": "task", "status": "today",
            "tags": "робота", "priority": None, "due_date": "2026-11-10",
            "remind_at": None, "recurrence": None, "body": None}
    base.update(kw)
    return base


class TestTodoistFormat:
    def test_checklist_line_with_tag_and_date(self):
        line = to_todoist([_item()])
        assert "- [ ] здати звіт @робота 📅 2026-11-10" in line

    def test_done_items_checked_and_last(self):
        md = to_todoist([_item(id=2, status="done", text="старе"),
                         _item(id=1, text="нове")])
        done_pos, open_pos = md.index("- [x] старе"), md.index("- [ ] нове")
        assert done_pos > open_pos

    def test_priority_shortform(self):
        assert "p1" in to_todoist([_item(priority=1)])
        assert "p4" not in to_todoist([_item()])  # default priority omitted

    def test_tags_have_no_spaces(self):
        line = to_todoist([_item(tags="my project, other")])
        assert "@my-project" in line and "@other" in line

    def test_recurrence_hint(self):
        assert "↻ every 3 days" in to_todoist([_item(recurrence="every:3")])
        assert "↻ every weekday" in to_todoist([_item(recurrence="weekdays")])
        assert "↻ every day" in to_todoist([_item(recurrence="daily")])


class TestMarkdownExport:
    def test_grouped_by_status(self):
        md = to_markdown([_item(status="today"), _item(status="done", text="ok")])
        assert "## ☀️ Today (1)" in md
        assert "## ✅ Done (1)" in md
        assert md.index("## ☀️ Today") < md.index("## ✅ Done")

    def test_body_included_as_quote(self):
        md = to_markdown([_item(body="деталі\nдругий рядок")])
        assert "> деталі" in md and "> другий рядок" in md

    def test_remind_at_shown_when_no_due_date(self):
        md = to_markdown([_item(due_date=None, remind_at="2026-11-10T15:00:00")])
        assert "🔔 2026-11-10T15:00" in md

    def test_empty_groups_omitted(self):
        md = to_markdown([_item(status="today")])
        assert "📥 Inbox" not in md


class TestApi:
    def test_todoist_endpoint(self, client):
        client.post("/api/capture", json={"text": "здати звіт завтра #робота"})
        r = client.get("/api/export/todoist.md")
        assert r.status_code == 200
        assert "text/markdown" in r.headers["content-type"]
        assert "- [ ] " in r.text

    def test_markdown_endpoint(self, client):
        client.post("/api/capture", json={"text": "нотатка про проєкт"})
        r = client.get("/api/export/markdown")
        assert r.status_code == 200
        assert "# Mindcatch export" in r.text

    def test_export_contains_captured_text(self, client):
        client.post("/api/capture", json={"text": "подзвонити мамі завтра"})
        md = client.get("/api/export/todoist.md").text
        assert "подзвонити мамі" in md
