from dataclasses import dataclass
from pathlib import Path

from schooltools_tui.storage import load_csv, save_csv

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


def get_timetable_path(root: Path, year: str) -> Path:
    return root / "school-years" / year / "timetable.csv"


def create_empty_timetable(path: Path) -> None:
    if path.exists():
        if not path.is_file():
            raise IsADirectoryError(f"Der Stundenplan-Pfad ist keine Datei: {path}")

        return

    save_csv(path=path, fieldnames=TIMETABLE_FIELDS, rows=())


def load_timetable(path: Path) -> list[TimetableEntry]:
    rows = load_csv(path)

    entries = []
    for row in rows:
        entry = TimetableEntry(
            weekday=row["weekday"],
            period=int(row["period"]),
            class_name=row["class_name"],
            subject=row["subject"],
            room=row["room"],
        )

        entries.append(entry)

    return entries


def save_timetable(path: Path, entries: list[TimetableEntry]) -> None:
    rows = []
    for entry in entries:
        row = {
            "weekday": entry.weekday,
            "period": str(entry.period),
            "class_name": entry.class_name,
            "subject": entry.subject,
            "room": entry.room,
        }

        rows.append(row)

    save_csv(path, TIMETABLE_FIELDS, rows)
