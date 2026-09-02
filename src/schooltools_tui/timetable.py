from dataclasses import dataclass
from pathlib import Path

from schooltools_tui.storage import load_csv, save_csv

TIMETABLE_FIELDS = (
    "weekday",
    "period",
    "school_class_id",
    "subject_id",
    "room",
)


@dataclass
class TimetableEntry:
    weekday: str
    period: int
    school_class_id: str
    subject_id: str
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
            school_class_id=row.get("school_class_id") or row["class_name"],
            subject_id=row.get("subject_id") or row["subject"],
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
            "school_class_id": entry.school_class_id,
            "subject_id": entry.subject_id,
            "room": entry.room,
        }

        rows.append(row)

    save_csv(path, TIMETABLE_FIELDS, rows)


def save_timetable_entry(path: Path, entry: TimetableEntry) -> None:
    entries = load_timetable(path)
    entries_by_slot = {
        (existing_entry.weekday, existing_entry.period): existing_entry
        for existing_entry in entries
    }
    entries_by_slot[(entry.weekday, entry.period)] = entry
    save_timetable(path, list(entries_by_slot.values()))


def delete_timetable_entry(path: Path, weekday: str, period: int) -> None:
    entries = load_timetable(path)
    remaining_entries = [
        entry
        for entry in entries
        if (entry.weekday, entry.period) != (weekday, period)
    ]
    save_timetable(path, remaining_entries)


def delete_timetable_entries_for_school_class(
    path: Path, school_class_id: str
) -> None:
    entries = load_timetable(path)
    remaining_entries = [
        entry for entry in entries if entry.school_class_id != school_class_id
    ]
    save_timetable(path, remaining_entries)
