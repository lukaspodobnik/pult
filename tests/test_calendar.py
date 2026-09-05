from datetime import date

import pytest

from schooltools_tui.school.calendar import (
    CalendarFileError,
    Closure,
    ClosureKind,
    ClosuresFileError,
    SchoolCalendar,
    has_school_day,
    is_school_day,
    load_school_calendar,
    load_school_closures,
    save_school_calendar,
    save_school_closures,
    validate_school_year,
)
from schooltools_tui.storage import save_toml


@pytest.mark.parametrize("value", ["2026", "2026/2027", "2026-2028", "abc"])
def test_validate_school_year_rejects_invalid_values(value):
    with pytest.raises(ValueError):
        validate_school_year(value)


def test_weekend_holiday_and_local_closure_are_not_school_days(
    school_calendar, local_closure
):
    assert not is_school_day(school_calendar, date(2026, 9, 12))
    assert not is_school_day(school_calendar, date(2026, 9, 14))
    assert not is_school_day(
        school_calendar, date(2026, 9, 9), [local_closure]
    )
    assert is_school_day(school_calendar, date(2026, 9, 10))


def test_dates_outside_teaching_period_are_not_school_days(school_calendar):
    assert not is_school_day(school_calendar, date(2026, 9, 6))
    assert not is_school_day(school_calendar, date(2026, 9, 19))


def test_has_school_day_handles_multi_day_closure(school_calendar):
    closure = Closure(
        "Projektwoche",
        ClosureKind.LOCAL,
        date(2026, 9, 7),
        date(2026, 9, 11),
    )
    assert not has_school_day(
        school_calendar, date(2026, 9, 7), date(2026, 9, 13), [closure]
    )
    assert has_school_day(
        school_calendar, date(2026, 9, 7), date(2026, 9, 15), [closure]
    )


def test_calendar_roundtrip(tmp_path, school_calendar):
    (tmp_path / "calendars").mkdir()
    save_school_calendar(tmp_path, school_calendar)
    assert load_school_calendar(tmp_path, school_calendar.school_year) == school_calendar


def test_local_closures_roundtrip_sorted(tmp_path):
    path = tmp_path / "school-years" / "2026-2027"
    path.mkdir(parents=True)
    closures = [
        Closure("Später", ClosureKind.LOCAL, date(2027, 2, 2), date(2027, 2, 2)),
        Closure("Früher", ClosureKind.LOCAL, date(2026, 10, 2), date(2026, 10, 2)),
    ]
    save_school_closures(tmp_path, "2026-2027", closures)
    assert [item.name for item in load_school_closures(tmp_path, "2026-2027")] == [
        "Früher", "Später"
    ]


def test_invalid_calendar_keys_raise_domain_error(tmp_path):
    path = tmp_path / "calendars"
    path.mkdir()
    save_toml(path / "2026-2027.toml", {"school_year": "2026-2027"})
    with pytest.raises(CalendarFileError):
        load_school_calendar(tmp_path, "2026-2027")


def test_official_closure_is_rejected_in_local_file(tmp_path):
    path = tmp_path / "school-years" / "2026-2027"
    path.mkdir(parents=True)
    closure = Closure(
        "Feiertag", ClosureKind.PUBLIC_HOLIDAY,
        date(2026, 10, 3), date(2026, 10, 3),
    )
    with pytest.raises(ValueError):
        save_school_closures(tmp_path, "2026-2027", [closure])


def test_invalid_local_closure_file_raises_domain_error(tmp_path):
    path = tmp_path / "school-years" / "2026-2027"
    path.mkdir(parents=True)
    save_toml(path / "closures.toml", {"closures": "invalid"})
    with pytest.raises(ClosuresFileError):
        load_school_closures(tmp_path, "2026-2027")


def test_calendar_rejects_local_closures():
    closure = Closure(
        "Lokal", ClosureKind.LOCAL, date(2026, 9, 8), date(2026, 9, 8)
    )
    with pytest.raises(ValueError):
        SchoolCalendar(
            "2026-2027", date(2026, 9, 7), date(2027, 7, 30), (closure,)
        )
