from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from schooltools_tui.school_class import get_school_class_path
from schooltools_tui.storage import load_toml, save_toml

SEQUENCE_STATUS_FILE_NAME = Path("sequence-status.toml")


class SequenceStatusFileError(ValueError):
    """Raised when a sequence status file has invalid contents."""


class ProgressAction(StrEnum):
    COMPLETED = "completed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class LessonProgressEntry:
    subject_id: str
    sequence_id: str
    lesson_id: str
    action: ProgressAction


@dataclass(frozen=True)
class ActiveSequence:
    subject_id: str
    sequence_id: str

    def __post_init__(self) -> None:
        pass


@dataclass(frozen=True)
class SequenceStatus:
    active_sequences: tuple[ActiveSequence, ...]
    progress: tuple[LessonProgressEntry, ...]

    def __post_init__(self) -> None:
        subject_ids = [active.subject_id for active in self.active_sequences]

        if len(subject_ids) != len(set(subject_ids)):
            raise ValueError("Pro Fach darf nur eine Sequenz aktiv sein.")

        lesson_keys = [
            (entry.subject_id, entry.sequence_id, entry.lesson_id)
            for entry in self.progress
        ]

        if len(lesson_keys) != len(set(lesson_keys)):
            raise ValueError("Eine Stunde darf nur einen Fortschrittseintrag besitzen.")


def get_sequence_status_path(
    root: Path,
    year: str,
    school_class_id: str,
) -> Path:
    class_directory = get_school_class_path(root, year, school_class_id).parent
    return class_directory / SEQUENCE_STATUS_FILE_NAME


def load_sequence_status(
    root: Path,
    year: str,
    school_class_id: str,
) -> SequenceStatus:
    path = get_sequence_status_path(root, year, school_class_id)

    try:
        data = load_toml(path)
        _require_exact_keys(data, {"active_sequences", "progress"}, "Statusdatei")

        active_sequences_data = _require_list(data, "active_sequences")
        progress_data = _require_list(data, "progress")

        active_sequences = tuple(
            _load_active_sequence(entry, index)
            for index, entry in enumerate(active_sequences_data, start=1)
        )
        progress = tuple(
            _load_progress_entry(entry, index)
            for index, entry in enumerate(progress_data, start=1)
        )

        return SequenceStatus(
            active_sequences=active_sequences,
            progress=progress,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise SequenceStatusFileError(
            f"Ungültige Sequenzstatusdatei '{path}': {error}"
        ) from error


def save_sequence_status(
    root: Path,
    year: str,
    school_class_id: str,
    status: SequenceStatus,
) -> None:
    data: dict[str, Any] = {
        "active_sequences": [
            {
                "subject_id": active_sequence.subject_id,
                "sequence_id": active_sequence.sequence_id,
            }
            for active_sequence in status.active_sequences
        ],
        "progress": [
            {
                "subject_id": entry.subject_id,
                "sequence_id": entry.sequence_id,
                "lesson_id": entry.lesson_id,
                "action": entry.action.value,
            }
            for entry in status.progress
        ],
    }

    path = get_sequence_status_path(root, year, school_class_id)
    save_toml(path, data)


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


def _load_progress_entry(data: Any, index: int) -> LessonProgressEntry:
    if not isinstance(data, dict):
        raise TypeError(f"Fortschrittseintrag {index} muss eine TOML-Tabelle sein.")

    _require_exact_keys(
        data,
        {"subject_id", "sequence_id", "lesson_id", "action"},
        f"Fortschrittseintrag {index}",
    )
    return LessonProgressEntry(
        subject_id=_require_string(data, "subject_id"),
        sequence_id=_require_string(data, "sequence_id"),
        lesson_id=_require_string(data, "lesson_id"),
        action=ProgressAction(_require_string(data, "action")),
    )


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


def _require_exact_keys(
    data: dict[str, Any],
    expected_keys: set[str],
    description: str,
) -> None:
    actual_keys = set(data)
    if actual_keys == expected_keys:
        return

    missing_keys = sorted(expected_keys - actual_keys)
    unexpected_keys = sorted(actual_keys - expected_keys)
    details = []
    if missing_keys:
        details.append(f"fehlend: {', '.join(missing_keys)}")
    if unexpected_keys:
        details.append(f"unbekannt: {', '.join(unexpected_keys)}")

    raise ValueError(f"{description} enthält ungültige Schlüssel ({'; '.join(details)}).")
