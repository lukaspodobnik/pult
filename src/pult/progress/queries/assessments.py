"""Gemeinsame LNW-Termine für Dashboard, Klassenansicht und Befehle."""

from collections.abc import Sequence
from dataclasses import dataclass

from pult.school.assessment import Assessment
from pult.school.calendar import Closure, SchoolCalendar, is_school_day
from pult.school.timetable import TimetableEntry

from .planning import PlannedLesson


@dataclass(frozen=True)
class PlannedAssessment:
    school_class_id: str
    assessment: Assessment
    number: int

    @property
    def label(self) -> str:
        return f"{self.number}. {self.assessment.kind.label} · {self.assessment.title}"

    @property
    def period(self) -> int:
        return min(self.assessment.occupied_periods)


def numbered_assessments(
    class_id: str, assessments: list[Assessment]
) -> list[PlannedAssessment]:
    counts: dict[tuple[str, object], int] = {}
    result = []
    for entry in sorted(assessments, key=lambda a: (a.date, a.start, a.id)):
        key = entry.subject_id, entry.kind
        counts[key] = counts.get(key, 0) + 1
        result.append(PlannedAssessment(class_id, entry, counts[key]))
    return result


def next_assessment(
    class_id: str,
    subject_id: str,
    assessments: list[Assessment],
    *,
    scheduled_only: bool = False,
    timetable: Sequence[TimetableEntry] = (),
    calendar: SchoolCalendar | None = None,
    closures: Sequence[Closure] = (),
) -> PlannedAssessment | None:
    candidates = []
    weekdays = (
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    )
    for item in numbered_assessments(class_id, assessments):
        entry = item.assessment
        if entry.subject_id != subject_id or entry.completed_on is not None:
            continue
        if scheduled_only:
            if (
                not entry.occupied_periods
                or calendar is None
                or not is_school_day(calendar, entry.date, closures)
            ):
                continue
            matching = {
                row.period
                for row in timetable
                if row.school_class_id == class_id
                and row.subject_id == subject_id
                and row.weekday == weekdays[entry.date.weekday()]
            }
            if not set(entry.occupied_periods) <= matching:
                continue
        candidates.append(item)
    return min(
        candidates,
        key=lambda item: (
            item.assessment.date,
            item.assessment.start,
            item.assessment.id,
        ),
        default=None,
    )


def next_event(
    lesson: PlannedLesson | None, assessment: PlannedAssessment | None
) -> PlannedLesson | PlannedAssessment | None:
    if assessment is None:
        return lesson
    if lesson is None or (assessment.assessment.date, assessment.period) <= (
        lesson.date,
        lesson.period,
    ):
        return assessment
    return lesson
