from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from schooltools_tui.curriculum.sequence import Sequence
from schooltools_tui.progress.class_progress import (
    ActiveSequence,
    ClassProgress,
    TeachingAction,
    TeachingLogEntry,
    TeachingOrigin,
)
from schooltools_tui.progress.queries import (
    PlannedLesson,
    get_next_lesson,
    get_suggested_next_sequence,
)


class ProgressCommandError(ValueError):
    """Fehler beim Ausführen von progress-commands."""


class LessonCompletionState(StrEnum):
    CONTINUES_SEQUENCE = "continues_sequence"
    NEEDS_NEXT_SEQUENCE = "needs_next_sequence"
    COMPLETES_SUBJECT = "completes_subject"


@dataclass(frozen=True)
class CompleteLessonResult:
    progress: ClassProgress
    state: LessonCompletionState
    subject_id: str


def complete_lesson(
    old_progress: ClassProgress,
    planned_lesson: PlannedLesson,
    sequences: list[Sequence],
    comment: str = "",
) -> CompleteLessonResult:
    """Schließe die nächste Lesson ab und verbrauche ihren Stundenplantermin."""
    return _progress_lesson(
        old_progress,
        planned_lesson,
        sequences,
        action=TeachingAction.COMPLETED,
        origin=TeachingOrigin.SCHEDULED,
        entry_date=planned_lesson.date,
        period=planned_lesson.period,
        comment=comment,
    )


def skip_lesson(
    old_progress: ClassProgress,
    planned_lesson: PlannedLesson,
    sequences: list[Sequence],
    comment: str = "",
) -> CompleteLessonResult:
    """Überspringe die nächste Lesson, ohne einen Stundenplantermin zu verbrauchen."""
    return _progress_lesson(
        old_progress,
        planned_lesson,
        sequences,
        action=TeachingAction.SKIPPED,
        origin=TeachingOrigin.NONE,
        entry_date=planned_lesson.date,
        period=None,
        comment=comment,
    )


def continue_lesson(
    old_progress: ClassProgress,
    planned_lesson: PlannedLesson,
    sequences: list[Sequence],
    comment: str = "",
) -> ClassProgress:
    """Verbrauche den Termin, lasse die aktuelle Lesson aber weiterhin offen."""
    _validate_planned_lesson(old_progress, planned_lesson, sequences)
    return _append_entry(
        old_progress,
        TeachingLogEntry(
            date=planned_lesson.date,
            subject_id=planned_lesson.subject_id,
            sequence_id=planned_lesson.sequence_id,
            action=TeachingAction.CONTINUED,
            origin=TeachingOrigin.SCHEDULED,
            lesson_id=planned_lesson.lesson.id,
            period=planned_lesson.period,
            comment=comment,
        ),
    )


def cancel_scheduled_lesson(
    old_progress: ClassProgress,
    planned_lesson: PlannedLesson,
    sequences: list[Sequence],
    comment: str = "",
) -> ClassProgress:
    """Protokolliere einen spontanen Ausfall, ohne die Lesson abzuschließen."""
    _validate_planned_lesson(old_progress, planned_lesson, sequences)
    return _append_entry(
        old_progress,
        TeachingLogEntry(
            date=planned_lesson.date,
            subject_id=planned_lesson.subject_id,
            sequence_id=planned_lesson.sequence_id,
            action=TeachingAction.CANCELLED,
            origin=TeachingOrigin.SCHEDULED,
            lesson_id=planned_lesson.lesson.id,
            period=planned_lesson.period,
            comment=comment,
        ),
    )


def add_extra_lesson(
    old_progress: ClassProgress,
    subject_id: str,
    entry_date: date,
    comment: str = "",
) -> ClassProgress:
    """Protokolliere Zusatzunterricht, der keine geplante Lesson abschließt."""
    active_sequence = _get_active_sequence(old_progress, subject_id)
    return _append_entry(
        old_progress,
        TeachingLogEntry(
            date=entry_date,
            subject_id=subject_id,
            sequence_id=active_sequence.sequence_id,
            action=TeachingAction.OTHER,
            origin=TeachingOrigin.ADDITIONAL,
            comment=comment,
        ),
    )


def complete_additional_lesson(
    old_progress: ClassProgress,
    subject_id: str,
    grade_level: int,
    entry_date: date,
    sequences: list[Sequence],
    comment: str = "",
) -> CompleteLessonResult:
    """Schließe die nächste Lesson in einem zusätzlichen Unterrichtstermin ab."""
    active_sequence = _get_active_sequence(old_progress, subject_id)
    lesson = get_next_lesson(
        old_progress,
        sequences,
        subject_id,
        grade_level,
    )
    if lesson is None:
        raise ProgressCommandError("Die aktive Sequenz ist bereits abgeschlossen.")

    new_progress = _append_entry(
        old_progress,
        TeachingLogEntry(
            date=entry_date,
            subject_id=subject_id,
            sequence_id=active_sequence.sequence_id,
            action=TeachingAction.COMPLETED,
            origin=TeachingOrigin.ADDITIONAL,
            lesson_id=lesson.id,
            period=None,
            comment=comment,
        ),
    )
    return _build_completion_result(
        new_progress,
        sequences,
        subject_id,
        grade_level,
    )


