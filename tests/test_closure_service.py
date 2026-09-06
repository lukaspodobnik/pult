from datetime import date

import pytest

from schooltools_tui.config import AppConfig
from schooltools_tui.school.calendar import (
    Closure,
    ClosureKind,
    load_class_closures,
    load_school_closures,
    save_class_closures,
    save_school_calendar,
    save_school_closures,
)
from schooltools_tui.services.closures import (
    ScopedClosure,
    add_closure,
    delete_closure,
    get_default_closure_date,
    validate_closure,
)


@pytest.fixture
def config(tmp_path, school_calendar):
    (tmp_path / "calendars").mkdir()
    (tmp_path / "school-years" / "2026-2027" / "classes" / "5A").mkdir(parents=True)
    save_school_calendar(tmp_path, school_calendar)
    save_school_closures(tmp_path, "2026-2027", [])
    save_class_closures(tmp_path, "2026-2027", "5A", [])
    return AppConfig(tmp_path, "true", "2026-2027")


@pytest.mark.parametrize("scope", [None, "5A"])
def test_add_delete_and_duplicate_validation(config, local_closure, scope):
    entry = ScopedClosure(local_closure, scope)
    add_closure(config, entry)
    school = load_school_closures(config.root, config.active_school_year)
    school_class = load_class_closures(config.root, config.active_school_year, "5A")
    assert school == ([local_closure] if scope is None else [])
    assert school_class == ([local_closure] if scope == "5A" else [])
    with pytest.raises(ValueError, match="keinen verfügbaren"):
        add_closure(config, entry)
    delete_closure(config, entry)
    assert load_school_closures(config.root, config.active_school_year) == []
    assert load_class_closures(config.root, config.active_school_year, "5A") == []


@pytest.mark.parametrize("day", [6, 12, 14, 19])
def test_unavailable_dates_rejected(config, day):
    closure = Closure("Test", ClosureKind.LOCAL, date(2026, 9, day), date(2026, 9, day))
    with pytest.raises(ValueError):
        validate_closure(config, ScopedClosure(closure, None))


def test_school_closure_blocks_class_closure(config, local_closure):
    add_closure(config, ScopedClosure(local_closure, None))
    with pytest.raises(ValueError, match="keinen verfügbaren"):
        validate_closure(config, ScopedClosure(local_closure, "5A"))


def test_default_date_search_and_empty_year(config, school_calendar):
    assert get_default_closure_date(config, date(2026, 9, 1)) == date(2026, 9, 7)
    assert get_default_closure_date(config, date(2026, 9, 12)) == date(2026, 9, 15)
    end = Closure("Ende", ClosureKind.LOCAL, date(2026, 9, 18), date(2026, 9, 18))
    add_closure(config, ScopedClosure(end, None))
    assert get_default_closure_date(config, date(2026, 10, 1)) == date(2026, 9, 17)
    save_school_closures(
        config.root,
        config.active_school_year,
        [
            Closure(
                "Alles",
                ClosureKind.LOCAL,
                school_calendar.first_school_day,
                school_calendar.last_school_day,
            )
        ],
    )
    with pytest.raises(ValueError, match="keinen verfügbaren"):
        get_default_closure_date(config, date(2026, 9, 7))
