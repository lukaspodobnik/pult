"""Geplante schriftliche Leistungsnachweise einer Klasse im Schuljahr."""

from dataclasses import dataclass
from datetime import date as Date
from datetime import time
from enum import StrEnum
from pathlib import Path
from tomllib import TOMLDecodeError
from typing import Any

from pult.school.school_class import get_school_class_path
from pult.storage import load_toml, save_toml

ASSESSMENTS_FILE_NAME = Path("assessments.toml")


class AssessmentsFileError(ValueError):
    """Die Leistungsnachweisdatei enthält ungültige Daten."""


class AssessmentKind(StrEnum):
    SCHOOL_EXAM = "sa"
    IMPROMPTU_TEST = "ex"
    ANNOUNCED_TEST = "akl"
    YEAR_GROUP_TEST = "jst"

    @property
    def abbreviation(self) -> str:
        return self.value.upper()

    @property
    def label(self) -> str:
        return {
            AssessmentKind.SCHOOL_EXAM: "Schulaufgabe",
            AssessmentKind.IMPROMPTU_TEST: "Stegreifaufgabe",
            AssessmentKind.ANNOUNCED_TEST: "Angekündigter kleiner Leistungsnachweis",
            AssessmentKind.YEAR_GROUP_TEST: "Jahrgangsstufentest",
        }[self]


@dataclass(frozen=True)
class Assessment:
    """Ein Termin; Klasse und Schuljahr ergeben sich aus dem Ablagekontext.

    ``occupied_periods`` enthält die Nummern der eigenen Unterrichtsstunden
    am angegebenen Datum, die vollständig belegt werden. Ein leerer Wert
    bezeichnet einen Termin ohne Verbrauch eigener Unterrichtsstunden.
    Die Dauer in Minuten bestimmt diese Zuordnung ausdrücklich nicht.

    ``group_id`` verbindet bei Bedarf Termine innerhalb derselben Klasse und
    desselben Fachs, etwa BMT und ergänzenden Test. Die Anrechnung auf eine
    Mindestzahl und eine etwaige Notengewichtung werden hier nicht festgelegt.
    Planung bedeutet bei einer Stegreifaufgabe keine Ankündigung an die Klasse.
    """

    id: str
    subject_id: str
    kind: AssessmentKind
    title: str
    date: Date
    start: time
    duration_minutes: int
    occupied_periods: tuple[int, ...] = ()
    group_id: str | None = None
    completed_on: Date | None = None

    def __post_init__(self) -> None:
        for field in ("id", "subject_id", "title", "group_id"):
            value = getattr(self, field)
            if field == "group_id" and value is None:
                continue
            if not isinstance(value, str):
                raise TypeError(f"{field} muss ein Text sein.")
            if not value.strip():
                raise ValueError(f"{field} darf nicht leer sein.")
            object.__setattr__(self, field, value.strip())

        if not isinstance(self.kind, AssessmentKind):
            raise TypeError("Die Art des Leistungsnachweises ist ungültig.")
        if type(self.date) is not Date:
            raise TypeError("Der Termin muss ein Datum ohne Uhrzeit sein.")
        if self.completed_on is not None and type(self.completed_on) is not Date:
            raise TypeError("Das Abschlussdatum muss ein Datum ohne Uhrzeit sein.")
        if not isinstance(self.start, time) or self.start.tzinfo is not None:
            raise TypeError("Der Beginn muss eine lokale Uhrzeit sein.")
        if type(self.duration_minutes) is not int or self.duration_minutes < 1:
            raise ValueError("Die Dauer muss eine positive ganze Minutenzahl sein.")
        if not isinstance(self.occupied_periods, tuple):
            raise TypeError("Die belegten Stunden müssen als Tupel angegeben werden.")
        if any(
            type(period) is not int or period < 1 for period in self.occupied_periods
        ):
            raise ValueError(
                "Belegte Stundennummern müssen positive ganze Zahlen sein."
            )
        if len(set(self.occupied_periods)) != len(self.occupied_periods):
            raise ValueError(
                "Eine Unterrichtsstunde darf nicht mehrfach belegt werden."
            )


