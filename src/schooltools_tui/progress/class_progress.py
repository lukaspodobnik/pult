from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Any

from schooltools_tui.curriculum.sequence import Sequence, validate_id
from schooltools_tui.school.school_class import SchoolClass, get_school_class_path
from schooltools_tui.storage import load_toml, save_toml

CLASS_PROGRESS_FILE_NAME = Path("class-progress.toml")


class ClassProgressFileError(ValueError):
    """Raised when a class progress file has invalid contents."""


class ClassProgressValidationError(ValueError):
    """Raised when class progress contradicts its class or sequence library."""


class TeachingOrigin(StrEnum):
    SCHEDULED = "scheduled"
    ADDITIONAL = "additional"
    NONE = "none"


class TeachingAction(StrEnum):
    COMPLETED = "completed"
    SKIPPED = "skipped"
    CONTINUED = "continued"
    CANCELLED = "cancelled"
    OTHER = "other"


@dataclass(frozen=True)
class ActiveSequence:
    subject_id: str
    sequence_id: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "subject_id",
            validate_id(self.subject_id, "Die Fach-ID"),
        )
        object.__setattr__(
            self,
            "sequence_id",
            validate_id(self.sequence_id, "Die Sequenz-ID"),
        )


@dataclass(frozen=True)
class TeachingLogEntry:
    date: date
    subject_id: str
    sequence_id: str
    action: TeachingAction
    origin: TeachingOrigin
    comment: str = ""
    lesson_id: str | None = None
    period: int | None = None

    def __post_init__(self) -> None:
        if type(self.date) is not date:
            raise TypeError("Das Datum muss ein Datum ohne Uhrzeit sein.")

        if not isinstance(self.comment, str):
            raise TypeError("Der Kommentar muss ein Text sein.")

        object.__setattr__(
            self,
            "subject_id",
            validate_id(self.subject_id, "Die Fach-ID"),
        )
        object.__setattr__(
            self,
            "sequence_id",
            validate_id(self.sequence_id, "Die Sequenz-ID"),
        )
        object.__setattr__(self, "comment", self.comment.strip())

        if not isinstance(self.action, TeachingAction):
            raise TypeError("Die Unterrichtsaktion ist ungültig.")

        if not isinstance(self.origin, TeachingOrigin):
            raise TypeError("Die Herkunft des Unterrichtstermins ist ungültig.")

        if self.lesson_id is not None:
            object.__setattr__(
                self,
                "lesson_id",
                validate_id(self.lesson_id, "Die Stunden-ID"),
            )

        if self.period is not None and (
            isinstance(self.period, bool)
            or not isinstance(self.period, int)
            or self.period < 1
        ):
            raise ValueError("Die Stundennummer muss größer als 0 sein.")

        self._validate_action()

    def _validate_action(self) -> None:
        actions_with_lesson = {
            TeachingAction.COMPLETED,
            TeachingAction.SKIPPED,
            TeachingAction.CONTINUED,
        }
        if self.action in actions_with_lesson and self.lesson_id is None:
            raise ValueError(
                f"Die Aktion '{self.action.value}' benötigt eine Stunden-ID."
            )

        if self.action is TeachingAction.OTHER and self.lesson_id is not None:
            raise ValueError(
                "Ein anderer Unterrichtsinhalt darf keine Stunden-ID besitzen."
            )

        if self.origin is TeachingOrigin.SCHEDULED and self.period is None:
            raise ValueError(
                "Ein regulärer Stundenplantermin benötigt eine Stundennummer."
            )

        if self.origin is not TeachingOrigin.SCHEDULED and self.period is not None:
            raise ValueError(
                "Nur ein regulärer Stundenplantermin darf eine Stundennummer besitzen."
            )

        if self.action is TeachingAction.SKIPPED:
            if self.origin is not TeachingOrigin.NONE:
                raise ValueError(
                    "Das Überspringen einer geplanten Stunde darf keinen Termin verbuchen."
                )
            return

        if self.origin is TeachingOrigin.NONE:
            raise ValueError(
                "Nur das Überspringen einer geplanten Stunde darf ohne Unterrichtstermin erfolgen."
            )

        if (
            self.action is TeachingAction.CANCELLED
            and self.origin is not TeachingOrigin.SCHEDULED
        ):
            raise ValueError(
                "Nur ein regulärer Stundenplantermin kann spontan ausfallen."
            )


