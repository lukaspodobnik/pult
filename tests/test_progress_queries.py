from datetime import date, datetime

from pult.progress.class_progress import (
    ClassProgress,
    TeachingAction,
    TeachingLogEntry,
    TeachingOrigin,
)
from pult.progress.commands import (
    complete_lesson,
    continue_lesson,
    skip_lesson,
)
from pult.progress.queries import (
    count_available_scheduled_occurrences,
    get_class_progress_summary,
    get_daily_schedule,
    get_home_dashboard_summary,
    get_next_lesson,
    get_next_planned_lesson,
    get_next_scheduled_occurrence,
    get_school_year_progress,
)
from pult.school.calendar import Closure, ClosureKind
from pult.school.school_class import SchoolClass
from pult.school.timetable import TimetableEntry


def test_next_lesson_ignores_continued_and_advances_past_skipped(
    empty_progress, planned_lesson, sequences
):
    continued = continue_lesson(empty_progress, planned_lesson, sequences)
    assert get_next_lesson(continued, sequences, "mathematik", 5).id == "lesson-1"

    skipped = skip_lesson(empty_progress, planned_lesson, sequences).progress
    assert get_next_lesson(skipped, sequences, "mathematik", 5).id == "lesson-2"


def test_next_occurrence_uses_both_periods_on_same_day(
    empty_progress, planned_lesson, sequences, timetable_entries, school_calendar
):
    progress = complete_lesson(empty_progress, planned_lesson, sequences).progress
    assert get_next_scheduled_occurrence(
        progress, timetable_entries, "5A", "mathematik", school_calendar, []
    ) == (date(2026, 9, 7), 2)


def test_next_occurrence_skips_holiday_and_local_closure(
    empty_progress, school_calendar, local_closure
):
    timetable = [TimetableEntry("monday", 1, "5A", "mathematik", "101")]
    assert get_next_scheduled_occurrence(
        empty_progress, timetable, "5A", "mathematik", school_calendar, []
    ) == (date(2026, 9, 7), 1)

    week_closure = Closure(
        "Erste Woche",
        ClosureKind.LOCAL,
        date(2026, 9, 7),
        date(2026, 9, 13),
    )
    # The following Monday is an official holiday, so no later occurrence exists.
    assert (
        get_next_scheduled_occurrence(
            empty_progress,
            timetable,
            "5A",
            "mathematik",
            school_calendar,
            [week_closure],
        )
        is None
    )


def test_available_occurrences_count_calendar_aware(
    empty_progress, timetable_entries, school_calendar, local_closure
):
    assert (
        count_available_scheduled_occurrences(
            empty_progress,
            timetable_entries,
            "5A",
            "mathematik",
            school_calendar,
            [local_closure],
        )
        == 3
    )


def test_subject_summary_calculates_progress_and_balance(
    empty_progress,
    planned_lesson,
    sequences,
    timetable_entries,
    school_class,
    school_calendar,
):
    progress = skip_lesson(empty_progress, planned_lesson, sequences).progress
    summary = get_class_progress_summary(
        progress,
        sequences,
        timetable_entries,
        school_class,
        school_calendar,
        [],
        [],
    )[0]
    assert summary.skipped_lesson_count == 1
    assert summary.remaining_lesson_count == 2
    assert summary.available_period_count == 4
    assert summary.lesson_balance == 2


def test_global_next_lesson_selects_earliest_class(
    empty_progress, sequences, school_calendar
):
    other_class = SchoolClass("5B", 5, ["mathematik"])
    timetable = [
        TimetableEntry("monday", 2, "5A", "mathematik", "101"),
        TimetableEntry("monday", 1, "5B", "mathematik", "102"),
    ]
    result = get_next_planned_lesson(
        {"5A": empty_progress, "5B": empty_progress},
        sequences,
        timetable,
        [SchoolClass("5A", 5, ["mathematik"]), other_class],
        school_calendar,
        [],
        {"5A": [], "5B": []},
    )
    assert result.school_class_id == "5B"
    assert result.period == 1


