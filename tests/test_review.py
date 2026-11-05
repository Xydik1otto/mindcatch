"""Weekly review: done this week vs carried over (week starts Monday)."""

from datetime import date

from app.logic.review import week_start, weekly_review


TODAY = date(2026, 11, 5)      # Thursday
MONDAY = date(2026, 11, 2)


def _item(id=1, status="inbox", created="2026-10-01T09:00:00+00:00",
          updated="2026-10-01T09:00:00+00:00", text="справа"):
    return {"id": id, "type": "task", "text": text, "status": status,
            "created_at": created, "updated_at": updated}


class TestWeekStart:
    def test_thursday_back_to_monday(self):
        assert week_start(TODAY) == MONDAY

    def test_monday_is_itself(self):
        assert week_start(MONDAY) == MONDAY

    def test_sunday_belongs_to_same_week(self):
        assert week_start(date(2026, 11, 8)) == MONDAY


class TestWeeklyReview:
    def test_done_this_week(self):
        items = [_item(status="done", updated="2026-11-03T15:00:00+00:00")]
        r = weekly_review(items, TODAY)
        assert r["counts"]["done"] == 1
        assert r["done_this_week"][0]["id"] == 1

    def test_done_last_week_not_counted(self):
        items = [_item(status="done", updated="2026-10-30T15:00:00+00:00")]
        assert weekly_review(items, TODAY)["counts"]["done"] == 0

    def test_done_after_today_not_counted(self):
        items = [_item(status="done", updated="2026-11-06T15:00:00+00:00")]
        assert weekly_review(items, TODAY)["counts"]["done"] == 0

    def test_carried_over_open_item_created_before_week(self):
        items = [_item(status="today", created="2026-10-20T09:00:00+00:00")]
        r = weekly_review(items, TODAY)
        assert r["counts"]["carried"] == 1

    def test_open_item_created_this_week_not_carried(self):
        items = [_item(status="today", created="2026-11-03T09:00:00+00:00")]
        assert weekly_review(items, TODAY)["counts"]["carried"] == 0

    def test_done_old_item_not_carried(self):
        items = [_item(status="done", created="2026-10-01T09:00:00+00:00")]
        assert weekly_review(items, TODAY)["counts"]["carried"] == 0

    def test_created_this_week_count(self):
        items = [
            _item(id=1, created="2026-11-03T09:00:00+00:00"),
            _item(id=2, created="2026-11-04T09:00:00+00:00"),
            _item(id=3, created="2026-10-01T09:00:00+00:00"),
        ]
        assert weekly_review(items, TODAY)["counts"]["created_this_week"] == 2

    def test_mixed_picture(self):
        items = [
            _item(id=1, status="done", updated="2026-11-03T10:00:00+00:00"),
            _item(id=2, status="week", created="2026-10-15T10:00:00+00:00"),
        ]
        r = weekly_review(items, TODAY)
        assert r["counts"] == {"done": 1, "carried": 1, "created_this_week": 0}
        assert r["week_start"] == MONDAY.isoformat()

    def test_empty(self):
        r = weekly_review([], TODAY)
        assert r["counts"] == {"done": 0, "carried": 0, "created_this_week": 0}
