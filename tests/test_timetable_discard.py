import asyncio
from dataclasses import replace

import pytest
from test_ui_integration import prepare_root

from pult.app import PultApp
from pult.school.timetable import (
    TimetableEntry,
    get_timetable_path,
    save_timetable,
)
from pult.screens.confirmation_screen import ConfirmationScreen
from pult.screens.edit_timetable_entry_screen import (
    TimetableEditAction,
    TimetableEditResult,
)
from pult.screens.edit_timetable_screen import EditTimetableScreen


@pytest.mark.parametrize(
    "change", ["unchanged", "same", "reverted", "edited", "deleted", "added"]
)
@pytest.mark.parametrize("escape", [True, False])
def test_discard_only_asks_for_actual_changes(tmp_path, monkeypatch, change, escape):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)
    path = get_timetable_path(tmp_path, config.active_school_year)
    original = TimetableEntry("monday", 1, "5A", "mathematik", "101")
    save_timetable(path, [original])
    saved_bytes = path.read_bytes()

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
            if escape:
                await pilot.press("escape")
            else:
                await pilot.click("#cancel-timetable-edit")
            await pilot.pause()
            if change in {"edited", "deleted", "added"}:
                assert isinstance(app.screen, ConfirmationScreen)
                await pilot.press("escape")
                await pilot.pause()
                assert app.screen is screen
                assert screen.entries_by_slot != screen._initial_entries
                screen.action_cancel()
                await pilot.pause()
                await pilot.click("#confirm-discard-timetable")
                await pilot.pause()
            assert app.screen is not screen
            assert path.read_bytes() == saved_bytes

    asyncio.run(run())
