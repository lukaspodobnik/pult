"""Fortschritt und Stundenbilanz einer Klasse, gruppiert nach Fach."""

from dataclasses import dataclass

from schooltools_tui.curriculum.sequence import Sequence, sequence_sort_key
from schooltools_tui.progress.class_progress import (
    ClassProgress,
    TeachingAction,
)
from schooltools_tui.school.calendar import (
    Closure,
    SchoolCalendar,
)
from schooltools_tui.school.school_class import SchoolClass
from schooltools_tui.school.timetable import TimetableEntry

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

    @property
    def progressed_lesson_count(self) -> int:
        return self.completed_lesson_count + self.skipped_lesson_count


@dataclass(frozen=True)
class SubjectProgressSummary:
    subject_id: str
    completed_lesson_count: int
    skipped_lesson_count: int
    total_lesson_count: int
    available_period_count: int
    next_planned_lesson: PlannedLesson | None
    sequences: tuple[SequenceProgressSummary, ...]

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
                )
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
                ),
                next_planned_lesson=next_lessons_by_subject_id.get(subject_id),
                sequences=tuple(sequence_summaries),
            )
        )

    return tuple(subject_summaries)
