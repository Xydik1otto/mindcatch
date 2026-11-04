"""Focus-mode Pomodoro timer: pure state machine with an injected clock.

Phases: idle -> work (25 min) -> short break (5) -> work ... -> long break
(15) after every 4th completed pomodoro -> ...
All methods take ``now`` (epoch seconds) so tests are deterministic.
"""

from __future__ import annotations

WORK_MIN = 25
SHORT_BREAK_MIN = 5
LONG_BREAK_MIN = 15
CYCLES_BEFORE_LONG = 4

PHASES = ("idle", "work", "short_break", "long_break")
PHASE_MINUTES = {
    "idle": 0,
    "work": WORK_MIN,
    "short_break": SHORT_BREAK_MIN,
    "long_break": LONG_BREAK_MIN,
}


class PomodoroTimer:
    def __init__(self) -> None:
        self.phase = "idle"
        self.running = False
        self.end_ts: float | None = None
        self.remaining_on_pause: int | None = None
        self.completed_pomodoros = 0

    # -- state helpers ------------------------------------------------------
    def remaining(self, now: float) -> int:
        """Seconds left in the current phase (0 when idle; frozen while paused)."""
        if self.phase == "idle":
            return 0
        if self.running and self.end_ts is not None:
            return max(0, int(round(self.end_ts - now)))
        return self.remaining_on_pause or 0

    def is_finished(self, now: float) -> bool:
        return self.running and self.remaining(now) == 0

    # -- actions ------------------------------------------------------------
    def start(self, now: float) -> "PomodoroTimer":
        if self.phase not in ("idle",):
            raise ValueError("timer already started; use pause/complete/stop")
        self.phase = "work"
        self.running = True
        self.end_ts = now + WORK_MIN * 60
        return self

    def pause(self, now: float) -> "PomodoroTimer":
        if self.phase == "idle" or not self.running:
            raise ValueError("nothing running to pause")
        self.remaining_on_pause = self.remaining(now)
        self.running = False
        self.end_ts = None
        return self

    def resume(self, now: float) -> "PomodoroTimer":
        if self.phase == "idle" or self.running:
            raise ValueError("nothing paused to resume")
        self.running = True
        self.end_ts = now + (self.remaining_on_pause or 0)
        self.remaining_on_pause = None
        return self

    def complete(self, now: float) -> "PomodoroTimer":
        """Finish the current phase and advance to the next one."""
        if self.phase == "idle":
            raise ValueError("timer is idle")
        if self.phase == "work":
            self.completed_pomodoros += 1
            if self.completed_pomodoros % CYCLES_BEFORE_LONG == 0:
                self.phase = "long_break"
            else:
                self.phase = "short_break"
        else:  # a break was completed -> back to work
            self.phase = "work"
        self.running = True
        self.end_ts = now + PHASE_MINUTES[self.phase] * 60
        return self

    def stop(self) -> "PomodoroTimer":
        """Abandon the session entirely."""
        self.phase = "idle"
        self.running = False
        self.end_ts = None
        self.remaining_on_pause = None
        return self
