from dataclasses import dataclass
from datetime import date, timedelta

from schooltools_tui.curriculum.sequence import Lesson, Sequence
from schooltools_tui.progress.class_progress import (
    ClassProgress,
    TeachingAction,
    TeachingOrigin,
)
from schooltools_tui.school.school_class import SchoolClass
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


@dataclass(frozen=True)
class PlannedLesson:
    school_class_id: str
    grade_level: int
    subject_id: str
    sequence_id: str
    lesson: Lesson
    date: date
    period: int


def get_next_lesson(
    progress: ClassProgress,
    sequences: list[Sequence],
    subject_id: str,
    grade_level: int,
) -> Lesson | None:
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


def get_next_planned_lessons_for_class(
    progress: ClassProgress,
    sequences: list[Sequence],
    timetable_entries: list[TimetableEntry],
    school_class: SchoolClass,
    school_year_start: date,
) -> list[PlannedLesson]:
    planned_lessons = []

    for subject_id in school_class.subject_ids:
        lesson = get_next_lesson(
            progress,
            sequences,
            subject_id,
            school_class.grade_level,
        )
        if lesson is None:
            continue

        occurrence = get_next_scheduled_occurrence(
            progress,
            timetable_entries,
            school_class.id,
            subject_id,
            school_year_start,
        )
        if occurrence is None:
            continue

        active_sequence = next(
            active_sequence
            for active_sequence in progress.active_sequences
            if active_sequence.subject_id == subject_id
        )
        occurrence_date, period = occurrence
        planned_lessons.append(
            PlannedLesson(
                school_class_id=school_class.id,
                grade_level=school_class.grade_level,
                subject_id=subject_id,
                sequence_id=active_sequence.sequence_id,
                lesson=lesson,
                date=occurrence_date,
                period=period,
            )
        )

    planned_lessons.sort(
        key=lambda planned_lesson: (
            planned_lesson.date,
            planned_lesson.period,
            planned_lesson.subject_id,
        )
    )
    return planned_lessons


def get_next_planned_lesson_for_class(
    progress: ClassProgress,
    sequences: list[Sequence],
    timetable_entries: list[TimetableEntry],
    school_class: SchoolClass,
    school_year_start: date,
) -> PlannedLesson | None:
    planned_lessons = get_next_planned_lessons_for_class(
        progress,
        sequences,
        timetable_entries,
        school_class,
        school_year_start,
    )
    return planned_lessons[0] if planned_lessons else None


def get_next_planned_lesson(
    progresses_by_class_id: dict[str, ClassProgress],
    sequences: list[Sequence],
    timetable_entries: list[TimetableEntry],
    school_classes: list[SchoolClass],
    school_year_start: date,
) -> PlannedLesson | None:
    planned_lessons = []

    for school_class in school_classes:
        planned_lesson = get_next_planned_lesson_for_class(
            progresses_by_class_id[school_class.id],
            sequences,
            timetable_entries,
            school_class,
            school_year_start,
        )
        if planned_lesson is not None:
            planned_lessons.append(planned_lesson)

    return min(
        planned_lessons,
        key=lambda planned_lesson: (
            planned_lesson.date,
            planned_lesson.period,
            planned_lesson.school_class_id,
            planned_lesson.subject_id,
        ),
        default=None,
    )
