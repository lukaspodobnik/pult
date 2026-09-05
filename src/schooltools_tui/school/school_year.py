from datetime import datetime
from importlib.resources import files
from pathlib import Path
from zoneinfo import ZoneInfo

from schooltools_tui.school.calendar import (
    CALENDARS_DIRECTORY_NAME,
    CALENDAR_FILE_SUFFIX,
    load_school_calendar,
    validate_school_year,
)


def get_school_year_options(
    root: Path | None = None,
) -> list[tuple[str, str]]:
    calendar_directory = (
        root / CALENDARS_DIRECTORY_NAME
        if root is not None
        else files("schooltools_tui.defaults") / CALENDARS_DIRECTORY_NAME
    )
    if not calendar_directory.is_dir():
        return []

    school_years = []
    for item in calendar_directory.iterdir():
        if not item.is_file() or not item.name.endswith(CALENDAR_FILE_SUFFIX):
            continue

        year = item.name.removesuffix(CALENDAR_FILE_SUFFIX)
        try:
            year = validate_school_year(year)
            if root is not None:
                load_school_calendar(root, year)
            school_years.append(year)
        except (OSError, TypeError, ValueError):
            continue

    return [(year, year) for year in sorted(set(school_years))]


def get_likely_school_year(
    school_year_options: list[tuple[str, str]],
) -> str:
    if not school_year_options:
        raise ValueError("Es ist kein Schuljahreskalender verfügbar.")

    now = datetime.now(ZoneInfo("Europe/Berlin"))
    start_year = now.year if now.month >= 8 else now.year - 1
    likely_school_year = f"{start_year}-{start_year + 1}"
    available_years = [year for _, year in school_year_options]

    if likely_school_year in available_years:
        return likely_school_year

    return min(
        available_years,
        key=lambda year: abs(int(year.split("-", maxsplit=1)[0]) - start_year),
    )
