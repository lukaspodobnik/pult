"""Verbinde den Sequenzfortschritt mit dem nächsten Unterrichtstermin."""

from dataclasses import dataclass
from datetime import date

from schooltools_tui.curriculum.sequence import Lesson, Sequence
from schooltools_tui.progress.class_progress import (
    ClassProgress,
)
from schooltools_tui.school.calendar import (
    Closure,
    SchoolCalendar,
)
from schooltools_tui.school.school_class import SchoolClass
from schooltools_tui.school.timetable import TimetableEntry

from .lessons import get_next_lesson
from .scheduling import get_next_scheduled_occurrence


@dataclass(frozen=True)
class PlannedLesson:
    school_class_id: str
    grade_level: int
    subject_id: str
    sequence_id: str
    lesson: Lesson
    date: date
    period: int


def get_next_planned_lessons_for_class(
    progress: ClassProgress,
    sequences: list[Sequence],
    timetable_entries: list[TimetableEntry],
    school_class: SchoolClass,
    school_calendar: SchoolCalendar,
    school_closures: list[Closure],
    class_closures: list[Closure],
) -> list[PlannedLesson]:
    """Berechne für jedes Fach einer Klasse die nächste geplante Lesson."""
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
            school_calendar,
            [*school_closures, *class_closures],
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
    school_calendar: SchoolCalendar,
    school_closures: list[Closure],
    class_closures: list[Closure],
) -> PlannedLesson | None:
    """Gib die zeitlich nächste geplante Lesson einer Klasse zurück."""
    planned_lessons = get_next_planned_lessons_for_class(
        progress,
        sequences,
        timetable_entries,
        school_class,
        school_calendar,
        school_closures,
        class_closures,
    )
    return planned_lessons[0] if planned_lessons else None


def get_next_planned_lesson(
    progresses_by_class_id: dict[str, ClassProgress],
    sequences: list[Sequence],
    timetable_entries: list[TimetableEntry],
    school_classes: list[SchoolClass],
    school_calendar: SchoolCalendar,
    school_closures: list[Closure],
    class_closures_by_class_id: dict[str, list[Closure]],
) -> PlannedLesson | None:
    """Gib die global nächste geplante Lesson über alle Klassen zurück."""
    planned_lessons = []

    for school_class in school_classes:
        planned_lesson = get_next_planned_lesson_for_class(
            progresses_by_class_id[school_class.id],
            sequences,
            timetable_entries,
            school_class,
            school_calendar,
            school_closures,
            class_closures_by_class_id[school_class.id],
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
