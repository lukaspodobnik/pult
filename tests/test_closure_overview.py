import asyncio
from datetime import date

from test_ui_integration import prepare_root
from textual.widgets import Static

from pult.app import PultApp
from pult.school.calendar import Closure, ClosureKind, save_school_closures
from pult.school.timetable import TimetableEntry, get_timetable_path, save_timetable
from pult.screens.edit_closures_screen import EditClosuresScreen
from pult.widgets.scrolling import OptionList


def test_closure_table_and_selected_details(tmp_path, monkeypatch):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)
    save_school_closures(
        tmp_path,
        config.active_school_year,
        [
            Closure(
                "Pädagogischer Tag",
                ClosureKind.LOCAL,
                date(2026, 10, 1),
                date(2026, 10, 1),
            ),
            Closure(
                "Fortbildung", ClosureKind.LOCAL, date(2026, 10, 2), date(2026, 10, 2)
            ),
        ],
    )
    save_timetable(
        get_timetable_path(tmp_path, config.active_school_year),
        [
            TimetableEntry("thursday", 1, "5A", "mathematik", "101"),
            TimetableEntry("thursday", 2, "5A", "mathematik", "101"),
            TimetableEntry("friday", 3, "5A", "mathematik", "101"),
        ],
    )

    async def run():
        app = PultApp()
        async with app.run_test(size=(180, 42)) as pilot:
            await pilot.pause()
            screen = EditClosuresScreen()
            await app.push_screen(screen)
            await pilot.pause()
            listing = screen.query_one("#closures", OptionList)
            assert listing.option_count == 2
            assert str(listing.get_option_at_index(0).prompt).rstrip().endswith("2")
            text = screen.query_one("#closure-details-text", Static)
            assert "Pädagogischer Tag" in str(text.content)
            assert "01.10.2026" in str(text.content)
            assert "Mathematik" in str(text.content)
            await pilot.press("down")
            assert "Fortbildung" in str(text.content)
            assert "02.10.2026" in str(text.content)
            assert "01.10.2026" not in str(text.content)
            app.save_screenshot("closures.svg", path=str(tmp_path))
            await pilot.resize_terminal(80, 24)
            await pilot.pause()
            assert screen.query_one("#edit-closures-screen").max_scroll_x > 0
            assert "Entfallende Stunden" in str(
                screen.query_one("#closures-headings", Static).content
            )

    asyncio.run(run())
