"""Date parser: UA + EN natural-language hints -> remind_at / due_date."""

from datetime import date

from app.logic.date_parser import parse


# Wednesday, so weekday tests are deterministic
TODAY = date(2026, 11, 4)  # Wednesday


def d(y, m, day):
    return date(y, m, day)


class TestRelativeDays:
    def test_ua_tomorrow(self):
        assert parse("завтра", TODAY).date == d(2026, 11, 5)

    def test_ua_today(self):
        assert parse("сьогодні купити хліб", TODAY).date == TODAY

    def test_ua_day_after_tomorrow(self):
        assert parse("післязавтра", TODAY).date == d(2026, 11, 6)

    def test_en_tomorrow(self):
        assert parse("call mom tomorrow", TODAY).date == d(2026, 11, 5)

    def test_extraction_from_middle_of_text(self):
        p = parse("нагадай завтра о 09:05 купити хліб", TODAY)
        assert p.date == d(2026, 11, 5)
        assert p.time.hour == 9 and p.time.minute == 5


class TestWeekdays:
    def test_ua_weekday_with_apostrophe(self):
        # у пʼятницю: Friday after Wednesday Nov 4 -> Nov 6
        assert parse("у пʼятницю", TODAY).date == d(2026, 11, 6)

    def test_ua_weekday_straight_apostrophe(self):
        assert parse("у п'ятницю", TODAY).date == d(2026, 11, 6)

    def test_ua_weekday_other_case(self):
        assert parse("на зустріч у суботу", TODAY).date == d(2026, 11, 7)

    def test_en_next_monday(self):
        # next Monday after Wed Nov 4 -> Nov 9
        assert parse("next monday", TODAY).date == d(2026, 11, 9)

    def test_en_bare_weekday(self):
        assert parse("submit report on friday", TODAY).date == d(2026, 11, 6)

    def test_weekday_today_goes_to_next_week(self):
        # 'friday' captured on a Friday -> next Friday
        assert parse("friday", d(2026, 11, 6)).date == d(2026, 11, 13)


class TestExplicitDates:
    def test_iso_date(self):
        assert parse("дедлайн 2026-11-10", TODAY).date == d(2026, 11, 10)

    def test_day_month_current_year(self):
        assert parse("31.12", TODAY).date == d(2026, 12, 31)

    def test_day_month_full_year(self):
        assert parse("31.12.2027", TODAY).date == d(2027, 12, 31)

    def test_passed_day_month_rolls_to_next_year(self):
        assert parse("1.01", TODAY).date == d(2027, 1, 1)


class TestTime:
    def test_tomorrow_with_time(self):
        p = parse("tomorrow 15:00", TODAY)
        assert p.date == d(2026, 11, 5)
        assert p.time.hour == 15

    def test_ua_time_with_preposition(self):
        p = parse("завтра о 9:30 дзвінок", TODAY)
        assert p.time.hour == 9 and p.time.minute == 30

    def test_remind_at_iso_defaults_9am(self):
        assert parse("завтра", TODAY).remind_at == "2026-11-05T09:00:00"

    def test_remind_at_with_time(self):
        assert parse("tomorrow 15:00", TODAY).remind_at == "2026-11-05T15:00:00"

    def test_due_date_format(self):
        assert parse("2026-11-10", TODAY).due_date == "2026-11-10"


class TestNoDate:
    def test_plain_text_returns_none(self):
        assert parse("просто думка без дат", TODAY) is None

    def test_empty_returns_none(self):
        assert parse("", TODAY) is None

    def test_matched_text_reported(self):
        assert parse("теріняю завтра нагадування", TODAY).matched_text.lower() == "завтра"
