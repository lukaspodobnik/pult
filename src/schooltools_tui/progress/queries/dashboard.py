"""Schuljahresfortschritt, Tagesplan und nächste Lesson für Home."""

from dataclasses import dataclass
from datetime import date, datetime

from schooltools_tui.curriculum.sequence import Sequence
from schooltools_tui.progress.class_progress import (
    ClassProgress,
    TeachingAction,
    TeachingLogEntry,
    TeachingOrigin,
)
from schooltools_tui.school.calendar import (
    Closure,
    SchoolCalendar,
    is_school_day,
)
from schooltools_tui.school.period import Period
from schooltools_tui.school.school_class import SchoolClass
from schooltools_tui.school.timetable import TimetableEntry

from .planning import (
    PlannedLesson,
    get_next_planned_lesson,
    get_next_planned_lessons_for_class,
)
from .scheduling import WEEKDAYS


@dataclass(frozen=True)
class SchoolYearProgressSummary:
    school_year: str
    elapsed_day_count: int
    total_day_count: int

    @property
    def percentage(self) -> int:
        if self.total_day_count == 0:
            return 100
        return round(self.elapsed_day_count / self.total_day_count * 100)


@dataclass(frozen=True)
class DailyTimetableEntry:
    timetable_entry: TimetableEntry
    grade_level: int
    log_entry: TeachingLogEntry | None
    planned_lesson: PlannedLesson | None
    is_time_highlighted: bool

    @property
    def action(self) -> TeachingAction | None:
        return self.log_entry.action if self.log_entry is not None else None


@dataclass(frozen=True)
class DailyAdditionalEntry:
    school_class_id: str
    log_entry: TeachingLogEntry


@dataclass(frozen=True)
class DailyScheduleSummary:
    date: date
    timetable_entries: tuple[DailyTimetableEntry, ...]
    additional_entries: tuple[DailyAdditionalEntry, ...]


@dataclass(frozen=True)
class HomeDashboardSummary:
    school_year_progress: SchoolYearProgressSummary
    next_planned_lesson: PlannedLesson | None
    daily_schedule: DailyScheduleSummary


def get_school_year_progress(
    school_calendar: SchoolCalendar,
    current_date: date,
) -> SchoolYearProgressSummary:
    """Berechne den vergangenen Anteil des Schuljahres aus allen Kalendertagen."""
    total_day_count = (
        school_calendar.last_school_day - school_calendar.first_school_day
    ).days + 1

    if current_date < school_calendar.first_school_day:
        elapsed_day_count = 0
    elif current_date > school_calendar.last_school_day:
        elapsed_day_count = total_day_count
    else:
        elapsed_day_count = (current_date - school_calendar.first_school_day).days + 1

    return SchoolYearProgressSummary(
        school_year=school_calendar.school_year,
        elapsed_day_count=elapsed_day_count,
        total_day_count=total_day_count,
    )


