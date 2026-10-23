import asyncio

from test_ui_integration import prepare_root
from textual.widgets import Button, DataTable, Input, Select

from pult.app import PultApp
from pult.initialization.school_class import initialize_school_class
from pult.school.school_class import SchoolClass
from pult.school.timetable import TimetableEntry
from pult.screens.management.edit_timetable_entry_screen import (
    EditTimetabelEntryScreen,
    TimetableEditAction,
    TimetableEditResult,
)
from pult.screens.management.edit_timetable_screen import EditTimetableScreen


def test_new_timetable_entry_reuses_last_accepted_values(tmp_path, monkeypatch):
    config = prepare_root(tmp_path)
    initialize_school_class(
        tmp_path,
        config.active_school_year,
        SchoolClass("9B", 9, ["mathematik", "informatik-ntg"]),
    )
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)

    async def run():
        app = PultApp()
        async with app.run_test(size=(160, 46)) as pilot:
            await pilot.pause()
            screen = EditTimetableScreen()
            await app.push_screen(screen)
            await pilot.pause()
            table = screen.query_one(DataTable)
            await pilot.press("ctrl+s")
            assert app.screen is screen
            table.move_cursor(row=0, column=0)
            await pilot.press("enter")
            await pilot.pause()
            modal = app.screen
            assert isinstance(modal, EditTimetabelEntryScreen)
            assert (
                str(modal.query_one("#save-timetable-entry", Button).label)
                == "Speichern"
            )
            modal.query_one("#school-class", Select).value = "9B"
            await pilot.pause()
            modal.query_one("#subject", Select).value = "informatik-ntg"
            modal.query_one("#room", Input).value = "101"
            await pilot.click("#save-timetable-entry")
            await pilot.pause()

            table.move_cursor(row=1, column=0)
            await pilot.press("enter")
            await pilot.pause()
            assert app.screen.query_one("#school-class", Select).value == "9B"
            assert app.screen.query_one("#subject", Select).value == "informatik-ntg"
            assert app.screen.query_one("#room", Input).value == "101"
            app.screen.query_one("#school-class", Select).value = "5A"
            app.screen.query_one("#room", Input).value = "999"
            await pilot.pause()
            await pilot.click("#cancel-timetable-entry-edit")
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            assert app.screen.query_one("#school-class", Select).value == "9B"
            assert app.screen.query_one("#subject", Select).value == "informatik-ntg"
            assert app.screen.query_one("#room", Input).value == "101"
            await pilot.click("#save-timetable-entry")
            await pilot.pause()

            # Existing slots keep their own values, regardless of the suggestion.
            screen.timetable_entry_edited(
                TimetableEditResult(
                    TimetableEditAction.SAVE,
                    TimetableEntry("monday", 3, "5A", "mathematik", "202"),
                )
            )
            table.move_cursor(row=0, column=0)
            await pilot.press("enter")
            await pilot.pause()
            assert app.screen.query_one("#school-class", Select).value == "9B"
            assert app.screen.query_one("#subject", Select).value == "informatik-ntg"
            assert app.screen.query_one("#room", Input).value == "101"

    asyncio.run(run())


def test_cell_updates_preserve_selection_and_focus(tmp_path, monkeypatch):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)

    async def run():
        app = PultApp()
        async with app.run_test(size=(160, 46)) as pilot:
            await pilot.pause()
            await app.push_screen(EditTimetableScreen())
            await pilot.pause()
            screen = app.screen
            table = screen.query_one(DataTable)
            table.move_cursor(row=2, column=1)
            cursor = table.cursor_coordinate
            for room, action in [
                ("12345678901234567890", TimetableEditAction.SAVE),
                ("1", TimetableEditAction.SAVE),
                ("1", TimetableEditAction.DELETE),
            ]:
                entry = TimetableEntry("tuesday", 3, "5A", "mathematik", room)
                screen.timetable_entry_edited(TimetableEditResult(action, entry))
                await pilot.pause()
                cell = str(table.get_cell("3", "tuesday"))
                assert ("5A · Ma" in cell) == (action is TimetableEditAction.SAVE)
                assert "--" not in str(table.get_cell("1", "monday"))
                assert table.cursor_coordinate == cursor
                assert table.has_focus
            await pilot.resize_terminal(180, 46)
            await pilot.pause()
            assert table.cursor_coordinate == cursor
            assert table.has_focus

    asyncio.run(run())
