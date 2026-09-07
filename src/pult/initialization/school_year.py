from pathlib import Path

from pult.school.calendar import (
    create_empty_school_closures,
    load_school_calendar,
)
from pult.school.timetable import (
    create_empty_timetable,
    get_timetable_path,
)

SCHOOL_YEAR_DIRECTORIES = (Path("classes"),)


def initialize_school_year(root: Path, year: str) -> None:
    """Lege ein Schuljahr samt leerem Stundenplan und schulweiten Ausfällen an."""
    load_school_calendar(root, year)
    school_year_path = root / "school-years" / year

    for relative_path in SCHOOL_YEAR_DIRECTORIES:
        directory = school_year_path / relative_path
        directory.mkdir(parents=True, exist_ok=True)

    create_empty_timetable(get_timetable_path(root, year))
    create_empty_school_closures(root, year)
