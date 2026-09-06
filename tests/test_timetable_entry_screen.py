import asyncio

import pytest
from textual.app import App
from textual.widgets import Select

from schooltools_tui.school.school_class import SchoolClass
from schooltools_tui.school.subject import Subject
from schooltools_tui.school.timetable import TimetableEntry
from schooltools_tui.screens.edit_timetable_entry_screen import (
    EditTimetabelEntryScreen,
    TimetableEditAction,
)


@pytest.mark.parametrize("target_class", [None, "6B", "6C"])
def test_existing_subject_is_preserved_unless_new_class_does_not_offer_it(target_class):
    subjects = [
        Subject("mathematik", "Mathematik", "Ma", [6]),
        Subject("informatik", "Informatik", "Inf", [6]),
    ]
    classes = [
        SchoolClass("6A", 6, ["mathematik", "informatik"]),
        SchoolClass("6B", 6, ["mathematik", "informatik"]),
        SchoolClass("6C", 6, ["mathematik"]),
    ]
    entry = TimetableEntry("monday", 1, "6A", "informatik", "101")
    results = []

    class TestApp(App):
        def on_mount(self):
            self.push_screen(
                EditTimetabelEntryScreen("monday", 1, entry, classes, subjects),
                results.append,
            )

    async def run():
        app = TestApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            assert screen.query_one("#subject", Select).value == "informatik"
            if target_class is not None:
                screen.query_one("#school-class", Select).value = target_class
                await pilot.pause()
            expected_subject = "mathematik" if target_class == "6C" else "informatik"
            assert screen.query_one("#subject", Select).value == expected_subject
            screen.save_timetable_entry()
            await pilot.pause()
            assert len(results) == 1
            assert results[0].action is TimetableEditAction.SAVE
            assert results[0].entry == TimetableEntry(
                "monday", 1, target_class or "6A", expected_subject, "101"
            )

    asyncio.run(run())
