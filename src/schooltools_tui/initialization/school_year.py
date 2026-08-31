
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from schooltools_tui.timetable import create_empty_timetable, get_timetable_path

SCHOOL_YEAR_DIRECTORIES = (
    Path("classes"),
)


def get_school_year_options() -> list[tuple[str, str]]:
    now = datetime.now(ZoneInfo("Europe/Berlin"))
    start_year = now.year if now.month >= 8 else now.year - 1

    return [
        (f"{year}-{year + 1}", f"{year}-{year + 1}")
        for year in range(start_year - 1, start_year + 2)
    ]

def initialize_school_year(root: Path, year: str) -> None:
    school_year_path = root / "school-years" / year

    for relative_path in SCHOOL_YEAR_DIRECTORIES:
        directory = school_year_path / relative_path
        directory.mkdir(parents=True, exist_ok=True)

    create_empty_timetable(get_timetable_path(root, year))
