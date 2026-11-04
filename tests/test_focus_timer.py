"""Focus timer (pomodoro) state machine — deterministic via injected clock."""

import pytest

from app.logic.focus_timer import (
    LONG_BREAK_MIN,
    SHORT_BREAK_MIN,
    WORK_MIN,
    PomodoroTimer,
)

T0 = 1000.0  # arbitrary epoch start
MIN = 60.0


class TestWorkPhase:
    def test_start(self):
        t = PomodoroTimer().start(T0)
        assert t.phase == "work"
        assert t.remaining(T0) == WORK_MIN * 60
        assert t.remaining(T0 + 10) == WORK_MIN * 60 - 10

    def test_double_start_raises(self):
        t = PomodoroTimer().start(T0)
        with pytest.raises(ValueError):
            t.start(T0 + 1)

    def test_finish_work_goes_to_short_break(self):
        t = PomodoroTimer().start(T0)
        t.complete(T0 + WORK_MIN * 60)
        assert t.phase == "short_break"
        assert t.remaining(T0 + WORK_MIN * 60) == SHORT_BREAK_MIN * 60
        assert t.completed_pomodoros == 1

    def test_finish_break_returns_to_work(self):
        t = PomodoroTimer().start(T0).complete(T0)
        t.complete(T0 + SHORT_BREAK_MIN * 60)
        assert t.phase == "work"
        assert t.completed_pomodoros == 1  # breaks don't count


class TestLongBreak:
    def test_long_break_after_4th_pomodoro(self):
        t = PomodoroTimer().start(T0)
        for _ in range(3):  # three full work+break cycles
            t.complete(T0)              # finish work
            t.complete(T0)              # finish break
        assert t.phase == "work"
        assert t.complete(T0)                  # finish the 4th work phase
        assert t.completed_pomodoros == 4
        assert t.phase == "long_break"
        assert t.remaining(T0) == LONG_BREAK_MIN * 60  # complete(T0) -> remaining vs T0


class TestPauseResume:
    def test_pause_freezes_remaining(self):
        t = PomodoroTimer().start(T0)
        t.pause(T0 + 10 * 60)
        assert t.running is False
        assert t.remaining(T0 + 100 * 60) == (WORK_MIN - 10) * 60  # frozen

    def test_resume_continues(self):
        t = PomodoroTimer().start(T0)
        t.pause(T0 + 10 * 60)
        t.resume(T0 + 100 * 60)
        assert t.remaining(T0 + 100 * 60) == (WORK_MIN - 10) * 60
        assert t.remaining(T0 + 100 * 60 + 60) == (WORK_MIN - 10) * 60 - 60

    def test_pause_when_idle_raises(self):
        with pytest.raises(ValueError):
            PomodoroTimer().pause(T0)

    def test_resume_when_running_raises(self):
        t = PomodoroTimer().start(T0)
        with pytest.raises(ValueError):
            t.resume(T0)


class TestStopAndEdge:
    def test_stop_resets(self):
        t = PomodoroTimer().start(T0).stop()
        assert t.phase == "idle"
        assert t.remaining(T0) == 0

    def test_complete_when_idle_raises(self):
        with pytest.raises(ValueError):
            PomodoroTimer().complete(T0)

    def test_finished_but_not_completed_stays(self):
        t = PomodoroTimer().start(T0)
        # time passed but complete() not called: phase is still work, remaining 0
        assert t.is_finished(T0 + WORK_MIN * 60 + 5)
        assert t.phase == "work"
        t.complete(T0 + WORK_MIN * 60 + 5)
        assert t.phase == "short_break"
