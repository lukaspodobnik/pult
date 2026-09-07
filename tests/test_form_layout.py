import asyncio
from datetime import date

import pytest
from test_ui_integration import prepare_root

from pult.app import PultApp
from pult.progress.class_progress import load_class_progress
from pult.school.school_class import load_school_classes
from pult.school.subject import load_subjects
from pult.screens.add_closure_screen import AddClosureScreen
from pult.screens.add_extra_lesson_screen import AddExtraLessonScreen
from pult.screens.cancel_lesson_screen import CancelLessonScreen
from pult.screens.edit_timetable_entry_screen import EditTimetabelEntryScreen
from pult.screens.select_next_sequence_screen import SelectNextSequenceScreen
from pult.screens.set_active_sequence_screen import SetActiveSequenceScreen
from pult.screens.setup_school_class_screen import SchoolClassSetupScreen
from pult.widgets.form_dialog import FormDialog


@pytest.mark.parametrize("size", [(206, 46), (80, 24)])
def test_form_frames_actions_and_focus(tmp_path, monkeypatch, size):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)
    classes = load_school_classes(tmp_path, config.active_school_year)
    subjects = load_subjects(tmp_path)
    progress = load_class_progress(tmp_path, config.active_school_year, "5A")

    async def run():
        app = PultApp()
        async with app.run_test(size=size) as pilot:
            await pilot.pause()
            sequences = [
                s
                for s in app.require_sequence_library().get_sequences()
                if s.grade_level == 5 and s.subject_id == "mathematik"
            ]
            screens = [
                SchoolClassSetupScreen(),
                AddClosureScreen(classes, date(2026, 10, 1)),
                EditTimetabelEntryScreen("monday", 1, None, classes, subjects),
                CancelLessonScreen("5A"),
                AddExtraLessonScreen(classes, subjects),
                AddExtraLessonScreen(classes, subjects, "5A", "mathematik"),
                SetActiveSequenceScreen(
                    classes[0], progress, sequences, subjects, "mathematik"
                ),
                SelectNextSequenceScreen(sequences, sequences[0].id),
            ]
            for screen in screens:
                await app.push_screen(screen)
                await pilot.pause()
                dialog = screen.query_one(FormDialog)
                assert dialog.border_title
                assert dialog.region.height >= 13
                assert dialog.region.y >= 0
                assert dialog.region.bottom <= size[1]
                actions = dialog.query_one(".form-actions")
                assert actions.region.height == 1
                assert actions.region.bottom <= dialog.content_region.bottom
                buttons = list(actions.query("Button"))
                for button in buttons:
                    assert str(button.label) in button.render_line(0).text
                assert all(
                    b.region.width == 16 and b.region.height == 1 for b in buttons
                )
                assert app.focused in list(dialog.query("Input, Select, SelectionList"))
                if isinstance(screen, AddClosureScreen):
                    assert (
                        screen.query_one("#closure-start").region.y
                        == screen.query_one("#closure-end").region.y
                    )
                await pilot.press("escape")
                await pilot.pause()
                assert app.screen is not screen

    asyncio.run(run())
