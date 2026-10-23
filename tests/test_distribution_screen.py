import asyncio

from test_ui_integration import prepare_root

from pult.app import PultApp
from pult.initialization.school_class import initialize_school_class
from pult.school.school_class import SchoolClass
from pult.school.timetable import TimetableEntry, get_timetable_path, save_timetable
from pult.screens.main_screen import MainScreen
from pult.screens.progress.distribution_screen import DistributionScreen
from pult.views.distribution_view import (
    DistributionView,
)
from pult.widgets.navigation import TeachingPicker, ViewPicker


def test_class_selection_and_export_keep_the_correct_scope(tmp_path, monkeypatch):
    config = prepare_root(tmp_path)
    initialize_school_class(
        tmp_path, config.active_school_year, SchoolClass("5B", 5, ["mathematik"])
    )
    save_timetable(
        get_timetable_path(tmp_path, config.active_school_year),
        [
            TimetableEntry("monday", 1, "5A", "mathematik", "101"),
            TimetableEntry("wednesday", 1, "5B", "mathematik", "102"),
        ],
    )
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)

    exports = []

    async def fake_export(renderer, export_config, **kwargs):
        exports.append(kwargs)
        await asyncio.sleep(0.1)
        return tmp_path / "exports/test.pdf"

    monkeypatch.setattr(
        "pult.screens.progress.distribution_screen.export_distribution_plan",
        fake_export,
    )

    async def run():
        app = PultApp()
        async with app.run_test(size=(160, 46)) as pilot:
            await pilot.pause(0.3)
            await pilot.wait_for_scheduled_animations()
            await pilot.pause()
            main = app.screen
            assert isinstance(main, MainScreen)
            classes = main.query_one(ViewPicker)
            classes.highlighted = 2
            await pilot.pause(0.3)
            assert main.active_school_class_id == "5B"
            teaching = main.query_one(TeachingPicker)
            teaching.highlighted = teaching.get_option_index("distribution")
            teaching.focus()
            await pilot.press("enter")
            await pilot.pause(0.3)
            screen = app.screen
            assert isinstance(screen, DistributionScreen)
            assert screen.subject_id == "mathematik"
            picker = screen.query_one(ViewPicker)
            assert picker.highlighted == 1
            assert "5B" in str(screen.query_one("#distribution-content").border_title)
            displayed_rows = next(
                view.rows for view in screen.query(DistributionView) if view.display
            )
            await pilot.press("x")
            screen.action_export_pdf()  # Ein laufender Export wird nicht doppelt gestartet.
            picker.highlighted = 0
            await pilot.pause(0.3)
            assert len(exports) == 1
            assert exports[0]["school_class_id"] == "5B"
            assert exports[0]["rows"] == displayed_rows
            assert not screen._exporting
            assert "5A" in str(screen.query_one("#distribution-content").border_title)
            view = next(view for view in screen.query(DistributionView) if view.display)
            assert all(
                row.date.weekday() == 0 for row in view.rows if row.period is not None
            )
            await pilot.press("escape")
            assert app.screen is main

    asyncio.run(run())
