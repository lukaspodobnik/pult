"""Nächste Lesson und Auswahl offener Sequenzen."""

from pult.curriculum.sequence import Lesson, Sequence, sequence_sort_key
from pult.progress.class_progress import (
    ClassProgress,
    TeachingAction,
)


def get_next_lesson(
    progress: ClassProgress,
    sequences: list[Sequence],
    subject_id: str,
    grade_level: int,
) -> Lesson | None:
    """Gib die erste weder abgeschlossene noch übersprungene Lesson zurück."""
    active_sequence = next(
        active
        for active in progress.active_sequences
        if active.subject_id == subject_id
    )

    sequence = next(
        sequence
        for sequence in sequences
        if sequence.grade_level == grade_level
        and sequence.subject_id == subject_id
        and sequence.id == active_sequence.sequence_id
    )

    progressed_lesson_ids = {
        entry.lesson_id
        for entry in progress.entries
        if entry.subject_id == subject_id
        and entry.sequence_id == sequence.id
        and entry.action in {TeachingAction.COMPLETED, TeachingAction.SKIPPED}
    }

    for lesson in sequence.lessons:
        if lesson.id not in progressed_lesson_ids:
            return lesson

    return None


def get_suggested_next_sequence(
    progress: ClassProgress,
    sequences: list[Sequence],
    subject_id: str,
    grade_level: int,
) -> Sequence | None:
    """Schlage die nächste offene Sequenz gemäß Lehrplanreihenfolge vor."""
    active_sequence = next(
        active
        for active in progress.active_sequences
        if active.subject_id == subject_id
    )
    current_sequence = next(
        sequence
        for sequence in sequences
        if sequence.grade_level == grade_level
        and sequence.subject_id == subject_id
        and sequence.id == active_sequence.sequence_id
    )

    available_sequences = get_available_next_sequences(
        progress,
        sequences,
        subject_id,
        grade_level,
    )
    current_sort_key = sequence_sort_key(current_sequence)
    return next(
        (
            sequence
            for sequence in available_sequences
            if sequence_sort_key(sequence) > current_sort_key
        ),
        available_sequences[0] if available_sequences else None,
    )


def get_available_next_sequences(
    progress: ClassProgress,
    sequences: list[Sequence],
    subject_id: str,
    grade_level: int,
) -> list[Sequence]:
    """Gib alle nicht abgeschlossenen alternativen Sequenzen eines Fachs zurück."""
    active_sequence = next(
        active
        for active in progress.active_sequences
        if active.subject_id == subject_id
    )
    available_sequences = []

    for sequence in sequences:
        if (
            sequence.grade_level != grade_level
            or sequence.subject_id != subject_id
            or sequence.id == active_sequence.sequence_id
            or not sequence.lessons
        ):
            continue

        progressed_lesson_ids = {
            entry.lesson_id
            for entry in progress.entries
            if entry.subject_id == subject_id
            and entry.sequence_id == sequence.id
            and entry.action in {TeachingAction.COMPLETED, TeachingAction.SKIPPED}
        }
        if any(lesson.id not in progressed_lesson_ids for lesson in sequence.lessons):
            available_sequences.append(sequence)

    available_sequences.sort(key=sequence_sort_key)
    return available_sequences
