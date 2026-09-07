"""Unterrichtstermine und verfügbare Stunden im Schulkalender."""

from datetime import date, timedelta

from pult.progress.class_progress import (
    ClassProgress,
    TeachingOrigin,
)
from pult.school.calendar import (
    Closure,
    SchoolCalendar,
    is_school_day,
)
from pult.school.timetable import TimetableEntry

WEEKDAYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


def get_next_scheduled_occurrence(
    progress: ClassProgress,
    timetable_entries: list[TimetableEntry],
    school_class_id: str,
    subject_id: str,
    school_calendar: SchoolCalendar,
    local_closures: list[Closure],
) -> tuple[date, int] | None:
    """Finde den ersten unverbrauchten Unterrichtstermin bis Schuljahresende."""
    matching_entries = _get_matching_timetable_entries(
        timetable_entries,
        school_class_id,
        subject_id,
    )
    after = _get_last_scheduled_occurrence(
        progress,
        subject_id,
        school_calendar,
    )

    candidate_date = max(after[0], school_calendar.first_school_day)

    while candidate_date <= school_calendar.last_school_day:
        if not is_school_day(
            school_calendar,
            candidate_date,
            local_closures,
        ):
            candidate_date += timedelta(days=1)
            continue

        weekday = WEEKDAYS[candidate_date.weekday()]
        weekday_entries = sorted(
            (entry for entry in matching_entries if entry.weekday == weekday),
            key=lambda entry: entry.period,
        )

        for entry in weekday_entries:
            occurrence = (candidate_date, entry.period)
            if occurrence > after:
                return occurrence

        candidate_date += timedelta(days=1)

    return None


def count_available_scheduled_occurrences(
    progress: ClassProgress,
    timetable_entries: list[TimetableEntry],
    school_class_id: str,
    subject_id: str,
    school_calendar: SchoolCalendar,
    local_closures: list[Closure],
) -> int:
    """Zähle unverbrauchte, kalenderbereinigte Termine bis Schuljahresende."""
    matching_entries = _get_matching_timetable_entries(
        timetable_entries,
        school_class_id,
        subject_id,
    )
    after = _get_last_scheduled_occurrence(
        progress,
        subject_id,
        school_calendar,
    )
    candidate_date = max(after[0], school_calendar.first_school_day)
    available_count = 0

    while candidate_date <= school_calendar.last_school_day:
        if is_school_day(school_calendar, candidate_date, local_closures):
            weekday = WEEKDAYS[candidate_date.weekday()]
            available_count += sum(
                (candidate_date, entry.period) > after
                for entry in matching_entries
                if entry.weekday == weekday
            )
        candidate_date += timedelta(days=1)

    return available_count


def _get_matching_timetable_entries(
    timetable_entries: list[TimetableEntry],
    school_class_id: str,
    subject_id: str,
) -> list[TimetableEntry]:
    return [
        entry
        for entry in timetable_entries
        if entry.subject_id == subject_id and entry.school_class_id == school_class_id
    ]


def _get_last_scheduled_occurrence(
    progress: ClassProgress,
    subject_id: str,
    school_calendar: SchoolCalendar,
) -> tuple[date, int]:
    scheduled_entries = [
        entry
        for entry in progress.entries
        if entry.subject_id == subject_id and entry.origin is TeachingOrigin.SCHEDULED
    ]
    last_occurrence = max(
        scheduled_entries,
        key=lambda entry: (entry.date, entry.period),
        default=None,
    )

    if last_occurrence is None:
        return school_calendar.first_school_day, 0

    assert last_occurrence.period is not None
    return last_occurrence.date, last_occurrence.period
