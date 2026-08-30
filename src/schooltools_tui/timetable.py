from dataclasses import dataclass
from pathlib import Path

from schooltools_tui.storage import save_csv

TIMETABLE_FIELDS = (
    "weekday",
    "period",
    "class_name",
    "subject",
    "room",
)

@dataclass
class TimetableEntry:
    weekday: str
    period: int
    class_name: str
    subject: str
    room: str


def create_empty_timetable(path: Path) -> None:
    if path.exists():
        if not path.is_file():
            raise IsADirectoryError(f"Der Stundenplan-Pfad ist keine Datei: {path}")

        return

    save_csv(path=path, fieldnames=TIMETABLE_FIELDS, rows=())


def load_timetable():
    pass


def save_timetable():
    pass