def test_daily_schedule_marks_completed_and_highlights_current(
    empty_progress, planned_lesson, sequences, periods, school_class, school_calendar
):
    progress = complete_lesson(empty_progress, planned_lesson, sequences).progress
    timetable = [
        TimetableEntry("monday", 1, "5A", "mathematik", "101"),
        TimetableEntry("monday", 2, "5A", "mathematik", "101"),
    ]
    summary = get_daily_schedule(
        datetime(2026, 9, 7, 8, 50),
        sequences,
        timetable,
        periods,
        [school_class],
        {"5A": progress},
        school_calendar,
        [],
        {"5A": []},
    )
    assert summary.timetable_entries[0].action is TeachingAction.COMPLETED
    assert summary.timetable_entries[1].is_time_highlighted
    assert summary.timetable_entries[1].planned_lesson.lesson.id == "lesson-2"


def test_skipped_lesson_changes_open_row_without_marking_it(
    empty_progress, planned_lesson, sequences, periods, school_class, school_calendar
):
    progress = skip_lesson(empty_progress, planned_lesson, sequences).progress
    timetable = [TimetableEntry("monday", 1, "5A", "mathematik", "101")]
    row = get_daily_schedule(
        datetime(2026, 9, 7, 7, 30),
        sequences,
        timetable,
        periods,
        [school_class],
        {"5A": progress},
        school_calendar,
        [],
        {"5A": []},
    ).timetable_entries[0]
    assert row.action is None
    assert row.planned_lesson.lesson.id == "lesson-2"


def test_class_closure_removes_only_affected_daily_entry(
    empty_progress, sequences, periods, school_calendar
):
    classes = [
        SchoolClass("5A", 5, ["mathematik"]),
        SchoolClass("5B", 5, ["mathematik"]),
    ]
    timetable = [
        TimetableEntry("monday", 1, "5A", "mathematik", "101"),
        TimetableEntry("monday", 2, "5B", "mathematik", "102"),
    ]
    closure = Closure("Ausflug", ClosureKind.LOCAL, date(2026, 9, 7), date(2026, 9, 7))
    summary = get_daily_schedule(
        datetime(2026, 9, 7, 7, 0),
        sequences,
        timetable,
        periods,
        classes,
        {"5A": empty_progress, "5B": empty_progress},
        school_calendar,
        [],
        {"5A": [closure], "5B": []},
    )
    assert [
        row.timetable_entry.school_class_id for row in summary.timetable_entries
    ] == ["5B"]


def test_additional_entries_are_listed_separately(
    empty_progress, sequences, periods, school_class, school_calendar
):
    entry = TeachingLogEntry(
        date(2026, 9, 7),
        "mathematik",
        "sequence-1",
        TeachingAction.OTHER,
        TeachingOrigin.ADDITIONAL,
        "Übung",
    )
    progress = ClassProgress(empty_progress.active_sequences, (entry,))
    summary = get_daily_schedule(
        datetime(2026, 9, 7, 10),
        sequences,
        [],
        periods,
        [school_class],
        {"5A": progress},
        school_calendar,
        [],
        {"5A": []},
    )
    assert summary.timetable_entries == ()
    assert summary.additional_entries[0].log_entry.comment == "Übung"


def test_school_year_progress_is_clamped(school_calendar):
    assert get_school_year_progress(school_calendar, date(2026, 9, 1)).percentage == 0
    assert (
        get_school_year_progress(school_calendar, date(2026, 9, 18)).percentage == 100
    )
    assert get_school_year_progress(school_calendar, date(2027, 1, 1)).percentage == 100


def test_dashboard_combines_all_queries(
    empty_progress, sequences, timetable_entries, periods, school_class, school_calendar
):
    dashboard = get_home_dashboard_summary(
        datetime(2026, 9, 7, 7, 30),
        {"5A": empty_progress},
        sequences,
        timetable_entries,
        periods,
        [school_class],
        school_calendar,
        [],
        {"5A": []},
    )
    assert dashboard.next_planned_lesson.lesson.id == "lesson-1"
    assert dashboard.daily_schedule.timetable_entries[0].is_time_highlighted
