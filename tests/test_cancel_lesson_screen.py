import asyncio

import pytest
from test_ui_integration import prepare_root
from textual.widgets import Input, Label

from pult.app import PultApp
from pult.progress.class_progress import TeachingAction, load_class_progress
from pult.school.timetable import (
    TimetableEntry,
    get_timetable_path,
    save_timetable,
)
from pult.screens.cancel_lesson_screen import CancelLessonScreen


@pytest.mark.parametrize("from_home", [True, False])
def test_cancellation_shows_home_class_and_saves_same_target(
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
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause(0.3)
            main = app.screen
            for _ in range(20):
                if main._pending_view_id is None:
                    break
                await pilot.pause(0.05)
            if not from_home:
                await main.show_school_class_view(main.school_classes_by_id["5A"])
            context = main.load_planned_lesson_context()
            assert context is not None
            main.action_cancel_next_lesson()
            await pilot.pause()
            modal = app.screen
            assert isinstance(modal, CancelLessonScreen)
            if from_home:
                assert (
                    modal.query_one("#cancel-lesson-class", Label).render().plain
                    == "Klasse 5A"
                )
            else:
                assert not modal.query("#cancel-lesson-class")
            comment = modal.query_one(Input)
            assert app.focused is comment
            comment.value = "Feueralarm"
            await pilot.click("#save-cancelled-lesson")
            await pilot.pause()
            assert app.screen is main
            progress = load_class_progress(tmp_path, config.active_school_year, "5A")
            entry = progress.entries[-1]
            assert entry.action is TeachingAction.CANCELLED
            assert entry.comment == "Feueralarm"
            assert (entry.date, entry.period) == (
                context.planned_lesson.date,
                context.planned_lesson.period,
            )

    asyncio.run(run())
