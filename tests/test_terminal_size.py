import asyncio

import pytest
from textual.screen import ModalScreen
from textual.widgets import Input

from pult.app import PultApp
from pult.widgets.terminal_size_notice import TerminalSizeNotice


@pytest.mark.parametrize("size", [(159, 45), (160, 44), (80, 24), (160, 45)])
def test_startup_explains_minimum_terminal_size(monkeypatch, size):
    monkeypatch.setattr("pult.app.load_app_config", lambda: None)

    async def run():
        app = PultApp()
        async with app.run_test(size=size) as pilot:
            await pilot.pause()
            notices = list(app.screen.query(TerminalSizeNotice))
            if size == (160, 45):
                assert not notices
            else:
                assert len(notices) == 1
                notice = notices[0]
                assert "160 × 45" in str(notice.content)
                assert f"{size[0]} × {size[1]}" in str(notice.content)
                assert app.screen.get_widget_at(size[0] // 2, size[1] // 2)[0] is notice
                screen = app.screen
                await pilot.press("f1", "escape", "enter")
                assert app.screen is screen

    asyncio.run(run())


def test_resize_blocks_input_and_restores_the_open_dialog(monkeypatch):
    monkeypatch.setattr("pult.app.load_app_config", lambda: None)

    class DraftScreen(ModalScreen):
        def compose(self):
            yield Input("Unfertige Eingabe", id="draft")

    async def run():
        app = PultApp()
        async with app.run_test(size=(160, 45)) as pilot:
            await app.push_screen(DraftScreen())
            await pilot.pause()
            screen = app.screen
            field = screen.query_one(Input)
            field.focus()
            field.cursor_position = 5
            stack = app.screen_stack
            await pilot.resize_terminal(159, 45)
            await pilot.pause()
            assert screen.query_one(TerminalSizeNotice).display
            await pilot.press("x", "backspace", "escape", "f1")
            assert field.value == "Unfertige Eingabe"
            assert field.cursor_position == 5
            assert app.screen_stack == stack
            # Even a screen opened by a delayed callback is covered.
            await app.push_screen(DraftScreen())
            await pilot.pause()
            assert app.screen.query_one(TerminalSizeNotice).display
            app.pop_screen()
            await pilot.resize_terminal(160, 45)
            await pilot.pause()
            assert not screen.query_one(TerminalSizeNotice).display
            assert app.screen is screen
            assert app.focused is field
            assert field.value == "Unfertige Eingabe"
            assert field.cursor_position == 5
            await pilot.press("x")
            assert field.value == "Unferxtige Eingabe"

    asyncio.run(run())


def test_small_terminal_can_be_quit(monkeypatch):
    monkeypatch.setattr("pult.app.load_app_config", lambda: None)

    async def run():
        app = PultApp()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            await pilot.press("q")
            assert app._exit

    asyncio.run(run())
