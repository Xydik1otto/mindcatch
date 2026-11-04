"""Triage transitions: inbox -> today/week/someday/done."""

import pytest

from app.logic.triage import STATUSES, can_move, move


class TestCanMove:
    def test_from_inbox_anywhere(self):
        for target in ("today", "week", "someday", "done"):
            assert can_move("inbox", target)

    def test_done_is_reachable_from_everywhere(self):
        for s in ("inbox", "today", "week", "someday"):
            assert can_move(s, "done")

    def test_reopen_done(self):
        for target in ("today", "week", "someday", "inbox"):
            assert can_move("done", target)

    def test_no_self_transition(self):
        for s in STATUSES:
            assert not can_move(s, s)

    def test_unknown_status(self):
        assert not can_move("archive", "today")
        assert not can_move("inbox", "archive")


class TestMove:
    def _item(self, status="inbox"):
        return {"id": 1, "text": "buy oat milk", "type": "task", "status": status}

    def test_happy_path(self):
        assert move(self._item(), "today")["status"] == "today"

    def test_original_untouched(self):
        item = self._item()
        move(item, "week")
        assert item["status"] == "inbox"  # returns a copy

    def test_self_move_raises(self):
        with pytest.raises(ValueError, match="already"):
            move(self._item("today"), "today")

    def test_unknown_status_raises(self):
        with pytest.raises(ValueError, match="unknown status"):
            move({"id": 1, "text": "x", "type": "task", "status": "archive"}, "today")

    def test_unknown_target_raises(self):
        with pytest.raises(ValueError, match="unknown target status"):
            move(self._item(), "archive")

    def test_full_lifecycle(self):
        item = self._item()
        for s in ("today", "week", "someday", "inbox", "today", "done"):
            item = move(item, s)
        assert item["status"] == "done"

    def test_gtd_someday_to_today(self):
        assert move(self._item("someday"), "today")["status"] == "today"