@dataclass(frozen=True)
class ClassProgress:
    active_sequences: tuple[ActiveSequence, ...]
    entries: tuple[TeachingLogEntry, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.active_sequences, tuple) or any(
            not isinstance(active_sequence, ActiveSequence)
            for active_sequence in self.active_sequences
        ):
            raise TypeError("Aktive Sequenzen müssen als Tupel angegeben werden.")

        if not isinstance(self.entries, tuple) or any(
            not isinstance(entry, TeachingLogEntry) for entry in self.entries
        ):
            raise TypeError("Protokolleinträge müssen als Tupel angegeben werden.")

        subject_ids = [
            active_sequence.subject_id for active_sequence in self.active_sequences
        ]
        if len(subject_ids) != len(set(subject_ids)):
            raise ValueError("Pro Fach darf nur eine Sequenz aktiv sein.")

        scheduled_occurrences = [
            (entry.date, entry.period)
            for entry in self.entries
            if entry.origin is TeachingOrigin.SCHEDULED
        ]
        if len(scheduled_occurrences) != len(set(scheduled_occurrences)):
            raise ValueError(
                "Ein Stundenplantermin darf nur einmal protokolliert werden."
            )

        progressed_lessons = [
            (entry.subject_id, entry.sequence_id, entry.lesson_id)
            for entry in self.entries
            if entry.action in {TeachingAction.COMPLETED, TeachingAction.SKIPPED}
        ]
        if len(progressed_lessons) != len(set(progressed_lessons)):
            raise ValueError(
                "Eine geplante Stunde darf nur einmal abgeschlossen oder übersprungen werden."
            )


def validate_class_progress(
    progress: ClassProgress,
    school_class: SchoolClass,
    sequences: list[Sequence],
) -> None:
    """Prüfe den Fortschritt gegen Klasse, Fächer und Sequenzbibliothek."""
    expected_subject_ids = set(school_class.subject_ids)
    active_subject_ids = {
        active_sequence.subject_id for active_sequence in progress.active_sequences
    }
    if active_subject_ids != expected_subject_ids:
        missing_subject_ids = sorted(expected_subject_ids - active_subject_ids)
        unexpected_subject_ids = sorted(active_subject_ids - expected_subject_ids)
        details = []
        if missing_subject_ids:
            details.append(f"ohne aktive Sequenz: {', '.join(missing_subject_ids)}")
        if unexpected_subject_ids:
            details.append(
                f"gehören nicht zur Klasse: {', '.join(unexpected_subject_ids)}"
            )
        raise ClassProgressValidationError("; ".join(details))

    sequences_by_key: dict[tuple[str, str], Sequence] = {}
    for sequence in sequences:
        if (
            sequence.grade_level != school_class.grade_level
            or sequence.subject_id not in expected_subject_ids
        ):
            continue

        key = (sequence.subject_id, sequence.id)
        if key in sequences_by_key:
            raise ClassProgressValidationError(
                f"Die Sequenz '{sequence.id}' ist für das Fach "
                f"'{sequence.subject_id}' mehrfach vorhanden."
            )
        sequences_by_key[key] = sequence

    for active_sequence in progress.active_sequences:
        key = (active_sequence.subject_id, active_sequence.sequence_id)
        if key not in sequences_by_key:
            raise ClassProgressValidationError(
                f"Die aktive Sequenz '{active_sequence.sequence_id}' existiert "
                f"für das Fach '{active_sequence.subject_id}' und die "
                f"{school_class.grade_level}. Jahrgangsstufe nicht."
            )

    progressed_entries_by_sequence: dict[tuple[str, str], list[TeachingLogEntry]] = {}
    for entry in progress.entries:
        if entry.subject_id not in expected_subject_ids:
            raise ClassProgressValidationError(
                f"Das Fach '{entry.subject_id}' gehört nicht zur Klasse "
                f"'{school_class.id}'."
            )

        key = (entry.subject_id, entry.sequence_id)
        sequence = sequences_by_key.get(key)
        if sequence is None:
            raise ClassProgressValidationError(
                f"Die Sequenz '{entry.sequence_id}' existiert für das Fach "
                f"'{entry.subject_id}' und die {school_class.grade_level}. "
                "Jahrgangsstufe nicht."
            )

        if entry.lesson_id is not None and entry.lesson_id not in {
            lesson.id for lesson in sequence.lessons
        }:
            raise ClassProgressValidationError(
                f"Die geplante Stunde '{entry.lesson_id}' existiert in der Sequenz "
                f"'{entry.sequence_id}' nicht."
            )

        if entry.action in {
            TeachingAction.COMPLETED,
            TeachingAction.SKIPPED,
        }:
            progressed_entries_by_sequence.setdefault(key, []).append(entry)

    for key, entries in progressed_entries_by_sequence.items():
        sequence = sequences_by_key[key]
        actual_lesson_ids = tuple(entry.lesson_id for entry in entries)
        expected_lesson_ids = tuple(
            lesson.id for lesson in sequence.lessons[: len(entries)]
        )
        if actual_lesson_ids != expected_lesson_ids:
            raise ClassProgressValidationError(
                f"Der Fortschritt der Sequenz '{sequence.id}' muss ihrer "
                "Stundenreihenfolge ohne Lücken entsprechen."
            )


def get_class_progress_path(
    root: Path,
    year: str,
    school_class_id: str,
) -> Path:
    """Gib den kanonischen Pfad des Unterrichtsprotokolls einer Klasse zurück."""
    class_directory = get_school_class_path(root, year, school_class_id).parent
    return class_directory / CLASS_PROGRESS_FILE_NAME


