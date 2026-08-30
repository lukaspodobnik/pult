
from pathlib import Path

from schooltools_tui.timetable import create_empty_timetable

SCHOOL_YEAR_DIRECTORIES = (
    Path("classes"),
)

def initialize_school_year(root: Path, year: str) -> None:
    school_year_path = root / "school-years" / year

    for relative_path in SCHOOL_YEAR_DIRECTORIES:
        directory = school_year_path / relative_path
        directory.mkdir(parents=True, exist_ok=True)

    create_empty_timetable(school_year_path / "timetable.csv")

