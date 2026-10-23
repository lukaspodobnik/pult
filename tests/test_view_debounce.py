import asyncio
from unittest.mock import AsyncMock

from test_ui_integration import prepare_root
from textual.screen import Screen

from pult.app import PultApp
from pult.initialization.school_class import initialize_school_class
from pult.school.school_class import SchoolClass
from pult.screens.main_screen import MainScreen
from pult.views.school_class_view import SchoolClassView
from pult.widgets.navigation import ViewPicker


def test_pending_selection_blocks_commands_and_resumes_after_modal(
    tmp_path, monkeypatch
):
    config = prepare_root(tmp_path)
    initialize_school_class(
        tmp_path, config.active_school_year, SchoolClass("5B", 5, ["mathematik"])
    )
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)
    monkeypatch.setattr(MainScreen, "VIEW_DEBOUNCE_SECONDS", 0.2)

    async def run():
        app = PultApp()
        async with app.run_test(size=(160, 46)) as pilot:
            await pilot.pause()
            await pilot.wait_for_scheduled_animations()
            screen = app.screen

            async def settled():
                for _ in range(40):
                    await pilot.pause(0.05)
                    if screen._pending_view_id is None:
                        return
                raise AssertionError("Ansichtswechsel wurde nicht abgeschlossen")

            await settled()
            picker = screen.query_one(ViewPicker)
            complete = AsyncMock()
            monkeypatch.setattr(screen, "action_complete_next_lesson", complete)
            for index in range(20):
                picker.highlighted = 1 if index % 2 == 0 else 2
            await pilot.pause(0.02)
            await app.run_action("complete_next_lesson", default_namespace=screen)
            complete.assert_not_awaited()
            await settled()
            assert screen.active_school_class_id == "5B"
            assert screen.query_one(SchoolClassView).school_class.id == "5B"
            await app.run_action("complete_next_lesson", default_namespace=screen)
            complete.assert_awaited_once()
            picker.highlighted = 1
            await pilot.pause(0.02)
            await app.push_screen(Screen())
            await pilot.pause(0.3)
            assert screen.active_school_class_id == "5B"
            app.pop_screen()
            await settled()
            assert screen.active_school_class_id == "5A"

    asyncio.run(run())
