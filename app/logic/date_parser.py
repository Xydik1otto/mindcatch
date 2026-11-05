"""Natural-language date parsing for capture text (UA + EN).

Pure logic, no I/O: ``parse(text, today=...)`` returns a :class:`ParsedDate`
with ``remind_at`` (ISO datetime) and ``due_date`` (ISO date) fields, or None
when no date hint is found. Tests inject ``today`` for determinism.

Supported (v0.1 scope):
- relative days: сьогодні/today, завтра/tomorrow, післязавтра/day after tomorrow
- weekdays: 'у пʼятницю', 'в середу', 'next monday', 'on friday'
- explicit dates: 2026-11-10, 31.12, 31.12.2027, 5/06
- time of day: 15:00, 9:05, 'tomorrow 15:00', 'завтра о 9:30'
- next week: 'next week', 'наступного тижня'
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

@dataclass
class ParsedDate:
    date: date
    time: time | None = None
    matched_text: str = ""

    @property
    def due_date(self) -> str:
        return self.date.isoformat()

    @property
    def remind_at(self) -> str:
        """ISO datetime; a date without time defaults to 09:00 local."""
        t = self.time or time(9, 0)
        return datetime.combine(self.date, t).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------

_WEEKDAY_UA = {
    "понеділк": 0, "вівтор": 1, "серед": 2, "четвер": 3,
    "пятниц": 4, "субот": 5, "неділ": 6,
}
_WEEKDAY_EN = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}

_RELATIVE = [
    (re.compile(r"післязавтра", re.IGNORECASE), 2),
    (re.compile(r"\bday\s+after\s+tomorrow\b", re.IGNORECASE), 2),
    (re.compile(r"завтра", re.IGNORECASE), 1),
    (re.compile(r"\btomorrow\b", re.IGNORECASE), 1),
    (re.compile(r"сьогодні", re.IGNORECASE), 0),
    (re.compile(r"\btoday\b", re.IGNORECASE), 0),
]

# UA weekday with any Slavic case ending; apostrophes normalized beforehand.
_UA_WEEKDAY_RE = re.compile(
    r"\b(?:у|в|на)?\s?(понеділк\w*|вівтор\w*|серед\w*|четвер\w*|"
    r"п'ятниц\w*|пятниц\w*|субот\w*|неділ\w*)\b", re.IGNORECASE)
_EN_WEEKDAY_RE = re.compile(r"\b(next\s+|on\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
                            re.IGNORECASE)
_NEXT_WEEK_RE = re.compile(r"\b(?:next\s+week|наступн\w+\s+тижн\w+|через\s+тиждень)\b", re.IGNORECASE)

_ISO_DATE_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_DMY_DATE_RE = re.compile(r"\b(\d{1,2})[./](\d{1,2})(?:[./](\d{2}|\d{4}))?\b")
_TIME_RE = re.compile(r"\b(?:о\s+|at\s+)?(\d{1,2}):(\d{2})\b", re.IGNORECASE)


def _normalize(text: str) -> str:
    """Unify apostrophes so 'пʼятницю', \"п'ятницю\", 'п`ятницю' all match."""
    for ch in ("\u02bc", "\u2019", "`", "'"):
        text = text.replace(ch, "'")
    return text


def _next_weekday(today: date, target: int, next_week: bool = False) -> date:
    """Next occurrence of ``target`` weekday, strictly in the future. The
    ``next_week`` flag ('next monday') is kept for signature compatibility."""
    days_ahead = (target - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return today + timedelta(days=days_ahead)


def _weekday_from_ua(word: str) -> int | None:
    w = word.lower()
    for prefix, wd in _WEEKDAY_UA.items():
        if w.startswith(prefix[:6]) or (prefix == "пятниц" and w.startswith("п'ятниц")):
            return wd
    return None


def parse(text: str, today: date | None = None) -> ParsedDate | None:
    """Extract the first date/time hint from ``text``. None when no hint."""
    if not text:
        return None
    today = today or date.today()
    text = _normalize(text)

    result_date: date | None = None
    matched = ""

    # 1. explicit ISO date
    m = _ISO_DATE_RE.search(text)
    if m:
        result_date = date(int(m[1]), int(m[2]), int(m[3]))
        matched = m[0]
    # 2. d.m(.yy|yyyy)
    if result_date is None:
        m = _DMY_DATE_RE.search(text)
        if m:
            d, mo = int(m[1]), int(m[2])
            year = today.year
            if m[3]:
                year = int(m[3])
                if year < 100:
                    year += 2000
            try:
                result_date = date(year, mo, d)
            except ValueError:
                result_date = None
            else:
                if not m[3] and result_date < today:  # 31.12 passed -> next year
                    result_date = date(year + 1, mo, d)
                matched = m[0]
    # 3. relative day words
    if result_date is None:
        for rx, delta in _RELATIVE:
            m = rx.search(text)
            if m:
                result_date = today + timedelta(days=delta)
                matched = m[0]
                break
    # 4. weekdays
    if result_date is None:
        m = _EN_WEEKDAY_RE.search(text)
        if m:
            next_week = bool(m[1] and "next" in m[1].lower())
            result_date = _next_weekday(today, _WEEKDAY_EN[m[2].lower()], next_week)
            matched = m[0]
    if result_date is None:
        m = _UA_WEEKDAY_RE.search(text)
        if m:
            wd = _weekday_from_ua(m[1])
            if wd is not None:
                result_date = _next_weekday(today, wd)
                matched = m[0].strip()
    # 5. next week
    if result_date is None:
        m = _NEXT_WEEK_RE.search(text)
        if m:
            result_date = today + timedelta(days=7)
            matched = m[0]

    if result_date is None:
        return None

    m_time = _TIME_RE.search(text)
    t = None
    if m_time:
        hh, mm = int(m_time[1]), int(m_time[2])
        if 0 <= hh < 24 and 0 <= mm < 60:
            t = time(hh, mm)
            if not matched:
                matched = m_time[0]
    return ParsedDate(date=result_date, time=t, matched_text=matched)
