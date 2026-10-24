import asyncio

import pytest
from test_ui_integration import prepare_root
from textual.widgets import Input, Label

from pult.app import PultApp
from pult.progress.class_progress import TeachingAction, load_class_progress
from pult.progress.queries.distribution import build_distribution_plan
from pult.school.timetable import TimetableEntry, get_timetable_path, save_timetable
from pult.screens.progress.continue_lesson_screen import ContinueLessonScreen
from pult.services.progress import load_planning_data
from pult.widgets.navigation import ViewPicker


@pytest.mark.parametrize("from_home", [True, False])
def test_continue_requires_reason_and_saves_only_after_confirmation(
    tmp_path, monkeypatch, from_home
):
    config = prepare_root(tmp_path)
    save_timetable(
        get_timetable_path(tmp_path, config.active_school_year),
        [TimetableEntry("monday", 1, "5A", "mathematik", "101")],
    )
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)

    async def run():
        app = PultApp()
        async with app.run_test(size=(160, 46)) as pilot:
            await pilot.pause(0.3)
            await pilot.wait_for_scheduled_animations()
            await pilot.pause()
            main = app.screen
            if not from_home:
                await main.show_school_class_view(main.school_classes_by_id["5A"])
            original = main.load_planned_lesson_context()
            assert original is not None
            main.query_one(ViewPicker).focus()
            await pilot.press("c")
            await pilot.pause()
            modal = app.screen
            assert isinstance(modal, ContinueLessonScreen)
            assert "5A" in modal.query_one(".form-context", Label).render().plain
            comment = modal.query_one(Input)
            assert app.focused is comment
            await pilot.click("#save-continue-lesson")
            assert app.screen is modal
            assert app.focused is comment
            comment.value = "   "
            await pilot.press("enter")
            assert app.screen is modal
            assert load_class_progress(tmp_path, config.active_school_year, "5A") == (
                original.progress
            )

            comment.value = "Noch nicht speichern"
            if from_home:
                await pilot.press("escape")
            else:
                await pilot.click("#cancel-continue-lesson")
            await pilot.pause()
            assert app.screen is main
            assert load_class_progress(tmp_path, config.active_school_year, "5A") == (
                original.progress
            )
            assert main.load_planned_lesson_context().planned_lesson == (
                original.planned_lesson
            )

            await pilot.press("c")
            await pilot.pause()
            modal = app.screen
            assert isinstance(modal, ContinueLessonScreen)
            modal.query_one(Input).value = "  Sicherung noch offen  "
            if from_home:
                await pilot.press("enter")
            else:
                await pilot.click("#save-continue-lesson")
            await pilot.pause()
            assert app.screen is main
            progress = load_class_progress(tmp_path, config.active_school_year, "5A")
            assert len(progress.entries) == 1
            entry = progress.entries[0]
            assert entry.action is TeachingAction.CONTINUED
            assert entry.comment == "Sicherung noch offen"
            assert entry.lesson_id == original.planned_lesson.lesson.id
            assert (entry.date, entry.period) == (
                original.planned_lesson.date,
                original.planned_lesson.period,
            )
            following = main.load_planned_lesson_context()
            assert following is not None
            assert (
                following.planned_lesson.lesson.id == original.planned_lesson.lesson.id
            )
            assert following.planned_lesson.date > original.planned_lesson.date
            rows = build_distribution_plan(
                load_planning_data(config, "5A"), "5A", "mathematik"
            )
            continued = next(
                row for row in rows if row.action is TeachingAction.CONTINUED
            )
            assert "Sicherung noch offen" in continued.notes

    asyncio.run(run())
