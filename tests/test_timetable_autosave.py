import asyncio
from dataclasses import replace

import pytest
from test_ui_integration import prepare_root

from pult.app import PultApp
from pult.school.timetable import (
    TimetableEntry,
    get_timetable_path,
    load_timetable,
    save_timetable,
)
from pult.screens.edit_timetable_entry_screen import (
    TimetableEditAction,
    TimetableEditResult,
)
from pult.screens.edit_timetable_screen import EditTimetableScreen


@pytest.mark.parametrize(
    "change", ["unchanged", "same", "reverted", "edited", "deleted", "added"]
)
@pytest.mark.parametrize("escape", [True, False])
def test_changes_persist_immediately_and_back_keeps_them(
    tmp_path, monkeypatch, change, escape
):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)
    path = get_timetable_path(tmp_path, config.active_school_year)
    original = TimetableEntry("monday", 1, "5A", "mathematik", "101")
    save_timetable(path, [original])

    async def run():
        app = PultApp()
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            screen = EditTimetableScreen()
            await app.push_screen(screen)
            await pilot.pause()
            if change != "unchanged":
                entry = replace(original, room="202")
                action = TimetableEditAction.SAVE
                if change == "same":
                    entry = replace(original)
                elif change == "deleted":
                    action = TimetableEditAction.DELETE
                elif change == "added":
                    entry = replace(original, period=2)
                screen.timetable_entry_edited(TimetableEditResult(action, entry))
                if change == "reverted":
                    screen.timetable_entry_edited(
                        TimetableEditResult(TimetableEditAction.SAVE, replace(original))
                    )
            expected = [original]
            if change == "edited":
                expected = [replace(original, room="202")]
            elif change == "deleted":
                expected = []
            elif change == "added":
                expected.append(replace(original, period=2))
            assert load_timetable(path) == expected
            if escape:
                await pilot.press("escape")
            else:
                await pilot.click("#close-timetable")
            await pilot.pause()
            assert app.screen is not screen
            assert load_timetable(path) == expected

    asyncio.run(run())


@pytest.mark.parametrize(
    "action", [TimetableEditAction.SAVE, TimetableEditAction.DELETE]
)
def test_failed_save_keeps_stored_and_displayed_entry(tmp_path, monkeypatch, action):
    from unittest.mock import Mock

    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)
    path = get_timetable_path(tmp_path, config.active_school_year)
    original = TimetableEntry("monday", 1, "5A", "mathematik", "101")
    save_timetable(path, [original])

    async def run():
        app = PultApp()
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            screen = EditTimetableScreen()
            await app.push_screen(screen)
            await pilot.pause()
            notify = Mock()
            monkeypatch.setattr(screen, "notify", notify)
            save = Mock(side_effect=OSError("Schreibfehler"))
            monkeypatch.setattr(
                "pult.screens.edit_timetable_screen.save_timetable", save
            )
            screen.timetable_entry_edited(None)
            save.assert_not_called()
            screen.timetable_entry_edited(
                TimetableEditResult(action, replace(original, room="202"))
            )
            assert screen.entries_by_slot == {("monday", 1): original}
            assert screen._last_entry is None
            assert load_timetable(path) == [original]
            notify.assert_called_once_with(
                "Stundenplan konnte nicht gespeichert werden: Schreibfehler",
                severity="error",
            )

    asyncio.run(run())
