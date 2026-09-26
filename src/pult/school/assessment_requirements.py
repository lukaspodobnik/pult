"""Jährliche LNW-Vorgaben je Fach und Jahrgangsstufe, unabhängig von Terminen."""

from dataclasses import dataclass, replace
from enum import StrEnum
from importlib.resources import files
from pathlib import Path
from tomllib import TOMLDecodeError, loads
from typing import Any

from pult.school.assessment import AssessmentKind
from pult.school.calendar import validate_school_year
from pult.school.subject import SUBJECT_ID_PATTERN
from pult.storage import load_toml, save_toml

ASSESSMENT_REQUIREMENTS_FILE_NAME = "assessment-requirements.toml"


class AssessmentRequirementsFileError(ValueError):
    """Die Vorgaben zu Leistungsnachweisen sind ungültig."""


class AssessmentCategory(StrEnum):
    LARGE_WRITTEN = "large_written"
    SMALL_WRITTEN = "small_written"


def assessment_category(kind: AssessmentKind) -> AssessmentCategory | None:
    """Jahrgangsstufentests zählen unabhängig von Verknüpfungen zu keiner Kategorie."""
    return {
        AssessmentKind.SCHOOL_EXAM: AssessmentCategory.LARGE_WRITTEN,
        AssessmentKind.IMPROMPTU_TEST: AssessmentCategory.SMALL_WRITTEN,
        AssessmentKind.ANNOUNCED_TEST: AssessmentCategory.SMALL_WRITTEN,
        AssessmentKind.YEAR_GROUP_TEST: None,
    }[kind]


@dataclass(frozen=True)
class AssessmentMinimum:
    category: AssessmentCategory
    count: int

    def __post_init__(self) -> None:
        if not isinstance(self.category, AssessmentCategory):
            raise ValueError("Ungültige Leistungsnachweiskategorie.")
        if type(self.count) is not int or self.count < 0:
            raise ValueError("Die Mindestzahl muss eine nichtnegative ganze Zahl sein.")


@dataclass(frozen=True)
class AssessmentRequirement:
    """Fehlende Mindestzahl bedeutet keine Vorgabe; erlaubt sind nur allowed_kinds.

    Fach-IDs unterscheiden bereits das grundlegende und erhöhte Niveau.
    Weitere Kategorien (etwa mündlich) können später ergänzt werden.
    """

    subject_id: str
    grade_level: int
    allowed_kinds: tuple[AssessmentKind, ...]
    minimums: tuple[AssessmentMinimum, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.subject_id, str) or not SUBJECT_ID_PATTERN.fullmatch(
            self.subject_id
        ):
            raise ValueError("Ungültige Fach-ID.")
        if type(self.grade_level) is not int or not 5 <= self.grade_level <= 13:
            raise ValueError("Die Jahrgangsstufe muss zwischen 5 und 13 liegen.")
        if not isinstance(self.allowed_kinds, tuple) or any(
            not isinstance(kind, AssessmentKind) for kind in self.allowed_kinds
        ):
            raise ValueError("Erlaubte Arten müssen als Tupel von LNW-Arten vorliegen.")
        if len(set(self.allowed_kinds)) != len(self.allowed_kinds):
            raise ValueError("Eine erlaubte Art darf nur einmal vorkommen.")
        if not isinstance(self.minimums, tuple) or any(
            not isinstance(minimum, AssessmentMinimum) for minimum in self.minimums
        ):
            raise ValueError("Mindestzahlen müssen als Tupel von Vorgaben vorliegen.")
        categories = [minimum.category for minimum in self.minimums]
        if len(set(categories)) != len(categories):
            raise ValueError("Eine Kategorie darf nur eine Mindestzahl haben.")
        allowed_categories = {assessment_category(kind) for kind in self.allowed_kinds}
        if any(
            minimum.count > 0 and minimum.category not in allowed_categories
            for minimum in self.minimums
        ):
            raise ValueError(
                "Eine positive Mindestzahl benötigt eine erlaubte LNW-Art."
            )

    def minimum_for(self, category: AssessmentCategory) -> int | None:
        return next(
            (
                minimum.count
                for minimum in self.minimums
                if minimum.category == category
            ),
            None,
        )


def get_assessment_requirements_path(root: Path, year: str) -> Path:
    return (
        root
        / "school-years"
        / validate_school_year(year)
        / ASSESSMENT_REQUIREMENTS_FILE_NAME
    )


def _validate_entries(entries: list[AssessmentRequirement]) -> None:
    seen: set[tuple[str, int]] = set()
    for entry in entries:
        if not isinstance(entry, AssessmentRequirement):
            raise AssessmentRequirementsFileError("Ungültige LNW-Vorgabe.")
        key = (entry.subject_id, entry.grade_level)
        if key in seen:
            raise AssessmentRequirementsFileError(
                f"Doppelte Vorgabe für {entry.subject_id}, Jahrgangsstufe {entry.grade_level}."
            )
        seen.add(key)