def get_assessments_path(root: Path, year: str, school_class_id: str) -> Path:
    """Gib den Pfad der Leistungsnachweise einer Klasse im Schuljahr zurück."""
    return (
        get_school_class_path(root, year, school_class_id).parent
        / ASSESSMENTS_FILE_NAME
    )


def load_assessments(root: Path, year: str, school_class_id: str) -> list[Assessment]:
    """Lade chronologisch; eine fehlende Datei bedeutet noch keine Termine."""
    path = get_assessments_path(root, year, school_class_id)
    try:
        data = load_toml(path)
    except FileNotFoundError:
        return []
    except TOMLDecodeError as error:
        raise AssessmentsFileError(f"Ungültiges TOML in {path}: {error}") from error

    try:
        rows = data.get("assessments")
        if not isinstance(rows, list):
            raise AssessmentsFileError(
                "Die Liste 'assessments' fehlt oder ist ungültig."
            )
        entries = [_load_assessment(row, index) for index, row in enumerate(rows, 1)]
        _validate_assessment_ids(entries)
    except AssessmentsFileError as error:
        raise AssessmentsFileError(f"{path}: {error}") from error
    return sorted(entries, key=lambda entry: (entry.date, entry.start, entry.id))


def save_assessments(
    root: Path, year: str, school_class_id: str, assessments: list[Assessment]
) -> None:
    """Ersetze die Termine einer bestehenden Klasse in chronologischer Reihenfolge."""
    _validate_assessment_ids(assessments)
    rows: list[dict[str, Any]] = []
    for entry in sorted(assessments, key=lambda item: (item.date, item.start, item.id)):
        row: dict[str, Any] = {
            "id": entry.id,
            "subject_id": entry.subject_id,
            "kind": entry.kind.value,
            "title": entry.title,
            "date": entry.date,
            "start": entry.start,
            "duration_minutes": entry.duration_minutes,
            "occupied_periods": list(entry.occupied_periods),
        }
        if entry.group_id is not None:
            row["group_id"] = entry.group_id
        if entry.completed_on is not None:
            row["completed_on"] = entry.completed_on
        rows.append(row)
    save_toml(get_assessments_path(root, year, school_class_id), {"assessments": rows})


def _load_assessment(row: object, index: int) -> Assessment:
    if not isinstance(row, dict):
        raise AssessmentsFileError(
            f"Eintrag {index} in 'assessments' muss eine Tabelle sein."
        )
    try:
        day = row["date"]
        start = row["start"]
        periods = row.get("occupied_periods", [])
        completed_on = row.get("completed_on")
        if not isinstance(periods, list):
            raise TypeError("'occupied_periods' muss eine Liste sein.")
        return Assessment(
            id=row["id"],
            subject_id=row["subject_id"],
            kind=AssessmentKind(row["kind"]),
            title=row["title"],
            date=Date.fromisoformat(day) if isinstance(day, str) else day,
            start=time.fromisoformat(start) if isinstance(start, str) else start,
            duration_minutes=row["duration_minutes"],
            occupied_periods=tuple(periods),
            group_id=row.get("group_id"),
            completed_on=Date.fromisoformat(completed_on)
            if isinstance(completed_on, str)
            else completed_on,
        )
    except KeyError as error:
        raise AssessmentsFileError(
            f"Eintrag {index}: Pflichtfeld {error} fehlt."
        ) from error
    except (TypeError, ValueError) as error:
        raise AssessmentsFileError(f"Eintrag {index} ist ungültig: {error}") from error


def _validate_assessment_ids(entries: list[Assessment]) -> None:
    seen: set[str] = set()
    for index, entry in enumerate(entries, 1):
        if entry.id in seen:
            raise AssessmentsFileError(
                f"Eintrag {index}: Die ID '{entry.id}' kommt mehrfach vor."
            )
        seen.add(entry.id)
