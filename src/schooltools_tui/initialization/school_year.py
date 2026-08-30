
from pathlib import Path

SCHOOL_YEAR_DIRECTORIES = (
    Path("classes"),
)

def initialize_school_year(root: Path, year: str) -> None:
    path = root / "school-years" / year

    for relative_path in SCHOOL_YEAR_DIRECTORIES:
        directory = path / relative_path
        directory.mkdir(parents=True, exist_ok=True)
