from dataclasses import dataclass
from datetime import date, datetime, timedelta

from schooltools_tui.curriculum.sequence import Lesson, Sequence, sequence_sort_key
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
from schooltools_tui.school.school_class import SchoolClass
from schooltools_tui.school.period import Period
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
class SchoolYearProgressSummary:
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
    """Return elapsed calendar days, including weekends and closures."""
    total_day_count = (
        school_calendar.last_school_day
        - school_calendar.first_school_day
    ).days + 1

    if current_date < school_calendar.first_school_day:
        elapsed_day_count = 0
    elif current_date > school_calendar.last_school_day:
        elapsed_day_count = total_day_count
    else:
        elapsed_day_count = (
            current_date - school_calendar.first_school_day
        ).days + 1

    return SchoolYearProgressSummary(
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
    """Return today's timetable with log state and a time-based highlight."""
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
    highlighted_occurrence = _get_time_highlighted_occurrence(
        entries_for_today,
        periods,
        current_datetime,
    )

    return DailyScheduleSummary(
        date=current_date,
        timetable_entries=tuple(
            DailyTimetableEntry(
                timetable_entry=entry,
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
    """Return all backend data required by the home dashboard."""
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
        if entry.date == current_date
        and entry.origin is TeachingOrigin.ADDITIONAL
    ]
    entries.sort(
        key=lambda item: (
            item.school_class_id,
            item.log_entry.subject_id,
            item.log_entry.sequence_id,
        )
    )
    return tuple(entries)


def _get_time_highlighted_occurrence(
    timetable_entries: list[TimetableEntry],
    periods: list[Period],
    current_datetime: datetime,
) -> tuple[str, str, int] | None:
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
    school_calendar: SchoolCalendar,
    local_closures: list[Closure],
) -> tuple[date, int] | None:
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


def count_available_scheduled_occurrences(
    progress: ClassProgress,
    timetable_entries: list[TimetableEntry],
    school_class_id: str,
    subject_id: str,
    school_calendar: SchoolCalendar,
    local_closures: list[Closure],
) -> int:
    """Count unprocessed timetable occurrences through the end of the year."""
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
        if entry.subject_id == subject_id
        and entry.school_class_id == school_class_id
    ]


def _get_last_scheduled_occurrence(
    progress: ClassProgress,
    subject_id: str,
    school_calendar: SchoolCalendar,
) -> tuple[date, int]:
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
        return school_calendar.first_school_day, 0

    assert last_occurrence.period is not None
    return last_occurrence.date, last_occurrence.period


def get_next_planned_lessons_for_class(
    progress: ClassProgress,
    sequences: list[Sequence],
    timetable_entries: list[TimetableEntry],
    school_class: SchoolClass,
    school_calendar: SchoolCalendar,
    school_closures: list[Closure],
    class_closures: list[Closure],
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