def load_class_progress(
    root: Path,
    year: str,
    school_class_id: str,
) -> ClassProgress:
    """Lade das Protokoll einer Klasse und validiere dessen Dateiformat."""
    path = get_class_progress_path(root, year, school_class_id)

    try:
        data = load_toml(path)
        _require_exact_keys(data, {"active_sequences", "entries"}, "Statusdatei")
        active_sequences_data = _require_list(data, "active_sequences")
        entries_data = _require_list(data, "entries")

        return ClassProgress(
            active_sequences=tuple(
                _load_active_sequence(entry, index)
                for index, entry in enumerate(active_sequences_data, start=1)
            ),
            entries=tuple(
                _load_teaching_log_entry(entry, index)
                for index, entry in enumerate(entries_data, start=1)
            ),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ClassProgressFileError(
            f"Ungültige Klassenfortschrittsdatei '{path}': {error}"
        ) from error


def save_class_progress(
    root: Path,
    year: str,
    school_class_id: str,
    progress: ClassProgress,
) -> None:
    """Speichere aktive Sequenzen und Unterrichtsprotokoll einer Klasse."""
    data: dict[str, Any] = {
        "active_sequences": [
            {
                "subject_id": active_sequence.subject_id,
                "sequence_id": active_sequence.sequence_id,
            }
            for active_sequence in progress.active_sequences
        ],
        "entries": [_serialize_teaching_log_entry(entry) for entry in progress.entries],
    }
    save_toml(get_class_progress_path(root, year, school_class_id), data)


def _load_active_sequence(data: Any, index: int) -> ActiveSequence:
    if not isinstance(data, dict):
        raise TypeError(f"Aktive Sequenz {index} muss eine TOML-Tabelle sein.")

    _require_exact_keys(
        data,
        {"subject_id", "sequence_id"},
        f"Aktive Sequenz {index}",
    )
    return ActiveSequence(
        subject_id=_require_string(data, "subject_id"),
        sequence_id=_require_string(data, "sequence_id"),
    )


def _load_teaching_log_entry(data: Any, index: int) -> TeachingLogEntry:
    if not isinstance(data, dict):
        raise TypeError(f"Protokolleintrag {index} muss eine TOML-Tabelle sein.")

    required_keys = {
        "date",
        "subject_id",
        "sequence_id",
        "action",
        "origin",
        "comment",
    }
    optional_keys = {"lesson_id", "period"}
    _require_allowed_keys(
        data,
        required_keys,
        optional_keys,
        f"Protokolleintrag {index}",
    )

    return TeachingLogEntry(
        date=_require_date(data, "date"),
        subject_id=_require_string(data, "subject_id"),
        sequence_id=_require_string(data, "sequence_id"),
        action=TeachingAction(_require_string(data, "action")),
        origin=TeachingOrigin(_require_string(data, "origin")),
        comment=_require_string(data, "comment"),
        lesson_id=_optional_string(data, "lesson_id"),
        period=_optional_integer(data, "period"),
    )


def _serialize_teaching_log_entry(entry: TeachingLogEntry) -> dict[str, Any]:
    data: dict[str, Any] = {
        "date": entry.date,
        "subject_id": entry.subject_id,
        "sequence_id": entry.sequence_id,
        "action": entry.action.value,
        "origin": entry.origin.value,
        "comment": entry.comment,
    }
    if entry.lesson_id is not None:
        data["lesson_id"] = entry.lesson_id
    if entry.period is not None:
        data["period"] = entry.period
    return data


def _require_list(data: dict[str, Any], key: str) -> list[Any]:
    value = data[key]
    if not isinstance(value, list):
        raise TypeError(f"'{key}' muss eine Liste sein.")
    return value


def _require_string(data: dict[str, Any], key: str) -> str:
    value = data[key]
    if not isinstance(value, str):
        raise TypeError(f"'{key}' muss ein Text sein.")
    return value


def _optional_string(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    if value is not None and not isinstance(value, str):
        raise TypeError(f"'{key}' muss ein Text sein.")
    return value


def _optional_integer(data: dict[str, Any], key: str) -> int | None:
    value = data.get(key)
    if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
        raise TypeError(f"'{key}' muss eine ganze Zahl sein.")
    return value


def _require_date(data: dict[str, Any], key: str) -> date:
    value = data[key]
    if type(value) is not date:
        raise TypeError(f"'{key}' muss ein TOML-Datum sein.")
    return value


def _require_exact_keys(
    data: dict[str, Any],
    expected_keys: set[str],
    description: str,
) -> None:
    _require_allowed_keys(data, expected_keys, set(), description)


def _require_allowed_keys(
    data: dict[str, Any],
    required_keys: set[str],
    optional_keys: set[str],
    description: str,
) -> None:
    actual_keys = set(data)
    missing_keys = sorted(required_keys - actual_keys)
    unexpected_keys = sorted(actual_keys - required_keys - optional_keys)
    if not missing_keys and not unexpected_keys:
        return

    details = []
    if missing_keys:
        details.append(f"fehlend: {', '.join(missing_keys)}")
    if unexpected_keys:
        details.append(f"unbekannt: {', '.join(unexpected_keys)}")
    raise ValueError(
        f"{description} enthält ungültige Schlüssel ({'; '.join(details)})."
    )
