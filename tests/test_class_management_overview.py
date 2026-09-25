import asyncio

from test_ui_integration import prepare_root
from textual.widgets import Static

from pult.app import PultApp
from pult.initialization.school_class import initialize_school_class
from pult.school.school_class import SchoolClass
from pult.school.timetable import TimetableEntry, get_timetable_path, save_timetable
from pult.screens.edit_classes_screen import EditClassesScreen
from pult.widgets.scrolling import OptionList


def test_class_overview_selection_counts_and_deletion(tmp_path, monkeypatch):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)
    initialize_school_class(
        tmp_path, config.active_school_year, SchoolClass("6B", 6, ["mathematik"])
    )
    save_timetable(
        get_timetable_path(tmp_path, config.active_school_year),
        [
            TimetableEntry("friday", 3, "5A", "mathematik", "202"),
            TimetableEntry("monday", 1, "5A", "mathematik", "101"),
        ],
    )

    async def run():
        app = PultApp()
        async with app.run_test(size=(180, 42)) as pilot:
            await pilot.pause()
            screen = EditClassesScreen()
            await app.push_screen(screen)
            await pilot.pause()
            listing = screen.query_one("#school-classes", OptionList)
            assert listing.option_count == 2
            first = str(listing.get_option_at_index(0).prompt)
            assert "Mathematik" in first and first.rstrip().endswith("2")
            text = screen.query_one("#class-timetable-text", Static)
            assert "101" in str(text.content) and "202" in str(text.content)
            assert str(text.content).index("Montag") < str(text.content).index(
                "Freitag"
            )
            assert screen.query_one("#class-timetable-details").region.height == 11
            app.save_screenshot("classes.svg", path=str(tmp_path))
            await pilot.press("down")
            assert "Klasse 6B" in str(text.content)
            assert "Noch kein Unterricht" in str(text.content)
            screen.refresh_classes()
            await pilot.pause()
            assert screen.selected_school_class_id == "6B"
            screen.school_class_deletion_confirmed(True)
            await pilot.pause()
            assert listing.option_count == 1
            assert "Klasse 5A" in str(text.content)
            await pilot.resize_terminal(80, 24)
            await pilot.pause()
            assert screen.query_one("#edit-classes-screen").max_scroll_x > 0
            screen.school_class_deletion_confirmed(True)
            await pilot.pause()
            assert listing.option_count == 0
            assert screen.query_one("#classes-empty").display
            assert "Noch keine Klassen" in str(text.content)
            assert screen.query_one("#delete-school-class").disabled

    asyncio.run(run())
