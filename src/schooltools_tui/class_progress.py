from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from schooltools_tui.sequence import validate_id


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
                    "Das Überspringen einer Lesson darf keinen Termin verbuchen."
                )
            return

        if self.origin is TeachingOrigin.NONE:
            raise ValueError(
                "Nur das Überspringen einer Lesson darf ohne Unterrichtstermin erfolgen."
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
            active_sequence.subject_id
            for active_sequence in self.active_sequences
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
            if entry.action
            in {TeachingAction.COMPLETED, TeachingAction.SKIPPED}
        ]
        if len(progressed_lessons) != len(set(progressed_lessons)):
            raise ValueError(
                "Eine Lesson darf nur einmal abgeschlossen oder übersprungen werden."
            )
