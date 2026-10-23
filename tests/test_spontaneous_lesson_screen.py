import asyncio

import pytest
from test_ui_integration import prepare_root
from textual.widgets import Input

from pult.app import PultApp
from pult.progress.class_progress import (
    TeachingAction,
    TeachingOrigin,
    load_class_progress,
)
from pult.school.timetable import TimetableEntry, get_timetable_path, save_timetable
from pult.screens.progress.spontaneous_lesson_screen import SpontaneousLessonScreen
from pult.widgets.navigation import ViewPicker


@pytest.mark.parametrize("from_home", [True, False])
def test_spontaneous_dialog_requires_description_and_preserves_plan(
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
            for _ in range(20):
                if main._pending_view_id is None:
                    break
                await pilot.pause(0.05)
            if not from_home:
                await main.show_school_class_view(main.school_classes_by_id["5A"])
            original = main.load_planned_lesson_context()
            assert original is not None
            main.query_one(ViewPicker).focus()
            await pilot.pause()
            assert main.check_action("record_spontaneous_lesson", ())
            await pilot.press("t")
            await pilot.pause()
            modal = app.screen
            assert isinstance(modal, SpontaneousLessonScreen)
            description = modal.query_one(Input)
            assert app.focused is description
            await pilot.click("#save-spontaneous-lesson")
            assert app.screen is modal
            assert not load_class_progress(
                tmp_path, config.active_school_year, "5A"
            ).entries
            await pilot.pause(0.4)  # Die erste Button-Aktivierung ist abgeklungen.
            description.value = "  Übung vor der Schulaufgabe  "
            await pilot.click("#save-spontaneous-lesson")
            await pilot.pause()
            assert app.screen is main
            entry = load_class_progress(
                tmp_path, config.active_school_year, "5A"
            ).entries[-1]
            assert (
                entry.action is TeachingAction.OTHER
                and entry.origin is TeachingOrigin.SCHEDULED
            )
            assert (
                entry.comment == "Übung vor der Schulaufgabe"
                and entry.lesson_id is None
            )
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
            await pilot.press("t")
            assert isinstance(app.screen, SpontaneousLessonScreen)
            await pilot.press("escape")
            assert (
                len(
                    load_class_progress(
                        tmp_path, config.active_school_year, "5A"
                    ).entries
                )
                == 1
            )

    asyncio.run(run())
