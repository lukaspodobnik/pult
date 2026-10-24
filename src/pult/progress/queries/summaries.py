"""Fortschritt und Stundenbilanz einer Klasse, gruppiert nach Fach."""

from collections import Counter
from dataclasses import dataclass

from pult.curriculum.sequence import Sequence, sequence_sort_key
from pult.progress.class_progress import (
    ClassProgress,
    TeachingAction,
    TeachingLogEntry,
)
from pult.school.assessment import Assessment
from pult.school.calendar import (
    Closure,
    SchoolCalendar,
)
from pult.school.school_class import SchoolClass
from pult.school.timetable import TimetableEntry

from .assessments import PlannedAssessment, next_assessment, numbered_assessments
from .planning import PlannedLesson, get_next_planned_lessons_for_class
from .scheduling import count_available_scheduled_occurrences


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
    held_lesson_count: int = 0

    @property
    def progressed_lesson_count(self) -> int:
        return self.completed_lesson_count + self.skipped_lesson_count


@dataclass(frozen=True)
class LastTeachingEntry:
    entry: TeachingLogEntry
    title: str
    sequence_label: str


@dataclass(frozen=True)
class SubjectProgressSummary:
    subject_id: str
    completed_lesson_count: int
    skipped_lesson_count: int
    total_lesson_count: int
    available_period_count: int
    next_planned_lesson: PlannedLesson | None
    sequences: tuple[SequenceProgressSummary, ...]
    next_scheduled_assessment: PlannedAssessment | None = None
    next_assessment: PlannedAssessment | None = None
    has_assessments: bool = False
    last_entry: LastTeachingEntry | None = None

    @property
    def progressed_lesson_count(self) -> int:
        return self.completed_lesson_count + self.skipped_lesson_count

    @property
    def remaining_lesson_count(self) -> int:
        return self.total_lesson_count - self.progressed_lesson_count

    @property
    def lesson_balance(self) -> int:
        return self.available_period_count - self.remaining_lesson_count


def get_class_progress_summary(
    progress: ClassProgress,
    sequences: list[Sequence],
    timetable_entries: list[TimetableEntry],
    school_class: SchoolClass,
    school_calendar: SchoolCalendar,
    school_closures: list[Closure],
    class_closures: list[Closure],
    assessments: list[Assessment] | None = None,
) -> tuple[SubjectProgressSummary, ...]:
    """Berechne Fortschritt, Stundenbilanz und nächste Lesson pro Fach."""
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
            school_calendar,
            school_closures,
            class_closures,
            assessments,
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
    held_lessons = Counter(
        (entry.subject_id, entry.sequence_id)
        for entry in progress.entries
        if entry.action
        in {TeachingAction.COMPLETED, TeachingAction.CONTINUED, TeachingAction.OTHER}
    )
    assessment_labels = {
        item.assessment.id: item.label
        for item in numbered_assessments(school_class.id, assessments or [])
    }

    subject_summaries = []
    for subject_id in school_class.subject_ids:
        sequence_summaries = []
        for sequence in relevant_sequences:
            if sequence.subject_id != subject_id:
                continue

            completed_lesson_count = sum(
                progressed_actions_by_lesson.get((subject_id, sequence.id, lesson.id))
                is TeachingAction.COMPLETED
                for lesson in sequence.lessons
            )
            skipped_lesson_count = sum(
                progressed_actions_by_lesson.get((subject_id, sequence.id, lesson.id))
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
                        active_sequence_ids_by_subject_id.get(subject_id) == sequence.id
                    ),
                    held_lesson_count=held_lessons[subject_id, sequence.id],
                )
            )

        # Same order as the log: date, period, then insertion order. Looking
        # backwards also makes the latest insertion win equal-date ties.
        last_entry = max(
            (e for e in reversed(progress.entries) if e.subject_id == subject_id),
            key=lambda e: (e.date, e.period if e.period is not None else 99),
            default=None,
        )
        last = None
        if last_entry is not None:
            sequence = next(
                (
                    s
                    for s in relevant_sequences
                    if s.subject_id == subject_id and s.id == last_entry.sequence_id
                ),
                None,
            )
            lesson = (
                next(
                    (
                        lesson
                        for lesson in sequence.lessons
                        if lesson.id == last_entry.lesson_id
                    ),
                    None,
                )
                if sequence is not None
                else None
            )
            last = LastTeachingEntry(
                entry=last_entry,
                title=(
                    lesson.title
                    if lesson is not None
                    else assessment_labels.get(last_entry.assessment_id or "", "")
                ),
                sequence_label=(
                    f"{sequence.curriculum_section_id} · {sequence.title}"
                    if sequence is not None
                    else ""
                ),
            )

        subject_summaries.append(
            SubjectProgressSummary(
                subject_id=subject_id,
                completed_lesson_count=sum(
                    sequence.completed_lesson_count for sequence in sequence_summaries
                ),
                skipped_lesson_count=sum(
                    sequence.skipped_lesson_count for sequence in sequence_summaries
                ),
                total_lesson_count=sum(
                    sequence.total_lesson_count for sequence in sequence_summaries
                ),
                available_period_count=count_available_scheduled_occurrences(
                    progress,
                    timetable_entries,
                    school_class.id,
                    subject_id,
                    school_calendar,
                    [*school_closures, *class_closures],
                    assessments or [],
                ),
                next_planned_lesson=next_lessons_by_subject_id.get(subject_id),
                sequences=tuple(sequence_summaries),
                last_entry=last,
                has_assessments=any(
                    item.subject_id == subject_id for item in assessments or []
                ),
                next_assessment=next_assessment(
                    school_class.id, subject_id, assessments or []
                ),
                next_scheduled_assessment=next_assessment(
                    school_class.id,
                    subject_id,
                    assessments or [],
                    scheduled_only=True,
                    timetable=timetable_entries,
                    calendar=school_calendar,
                    closures=[*school_closures, *class_closures],
                ),
            )
        )

    return tuple(subject_summaries)
