import asyncio

from test_ui_integration import prepare_root
from textual.widgets import DataTable

from pult.app import PultApp
from pult.initialization.school_class import initialize_school_class
from pult.school.school_class import SchoolClass
from pult.school.timetable import (
    TimetableEntry,
    get_timetable_path,
    save_timetable,
)
from pult.views.home_view import HomeView
from pult.views.school_class_view import SchoolClassView


def test_refresh_keeps_selected_class_and_updates_home(tmp_path, monkeypatch):
    config = prepare_root(tmp_path)
    initialize_school_class(
        tmp_path, config.active_school_year, SchoolClass("5B", 5, ["mathematik"])
    )
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)

    async def run():
        app = PultApp()
        async with app.run_test(size=(160, 46)) as pilot:
            await pilot.pause()
            await pilot.wait_for_scheduled_animations()
            screen = app.screen
            await screen.show_school_class_view(screen.school_classes_by_id["5A"])
            await screen.show_home_view()
            await screen.show_school_class_view(screen.school_classes_by_id["5B"])
            assert screen.query_one(SchoolClassView).school_class.id == "5B"
            entries = [TimetableEntry("monday", 1, "5A", "mathematik", "101")]
            save_timetable(
                get_timetable_path(tmp_path, config.active_school_year), entries
            )
            await screen.timetable_edit_finished(None)
            assert screen.active_school_class_id == "5B"
            assert screen.query_one(SchoolClassView).display
            assert not screen.query_one(HomeView).display
            await screen.show_home_view()
            home = screen.query_one(HomeView)
            assert home.display
            assert home.timetable_entries == entries
            assert "5A" in str(home.query_one(DataTable).get_cell("1", "monday"))

    asyncio.run(run())
