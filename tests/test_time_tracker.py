"""Time tracker: estimates, timer sessions, history math."""

from datetime import datetime

import pytest

from app.logic.time_tracker import (elapsed_minutes, estimate_status,
                                    format_minutes, total_minutes,
                                    validate_estimate)


class TestElapsedMinutes:
    def test_exact_hour(self):
        assert elapsed_minutes("2026-11-05T10:00:00", "2026-11-05T11:00:00") == 60

    def test_rounds_to_nearest_minute(self):
        assert elapsed_minutes("2026-11-05T10:00:00", "2026-11-05T10:00:29") == 0
        assert elapsed_minutes("2026-11-05T10:00:00", "2026-11-05T10:00:31") == 1

    def test_inverted_is_zero(self):
        assert elapsed_minutes("2026-11-05T10:00:00", "2026-11-05T09:00:00") == 0

    def test_crosses_midnight(self):
        assert elapsed_minutes("2026-11-05T23:30:00", "2026-11-06T00:30:00") == 60


class TestTotalMinutes:
    def test_sums_logs(self):
        logs = [{"minutes": 25}, {"minutes": 15}, {"minutes": None}]
        assert total_minutes(logs) == 40

    def test_empty(self):
        assert total_minutes([]) == 0


class TestFormat:
    def test_minutes_only(self):
        assert format_minutes(45) == "45 хв"

    def test_hours_and_minutes(self):
        assert format_minutes(95) == "1 год 35 хв"


class TestValidateEstimate:
    def test_none_ok(self):
        assert validate_estimate(None) is None

    def test_valid(self):
        assert validate_estimate(45) == 45

    def test_negative_raises(self):
        with pytest.raises(ValueError, match=">= 0"):
            validate_estimate(-5)

    def test_over_24h_raises(self):
        with pytest.raises(ValueError, match="24h"):
            validate_estimate(1500)


class TestEstimateStatus:
    def test_no_estimate(self):
        assert estimate_status(None, 100) == "no_estimate"

    def test_within(self):
        assert estimate_status(45, 30) == "ok"

    def test_over(self):
        assert estimate_status(25, 26) == "over"

    def test_exact_boundary_is_ok(self):
        assert estimate_status(25, 25) == "ok"
