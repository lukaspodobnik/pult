from dataclasses import dataclass
from datetime import date, timedelta

from schooltools_tui.curriculum.sequence import Lesson, Sequence, sequence_sort_key
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


@dataclass(frozen=True)
class SequenceProgressSummary:
    sequence_id: str
    curriculum_section_id: str
    title: str
    chapter_id: str | None
    chapter_title: str | None
    completed_lesson_count: int
    skipped_lesson_count: int
    total_lesson_count: int
    is_active: bool

    @property
    def progressed_lesson_count(self) -> int:
        return self.completed_lesson_count + self.skipped_lesson_count


@dataclass(frozen=True)
class SubjectProgressSummary:
    subject_id: str
    completed_lesson_count: int
    skipped_lesson_count: int
    total_lesson_count: int
    next_planned_lesson: PlannedLesson | None
    sequences: tuple[SequenceProgressSummary, ...]

    @property
    def progressed_lesson_count(self) -> int:
        return self.completed_lesson_count + self.skipped_lesson_count


def get_class_progress_summary(
    progress: ClassProgress,
    sequences: list[Sequence],
    timetable_entries: list[TimetableEntry],
    school_class: SchoolClass,
    school_year_start: date,
) -> tuple[SubjectProgressSummary, ...]:
    """Return the curriculum progress needed to render a class view."""
    relevant_sequences = [
        sequence
        for sequence in sequences
        if sequence.grade_level == school_class.grade_level
        and sequence.subject_id in school_class.subject_ids
    ]
    relevant_sequences.sort(key=sequence_sort_key)

    next_lessons_by_subject_id = {
        planned_lesson.subject_id: planned_lesson
        for planned_lesson in get_next_planned_lessons_for_class(
            progress,
            sequences,
            timetable_entries,
            school_class,
            school_year_start,
        )
    }
    active_sequence_ids_by_subject_id = {
        active_sequence.subject_id: active_sequence.sequence_id
        for active_sequence in progress.active_sequences
    }
    progressed_actions_by_lesson = {
        (entry.subject_id, entry.sequence_id, entry.lesson_id): entry.action
        for entry in progress.entries
        if entry.action in {TeachingAction.COMPLETED, TeachingAction.SKIPPED}
    }

    subject_summaries = []
    for subject_id in school_class.subject_ids:
        sequence_summaries = []
        for sequence in relevant_sequences:
            if sequence.subject_id != subject_id:
                continue

            completed_lesson_count = sum(
                progressed_actions_by_lesson.get(
                    (subject_id, sequence.id, lesson.id)
                )
                is TeachingAction.COMPLETED
                for lesson in sequence.lessons
            )
            skipped_lesson_count = sum(
                progressed_actions_by_lesson.get(
                    (subject_id, sequence.id, lesson.id)
                )
                is TeachingAction.SKIPPED
                for lesson in sequence.lessons
            )
            sequence_summaries.append(
                SequenceProgressSummary(
                    sequence_id=sequence.id,
                    curriculum_section_id=sequence.curriculum_section_id,
                    title=sequence.title,
                    chapter_id=sequence.chapter_id,
                    chapter_title=sequence.chapter_title,
                    completed_lesson_count=completed_lesson_count,
                    skipped_lesson_count=skipped_lesson_count,
                    total_lesson_count=len(sequence.lessons),
                    is_active=(
                        active_sequence_ids_by_subject_id.get(subject_id)
                        == sequence.id
                    ),
                )
            )

        subject_summaries.append(
            SubjectProgressSummary(
                subject_id=subject_id,
                completed_lesson_count=sum(
                    sequence.completed_lesson_count
                    for sequence in sequence_summaries
                ),
                skipped_lesson_count=sum(
                    sequence.skipped_lesson_count
                    for sequence in sequence_summaries
                ),
                total_lesson_count=sum(
                    sequence.total_lesson_count for sequence in sequence_summaries
                ),
                next_planned_lesson=next_lessons_by_subject_id.get(subject_id),
                sequences=tuple(sequence_summaries),
            )
        )

    return tuple(subject_summaries)


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


def get_suggested_next_sequence(
    progress: ClassProgress,
    sequences: list[Sequence],
    subject_id: str,
    grade_level: int,
) -> Sequence | None:
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
            and entry.action
            in {TeachingAction.COMPLETED, TeachingAction.SKIPPED}
        }
        if any(
            lesson.id not in progressed_lesson_ids
            for lesson in sequence.lessons
        ):
            available_sequences.append(sequence)

    available_sequences.sort(key=sequence_sort_key)
    return available_sequences


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