def get_daily_schedule(
    current_datetime: datetime,
    sequences: list[Sequence],
    timetable_entries: list[TimetableEntry],
    periods: list[Period],
    school_classes: list[SchoolClass],
    progresses_by_class_id: dict[str, ClassProgress],
    school_calendar: SchoolCalendar,
    school_closures: list[Closure],
    class_closures_by_class_id: dict[str, list[Closure]],
) -> DailyScheduleSummary:
    """Berechne heutige Termine samt Protokollstatus und Zeitmarkierung."""
    current_date = current_datetime.date()
    additional_entries = _get_daily_additional_entries(
        current_date,
        progresses_by_class_id,
    )

    if not is_school_day(
        school_calendar,
        current_date,
        school_closures,
    ):
        return DailyScheduleSummary(
            date=current_date,
            timetable_entries=(),
            additional_entries=additional_entries,
        )

    weekday = WEEKDAYS[current_date.weekday()]
    entries_for_today = [
        entry
        for entry in timetable_entries
        if entry.weekday == weekday
        and is_school_day(
            school_calendar,
            current_date,
            [
                *school_closures,
                *class_closures_by_class_id.get(entry.school_class_id, []),
            ],
        )
    ]
    entries_for_today.sort(
        key=lambda entry: (
            entry.period,
            entry.school_class_id,
            entry.subject_id,
        )
    )

    logged_entries_by_occurrence = {
        (school_class_id, entry.period): entry
        for school_class_id, progress in progresses_by_class_id.items()
        for entry in progress.entries
        if entry.date == current_date
        and entry.origin is TeachingOrigin.SCHEDULED
        and entry.period is not None
    }
    planned_lessons_by_occurrence = {
        (
            planned_lesson.school_class_id,
            planned_lesson.subject_id,
            planned_lesson.period,
        ): planned_lesson
        for school_class in school_classes
        for planned_lesson in get_next_planned_lessons_for_class(
            progresses_by_class_id[school_class.id],
            sequences,
            timetable_entries,
            school_class,
            school_calendar,
            school_closures,
            class_closures_by_class_id.get(school_class.id, []),
        )
        if planned_lesson.date == current_date
    }
    highlighted_occurrence = get_time_highlighted_occurrence(
        entries_for_today,
        periods,
        current_datetime,
    )
    school_classes_by_id = {
        school_class.id: school_class for school_class in school_classes
    }

    return DailyScheduleSummary(
        date=current_date,
        timetable_entries=tuple(
            DailyTimetableEntry(
                timetable_entry=entry,
                grade_level=school_classes_by_id[entry.school_class_id].grade_level,
                log_entry=logged_entries_by_occurrence.get(
                    (entry.school_class_id, entry.period)
                ),
                planned_lesson=planned_lessons_by_occurrence.get(
                    (entry.school_class_id, entry.subject_id, entry.period)
                ),
                is_time_highlighted=(
                    entry.school_class_id,
                    entry.subject_id,
                    entry.period,
                )
                == highlighted_occurrence,
            )
            for entry in entries_for_today
        ),
        additional_entries=additional_entries,
    )


def get_home_dashboard_summary(
    current_datetime: datetime,
    progresses_by_class_id: dict[str, ClassProgress],
    sequences: list[Sequence],
    timetable_entries: list[TimetableEntry],
    periods: list[Period],
    school_classes: list[SchoolClass],
    school_calendar: SchoolCalendar,
    school_closures: list[Closure],
    class_closures_by_class_id: dict[str, list[Closure]],
) -> HomeDashboardSummary:
    """Fasse Schuljahr, nächste Lesson und Tagesplan für das Dashboard zusammen."""
    return HomeDashboardSummary(
        school_year_progress=get_school_year_progress(
            school_calendar,
            current_datetime.date(),
        ),
        next_planned_lesson=get_next_planned_lesson(
            progresses_by_class_id,
            sequences,
            timetable_entries,
            school_classes,
            school_calendar,
            school_closures,
            class_closures_by_class_id,
        ),
        daily_schedule=get_daily_schedule(
            current_datetime,
            sequences,
            timetable_entries,
            periods,
            school_classes,
            progresses_by_class_id,
            school_calendar,
            school_closures,
            class_closures_by_class_id,
        ),
    )


def _get_daily_additional_entries(
    current_date: date,
    progresses_by_class_id: dict[str, ClassProgress],
) -> tuple[DailyAdditionalEntry, ...]:
    entries = [
        DailyAdditionalEntry(school_class_id, entry)
        for school_class_id, progress in progresses_by_class_id.items()
        for entry in progress.entries
        if entry.date == current_date and entry.origin is TeachingOrigin.ADDITIONAL
    ]
    entries.sort(
        key=lambda item: (
            item.school_class_id,
            item.log_entry.subject_id,
            item.log_entry.sequence_id,
        )
    )
    return tuple(entries)


def get_time_highlighted_occurrence(
    timetable_entries: list[TimetableEntry],
    periods: list[Period],
    current_datetime: datetime,
) -> tuple[str, str, int] | None:
    """Bestimme den laufenden oder zeitlich nächsten Termin des Tages."""
    periods_by_number = {period.number: period for period in periods}
    current_time = current_datetime.time()

    for entry in timetable_entries:
        period = periods_by_number.get(entry.period)
        if period is not None and period.start <= current_time < period.end:
            return entry.school_class_id, entry.subject_id, entry.period

    return next(
        (
            (entry.school_class_id, entry.subject_id, entry.period)
            for entry in timetable_entries
            if (period := periods_by_number.get(entry.period)) is not None
            and period.start > current_time
        ),
        None,
    )
