import asyncio
from dataclasses import replace
from datetime import date, time

import pytest
from test_ui_integration import prepare_root
from textual.widgets import Input, Select, SelectionList

from pult.app import PultApp
from pult.school.assessment import Assessment, AssessmentKind, load_assessments
from pult.school.period import load_periods
from pult.school.timetable import TimetableEntry, get_timetable_path, save_timetable
from pult.screens.edit_assessment_screen import EditAssessmentScreen
from pult.screens.edit_assessments_screen import EditAssessmentsScreen
from pult.services.assessments import (
    list_assessments,
    store_assessment,
    validate_assessment,
)
from pult.widgets.navigation import ManagementPicker


def test_numbering_and_slot_validation(tmp_path):
    config = prepare_root(tmp_path)
    entry = Assessment(
        "later",
        "mathematik",
        AssessmentKind.SCHOOL_EXAM,
        "Brüche",
        date(2026, 10, 5),
        time(8),
        20,
    )
    store_assessment(config, "5A", entry, creating=True)
    earlier = replace(entry, id="earlier", date=date(2026, 9, 21))
    store_assessment(config, "5A", earlier, creating=True)
    assert [(item.assessment.id, item.number) for item in list_assessments(config)] == [
        ("earlier", 1),
        ("later", 2),
    ]
    with pytest.raises(ValueError, match="Stundenplan"):
        validate_assessment(config, "5A", replace(entry, occupied_periods=(1,)))
    save_timetable(
        get_timetable_path(config.root, config.active_school_year),
        [TimetableEntry("monday", 1, "5A", "mathematik", "")],
    )
    validate_assessment(config, "5A", replace(entry, occupied_periods=(1,)))
    with pytest.raises(ValueError, match="Fach"):
        validate_assessment(config, "5A", replace(entry, subject_id="unknown"))
    store_assessment(config, "5A", replace(entry, group_id="earlier"), creating=False)
    assert {
        item.group_id
        for item in load_assessments(config.root, config.active_school_year, "5A")
    } == {"earlier"}
    store_assessment(
        config, "5A", replace(entry, date=date(2026, 9, 18)), creating=False
    )
    assert list_assessments(config)[0].assessment.id == "later"


@pytest.mark.parametrize("size", [(140, 42), (80, 24)])
def test_management_create_edit_delete(tmp_path, monkeypatch, size):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)
    save_timetable(
        get_timetable_path(config.root, config.active_school_year),
        [TimetableEntry("monday", 1, "5A", "mathematik", "")],
    )

    async def run():
        app = PultApp()
        async with app.run_test(size=size) as pilot:
            await pilot.pause()
            await pilot.wait_for_scheduled_animations()
            nav = app.screen.query_one(ManagementPicker)
            nav.highlighted = nav.get_option_index("edit-assessments")
            nav.focus()
            await pilot.press("enter")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, EditAssessmentsScreen)
            screen.action_create()
            await pilot.pause()
            form = app.screen
            assert isinstance(form, EditAssessmentScreen)
            assert form.query_one("#assessment-subject", Select).value == "mathematik"
            form.query_one("#assessment-start", Select).value = 2
            form.query_one("#assessment-title", Input).value = "Bruchrechnung"
            form.query_one("#assessment-date", Input).value = "05.10.2026"
            await pilot.pause()
            assert form.query_one("#save-assessment").region.bottom <= size[1]
            if size[0] > 80:
                form.query_one("#assessment-periods", SelectionList).select(1)
            else:
                form.query_one("#assessment-periods", SelectionList).deselect_all()
            form.save()
            await pilot.pause()
            assert app.screen is screen
            assert len(screen.entries) == 1
            assert (
                screen.entries[0].assessment.start == load_periods(config.root)[1].start
            )
            assert screen.entries[0].number == 1
            first_id = screen.entries[0].assessment.id
            screen.action_edit()
            await pilot.pause()
            form = app.screen
            assert form.query_one("#assessment-start", Select).value == 2
            form.query_one("#assessment-duration", Input).value = "60"
            form.save()
            await pilot.pause()
            assert screen.entries[0].assessment.id == first_id
            assert screen.entries[0].assessment.duration_minutes == 60
            assert screen.entries[0].assessment.occupied_periods == (
                (1,) if size[0] > 80 else ()
            )
            screen.action_delete()
            await pilot.pause()
            await pilot.click("#cancel-assessment-deletion")
            await pilot.pause()
            assert len(screen.entries) == 1
            screen.action_delete()
            await pilot.pause()
            await pilot.click("#confirm-assessment-deletion")
            await pilot.pause()
            assert screen.entries == []
            assert load_assessments(config.root, config.active_school_year, "5A") == []

    asyncio.run(run())


def test_selecting_start_marks_matching_lesson(tmp_path, monkeypatch):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)
    save_timetable(
        get_timetable_path(config.root, config.active_school_year),
        [
            TimetableEntry("monday", 2, "5A", "mathematik", ""),
            TimetableEntry("monday", 3, "5A", "mathematik", ""),
        ],
    )

    async def run():
        app = PultApp()
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            await pilot.wait_for_scheduled_animations()
            await app.push_screen(EditAssessmentScreen())
            await pilot.pause()
            form = app.screen
            form.query_one("#assessment-date", Input).value = "05.10.2026"
            await pilot.pause()
            listing = form.query_one("#assessment-periods", SelectionList)
            listing.select(3)
            form.query_one("#assessment-start", Select).value = 2
            await pilot.pause()
            assert set(listing.selected) == {2, 3}
            listing.deselect(2)
            form.query_one("#assessment-start", Select).value = 1
            await pilot.pause()
            assert listing.selected == [3]

    asyncio.run(run())


def test_default_start_is_selected_without_changing_start(tmp_path, monkeypatch):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)
    monkeypatch.setattr(
        "pult.screens.edit_assessment_screen.get_default_closure_date",
        lambda *_: date(2026, 10, 5),
    )
    save_timetable(
        get_timetable_path(config.root, config.active_school_year),
        [
            TimetableEntry("monday", 1, "5A", "mathematik", ""),
        ],
    )

    async def run():
        app = PultApp()
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            await pilot.wait_for_scheduled_animations()
            await app.push_screen(EditAssessmentScreen())
            await pilot.pause()
            form = app.screen
            listing = form.query_one("#assessment-periods", SelectionList)
            assert form.query_one("#assessment-start", Select).value == 1
            assert listing.selected == [1]
            listing.deselect(1)
            form.update_periods()
            assert listing.selected == []
            form.query_one("#assessment-date", Input).value = "12.10.2026"
            await pilot.pause()
            assert listing.selected == [1]

    asyncio.run(run())


def test_kind_change_sets_duration(tmp_path, monkeypatch):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)

    async def run():
        app = PultApp()
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            await pilot.wait_for_scheduled_animations()
            await app.push_screen(EditAssessmentScreen())
            await pilot.pause()
            form = app.screen
            kind = form.query_one("#assessment-kind", Select)
            duration = form.query_one("#assessment-duration", Input)
            for value, minutes in (("ex", "20"), ("akl", "30"), ("sa", "45")):
                kind.value = value
                await pilot.pause()
                assert duration.value == minutes
            duration.value = "60"
            kind.value = "jst"
            await pilot.pause()
            assert duration.value == "60"

    asyncio.run(run())