def undo_last_entry(progress: ClassProgress) -> ClassProgress:
    """Entferne den zuletzt angelegten Protokolleintrag und korrigiere die Sequenz."""
    if not progress.entries:
        raise ProgressCommandError("Es gibt keinen Protokolleintrag zum Zurücknehmen.")

    removed_entry = progress.entries[-1]
    active_sequences = progress.active_sequences
    if removed_entry.action in {
        TeachingAction.COMPLETED,
        TeachingAction.SKIPPED,
    }:
        active_sequences = tuple(
            ActiveSequence(active.subject_id, removed_entry.sequence_id)
            if active.subject_id == removed_entry.subject_id
            else active
            for active in progress.active_sequences
        )

    return ClassProgress(
        active_sequences=active_sequences,
        entries=progress.entries[:-1],
    )


def set_active_sequence(
    progress: ClassProgress,
    subject_id: str,
    sequence_id: str,
    grade_level: int,
    sequences: list[Sequence],
) -> ClassProgress:
    """Aktiviere eine andere noch nicht abgeschlossene Sequenz eines Fachs."""
    current = _get_active_sequence(progress, subject_id)
    if current.sequence_id == sequence_id:
        raise ProgressCommandError("Diese Sequenz ist bereits aktiv.")

    selected_sequence = next(
        (
            sequence
            for sequence in sequences
            if sequence.grade_level == grade_level
            and sequence.subject_id == subject_id
            and sequence.id == sequence_id
        ),
        None,
    )
    if selected_sequence is None:
        raise ProgressCommandError(
            "Die ausgewählte Sequenz gehört nicht zum Fach und zur Jahrgangsstufe."
        )

    if not selected_sequence.lessons:
        raise ProgressCommandError(
            "Die ausgewählte Sequenz enthält noch keine Lessons."
        )

    progressed_lesson_ids = _get_progressed_lesson_ids(
        progress,
        subject_id,
        sequence_id,
    )
    if all(lesson.id in progressed_lesson_ids for lesson in selected_sequence.lessons):
        raise ProgressCommandError("Die ausgewählte Sequenz ist bereits abgeschlossen.")

    active_sequences = tuple(
        ActiveSequence(subject_id, sequence_id)
        if active.subject_id == subject_id
        else active
        for active in progress.active_sequences
    )
    return ClassProgress(
        active_sequences=active_sequences,
        entries=progress.entries,
    )


def _progress_lesson(
    old_progress: ClassProgress,
    planned_lesson: PlannedLesson,
    sequences: list[Sequence],
    *,
    action: TeachingAction,
    origin: TeachingOrigin,
    entry_date: date,
    period: int | None,
    comment: str,
) -> CompleteLessonResult:
    _validate_planned_lesson(old_progress, planned_lesson, sequences)
    new_progress = _append_entry(
        old_progress,
        TeachingLogEntry(
            date=entry_date,
            subject_id=planned_lesson.subject_id,
            sequence_id=planned_lesson.sequence_id,
            action=action,
            origin=origin,
            lesson_id=planned_lesson.lesson.id,
            period=period,
            comment=comment,
        ),
    )

    return _build_completion_result(
        new_progress,
        sequences,
        planned_lesson.subject_id,
        planned_lesson.grade_level,
    )


def _build_completion_result(
    progress: ClassProgress,
    sequences: list[Sequence],
    subject_id: str,
    grade_level: int,
) -> CompleteLessonResult:
    next_lesson = get_next_lesson(
        progress,
        sequences,
        subject_id,
        grade_level,
    )
    if next_lesson is not None:
        state = LessonCompletionState.CONTINUES_SEQUENCE
    elif (
        get_suggested_next_sequence(
            progress,
            sequences,
            subject_id,
            grade_level,
        )
        is not None
    ):
        state = LessonCompletionState.NEEDS_NEXT_SEQUENCE
    else:
        state = LessonCompletionState.COMPLETES_SUBJECT

    return CompleteLessonResult(
        progress=progress,
        state=state,
        subject_id=subject_id,
    )


def _validate_planned_lesson(
    progress: ClassProgress,
    planned_lesson: PlannedLesson,
    sequences: list[Sequence],
) -> None:
    active_sequence = _get_active_sequence(progress, planned_lesson.subject_id)
    if active_sequence.sequence_id != planned_lesson.sequence_id:
        raise ProgressCommandError(
            "Die geplante Lesson gehört nicht zur aktiven Sequenz."
        )

    expected_lesson = get_next_lesson(
        progress,
        sequences,
        planned_lesson.subject_id,
        planned_lesson.grade_level,
    )
    if expected_lesson is None:
        raise ProgressCommandError("Die aktive Sequenz ist bereits abgeschlossen.")

    if expected_lesson.id != planned_lesson.lesson.id:
        raise ProgressCommandError(
            "Nur die nächste offene Lesson kann bearbeitet werden."
        )


def _append_entry(
    progress: ClassProgress,
    entry: TeachingLogEntry,
) -> ClassProgress:
    try:
        return ClassProgress(
            active_sequences=progress.active_sequences,
            entries=progress.entries + (entry,),
        )
    except (TypeError, ValueError) as error:
        raise ProgressCommandError(str(error)) from error


def _get_active_sequence(
    progress: ClassProgress,
    subject_id: str,
) -> ActiveSequence:
    active_sequence = next(
        (
            active
            for active in progress.active_sequences
            if active.subject_id == subject_id
        ),
        None,
    )
    if active_sequence is None:
        raise ProgressCommandError(
            f"Für das Fach '{subject_id}' ist keine Sequenz aktiv."
        )
    return active_sequence


def _get_progressed_lesson_ids(
    progress: ClassProgress,
    subject_id: str,
    sequence_id: str,
) -> set[str]:
    return {
        entry.lesson_id
        for entry in progress.entries
        if entry.subject_id == subject_id
        and entry.sequence_id == sequence_id
        and entry.action in {TeachingAction.COMPLETED, TeachingAction.SKIPPED}
        and entry.lesson_id is not None
    }