def _parse(data: dict[str, Any], source: str) -> list[AssessmentRequirement]:
    try:
        if set(data) != {"requirements"} or not isinstance(data["requirements"], list):
            raise ValueError("Erwartet wird die Liste 'requirements'.")
        entries = []
        for index, row in enumerate(data["requirements"], 1):
            try:
                if not isinstance(row, dict) or set(row) - {
                    "subject_id",
                    "grade_level",
                    "allowed_kinds",
                    "minimums",
                }:
                    raise ValueError("Ungültige Tabelle oder unbekanntes Feld.")
                if not isinstance(row["allowed_kinds"], list):
                    raise ValueError("'allowed_kinds' muss eine Liste sein.")
                minimums = row.get("minimums", {})
                if not isinstance(minimums, dict):
                    raise ValueError("'minimums' muss eine Tabelle sein.")
                entries.append(
                    AssessmentRequirement(
                        subject_id=row["subject_id"],
                        grade_level=row["grade_level"],
                        allowed_kinds=tuple(
                            AssessmentKind(kind) for kind in row["allowed_kinds"]
                        ),
                        minimums=tuple(
                            AssessmentMinimum(AssessmentCategory(category), count)
                            for category, count in minimums.items()
                        ),
                    )
                )
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError(f"Eintrag {index}: {error}") from error
        _validate_entries(entries)
        return sorted(entries, key=lambda entry: (entry.subject_id, entry.grade_level))
    except (TypeError, ValueError) as error:
        raise AssessmentRequirementsFileError(f"{source}: {error}") from error


def load_default_assessment_requirements(year: str) -> list[AssessmentRequirement]:
    """Lade die mitgelieferten Vorgaben (G9); berücksichtige die Änderung 2026/27."""
    year = validate_school_year(year)
    source = files("pult.defaults") / ASSESSMENT_REQUIREMENTS_FILE_NAME
    entries = _parse(loads(source.read_text(encoding="utf-8")), str(source))
    if year < "2026-2027":
        entries = [
            replace(
                entry,
                minimums=(AssessmentMinimum(AssessmentCategory.LARGE_WRITTEN, 4),),
            )
            if entry.subject_id == "mathematik" and entry.grade_level == 9
            else entry
            for entry in entries
        ]
    return entries


def load_assessment_requirements(root: Path, year: str) -> list[AssessmentRequirement]:
    """Lade Vorgaben, bei Altbeständen ohne Datei aus dem letzten Vorjahr/Standard.

    Lesen schreibt keine Dateien. Fehlerhafte vorhandene Dateien werden niemals
    durch Standards verdeckt. Eine vorhandene leere Liste bleibt bewusst leer.
    """
    year = validate_school_year(year)
    path = get_assessment_requirements_path(root, year)
    if not path.exists():
        candidates = []
        for candidate in (root / "school-years").glob(
            f"*/{ASSESSMENT_REQUIREMENTS_FILE_NAME}"
        ):
            try:
                candidate_year = validate_school_year(candidate.parent.name)
            except ValueError:
                continue
            if candidate_year < year:
                candidates.append((candidate_year, candidate))
        if not candidates:
            return load_default_assessment_requirements(year)
        _, path = max(candidates)
    try:
        return _parse(load_toml(path), str(path))
    except TOMLDecodeError as error:
        raise AssessmentRequirementsFileError(
            f"Ungültiges TOML in {path}: {error}"
        ) from error


def save_assessment_requirements(
    root: Path, year: str, entries: list[AssessmentRequirement]
) -> None:
    """Validiere vollständig vor dem atomaren Speichern im bestehenden Schuljahr."""
    _validate_entries(entries)
    rows = [
        {
            "subject_id": entry.subject_id,
            "grade_level": entry.grade_level,
            "allowed_kinds": [kind.value for kind in entry.allowed_kinds],
            "minimums": {
                minimum.category.value: minimum.count for minimum in entry.minimums
            },
        }
        for entry in sorted(
            entries, key=lambda entry: (entry.subject_id, entry.grade_level)
        )
    ]
    save_toml(get_assessment_requirements_path(root, year), {"requirements": rows})


def initialize_assessment_requirements(root: Path, year: str) -> None:
    """Übernimm die letzte frühere Einstellung als eigene Kopie, ohne Überschreiben."""
    if get_assessment_requirements_path(root, year).exists():
        return
    save_assessment_requirements(root, year, load_assessment_requirements(root, year))
