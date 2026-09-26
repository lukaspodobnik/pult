import asyncio
from dataclasses import replace
from datetime import date, datetime, time

import pytest
from test_ui_integration import prepare_root

from pult.app import PultApp
from pult.curriculum.sequence import load_sequence_library
from pult.progress.class_progress import (
    TeachingAction,
    load_class_progress,
    save_class_progress,
    validate_class_progress,
)
from pult.progress.commands import undo_last_entry
from pult.progress.queries import (
    get_home_dashboard_summary,
)
from pult.progress.queries.assessments import PlannedAssessment, next_event
from pult.school.assessment import Assessment, AssessmentKind, save_assessments
from pult.school.calendar import load_school_calendar
from pult.school.school_class import load_school_class
from pult.school.timetable import TimetableEntry, get_timetable_path, save_timetable
from pult.screens.edit_assessments_screen import EditAssessmentsScreen
from pult.screens.teaching_log_screen import TeachingLogScreen
from pult.services.assessments import (
    complete_assessment,
    load_effective_assessments,
)
from pult.views.teaching_log_view import TeachingLogEntryBlock


def test_reservations_daily_and_external(
    empty_progress,
    sequences,
    school_class,
    school_calendar,
    periods,
    timetable_entries,
    local_closure,
):
    entry = Assessment(
        "sa-1",
        "mathematik",
        AssessmentKind.SCHOOL_EXAM,
        "Test",
        date(2026, 9, 7),
        time(8),
        60,
        (1, 2),
    )
    external = replace(
        entry, id="external", occupied_periods=(), kind=AssessmentKind.YEAR_GROUP_TEST
    )

    def summary(assessments, closures=()):
        return get_home_dashboard_summary(
            datetime(2026, 9, 7, 8),
            {"5A": empty_progress},
            sequences,
            timetable_entries,
            periods,
            [school_class],
            school_calendar,
            list(closures),
            {"5A": []},
            {"5A": assessments},
        )

    baseline = summary([])
    planned = summary([entry, external])
    assert (
        planned.class_balances[0].difference
        == baseline.class_balances[0].difference - 2
    )
    assert isinstance(
        next_event(planned.next_planned_lesson, planned.next_scheduled_assessment),
        PlannedAssessment,
    )
    assert planned.next_planned_lesson.date == date(2026, 9, 9)
    assert all(
        item.assessment.assessment.id == entry.id
        for item in planned.daily_schedule.timetable_entries
    )
    assert len(planned.daily_schedule.external_assessments) == 1
    closed = replace(local_closure, start=entry.date, end=entry.date)
    assert (
        summary([entry], [closed]).class_balances[0].difference
        == summary([], [closed]).class_balances[0].difference
    )
    completed = summary([replace(entry, completed_on=entry.date)])
    assert (
        completed.class_balances[0].difference == planned.class_balances[0].difference
    )
    assert completed.next_scheduled_assessment is None
    assert all(
        item.action is TeachingAction.ASSESSMENT_COMPLETED
        for item in completed.daily_schedule.timetable_entries
    )


def prepare_assessment(tmp_path, *, external=False):
    config = prepare_root(tmp_path)
    day = load_school_calendar(config.root, config.active_school_year).first_school_day
    weekday = ("monday", "tuesday", "wednesday", "thursday", "friday")[day.weekday()]
    save_timetable(
        get_timetable_path(config.root, config.active_school_year),
        [
            TimetableEntry(weekday, period, "5A", "mathematik", "")
            for period in (1, 2, 3)
        ],
    )
    entry = Assessment(
        "sa-1",
        "mathematik",
        AssessmentKind.SCHOOL_EXAM,
        "Bruchrechnung",
        day,
        time(8),
        60,
        () if external else (1, 2),
    )
    save_assessments(config.root, config.active_school_year, "5A", [entry])
    return config, entry


def test_completion_log_undo_and_failed_write(tmp_path, monkeypatch):
    config, entry = prepare_assessment(tmp_path)
    before = load_class_progress(config.root, config.active_school_year, "5A")
    complete_assessment(config, "5A", entry.id)
    progress = load_class_progress(config.root, config.active_school_year, "5A")
    assert progress.active_sequences == before.active_sequences
    assert len(progress.entries) == len(before.entries) + 1
    log = progress.entries[-1]
    assert log.assessment_id == entry.id and log.assessment_periods == (1, 2)
    assert log.lesson_id is None and log.sequence_id == ""
    validate_class_progress(
        progress,
        load_school_class(config.root, config.active_school_year, "5A"),
        load_sequence_library(config.root),
    )
    assert load_effective_assessments(config, "5A")[0].completed_on == entry.date
    with pytest.raises(ValueError):
        complete_assessment(config, "5A", entry.id)
    save_class_progress(
        config.root,
        config.active_school_year,
        "5A",
        undo_last_entry(progress, subject_id="mathematik"),
    )
    assert load_effective_assessments(config, "5A")[0].completed_on is None

    def fail(*args, **kwargs):
        raise OSError("test failure")

    monkeypatch.setattr("pult.storage.os.fsync", fail)
    with pytest.raises(OSError):
        complete_assessment(config, "5A", entry.id)
    assert load_class_progress(config.root, config.active_school_year, "5A") == before
    assert load_effective_assessments(config, "5A")[0].completed_on is None


@pytest.mark.parametrize("external", [False, True])
def test_ui_completion_and_reopen(tmp_path, monkeypatch, external):
    config, entry = prepare_assessment(tmp_path, external=external)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)

    async def run():
        app = PultApp()
        async with app.run_test(size=(160, 48)) as pilot:
            await pilot.pause()
            await pilot.wait_for_scheduled_animations()
            main = app.screen
            if external:
                await app.push_screen(EditAssessmentsScreen())
                await pilot.pause()
            else:
                assert isinstance(main.displayed_next_lesson(), PlannedAssessment)
            await pilot.press("n")
            await pilot.pause()
            assert load_effective_assessments(config, "5A")[0].completed_on is not None
            await app.push_screen(TeachingLogScreen("5A", subject_id="mathematik"))
            await pilot.pause()
            blocks = list(app.screen.query(TeachingLogEntryBlock))
            assert len(blocks) == 1
            assert blocks[0].entry.assessment_id == entry.id
            await pilot.press("escape")
            await pilot.pause()
            await pilot.press("p")
            await pilot.pause()
            await pilot.click(
                "#confirm-assessment-reopen" if external else "#confirm-undo"
            )
            await pilot.pause()
            assert load_effective_assessments(config, "5A")[0].completed_on is None
            assert not load_class_progress(
                config.root, config.active_school_year, "5A"
            ).entries

    asyncio.run(run())
