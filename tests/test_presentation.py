from datetime import date

import pytest

from schooltools_tui.presentation import format_date, format_school_year, parse_date
from schooltools_tui.school.school_year import get_school_year_options


def test_german_date_display_and_input():
    value = date(2026, 9, 7)
    assert format_date(value) == "07.09.2026"
    assert format_date(value, with_weekday=True) == "Montag, 07.09.2026"
    assert parse_date(format_date(value)) == value
    assert parse_date(" 07.09.2026 ") == value
    assert parse_date("29.02.2028") == date(2028, 2, 29)


@pytest.mark.parametrize(
    "value", ["2026-09-07", "7.9.2026", "31.09.2026", "29.02.2026", "", "07.09.26"]
)
def test_invalid_date_input_has_german_format_hint(value):
    with pytest.raises(ValueError, match=r"Das Startdatum.*TT\.MM\.JJJJ"):
        parse_date(value, "Das Startdatum")


def test_school_year_labels_do_not_change_internal_values():
    assert format_school_year("2026-2027") == "2026/27"
    options = get_school_year_options()
    assert options
    for label, value in options:
        assert label == format_school_year(value)
        assert len(value) == 9 and value[4] == "-"
