from datetime import date, timedelta

from schooltools_tui.curriculum.sequence import Lesson, Sequence
from schooltools_tui.progress.class_progress import (
    ClassProgress,
    TeachingAction,
    TeachingOrigin,
)
from schooltools_tui.school.timetable import TimetableEntry

WEEKDAYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


def get_next_lesson(
    progress: ClassProgress, sequences: list[Sequence], subject_id: str
) -> Lesson | None:
    active_sequence = next(
        active
        for active in progress.active_sequences
        if active.subject_id == subject_id
    )

    sequence = next(
        sequence
        for sequence in sequences
        if sequence.subject_id == subject_id
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


def get_next_scheduled_occurrence(
    progress: ClassProgress,
    timetable_entries: list[TimetableEntry],
    school_class_id: str,
    subject_id: str,
    school_year_start: date,
) -> tuple[date, int] | None:
    matching_entries = [
        entry
        for entry in timetable_entries
        if entry.subject_id == subject_id
        and entry.school_class_id == school_class_id
    ]

    scheduled_entries = [
        entry
        for entry in progress.entries
        if entry.subject_id == subject_id
        and entry.origin is TeachingOrigin.SCHEDULED
    ]

    last_occurrence = max(
        scheduled_entries,
        key=lambda entry: (entry.date, entry.period),
        default=None,
    )

    if last_occurrence is None:
        after = (school_year_start, 0)
    else:
        assert last_occurrence.period is not None
        after = (last_occurrence.date, last_occurrence.period)

    candidate_date = after[0]

    for _ in range(8):
        weekday = WEEKDAYS[candidate_date.weekday()]
        weekday_entries = sorted(
            (
                entry
                for entry in matching_entries
                if entry.weekday == weekday
            ),
            key=lambda entry: entry.period,
        )

        for entry in weekday_entries:
            occurrence = (candidate_date, entry.period)
            if occurrence > after:
                return occurrence

        candidate_date += timedelta(days=1)

    return None
