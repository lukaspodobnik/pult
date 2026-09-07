import asyncio
from datetime import time
from importlib.resources import files
from pathlib import Path

import pytest
from test_ui_integration import prepare_root
from textual.widgets import Input, Static

from pult.app import PultApp
from pult.school.period import load_periods
from pult.screens.about_screen import AboutScreen
from pult.screens.edit_periods_screen import EditPeriodsScreen
from pult.screens.main_screen import MainScreen
from pult.screens.settings_screen import SettingsScreen
from pult.views.home_view import HomeView


def prepare_app(tmp_path, monkeypatch):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)
    monkeypatch.setattr("pult.app.get_suggested_school_year", lambda *_: None)
    return PultApp()


def test_period_settings_save_cancel_and_refresh(tmp_path, monkeypatch):
    app = prepare_app(tmp_path, monkeypatch)
    original = load_periods(tmp_path)

    async def run():
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause(0.3)
            main = app.screen
            assert isinstance(main, MainScreen)
            await app.push_screen(SettingsScreen(), main.settings_changed)
            await pilot.pause()
            assert await pilot.click("#edit-periods")
            await pilot.pause()
            assert isinstance(app.screen, EditPeriodsScreen)
            assert len(app.screen.query(Input)) == 2 * len(original)
            app.screen.query_one("#start-1", Input).value = "07:55"
            await pilot.press("escape")
            assert load_periods(tmp_path) == original
            assert await pilot.click("#edit-periods")
            await pilot.pause()
            app.screen.query_one("#start-1", Input).value = "07:55"
            assert await pilot.click("#save-periods")
            await pilot.pause()
            updated = load_periods(tmp_path)
            assert updated[0].start == time(7, 55)
            assert [p.number for p in updated] == [p.number for p in original]
            assert updated[1:] == original[1:]
            # Der separate Dialog hat gespeichert, auch wenn Editor/Jahr abbrechen.
            await pilot.press("escape")
            for _ in range(40):
                await pilot.pause(0.05)
                if main.query_one(HomeView).periods == updated:
                    break
            assert main.query_one(HomeView).periods == updated

    asyncio.run(run())


@pytest.mark.parametrize(
    "start,end",
    [("8:00", "08:45"), ("24:00", "08:45"), ("09:00", "08:45"), ("08:00", "09:00")],
)
def test_invalid_period_times_preserve_file(tmp_path, monkeypatch, start, end):
    app = prepare_app(tmp_path, monkeypatch)
    path = tmp_path / "periods.toml"
    original = path.read_bytes()

    async def run():
        async with app.run_test(size=(140, 42)) as pilot:
            await app.push_screen(EditPeriodsScreen(load_periods(tmp_path)))
            await pilot.pause()
            app.screen.query_one("#start-1", Input).value = start
            app.screen.query_one("#end-1", Input).value = end
            assert await pilot.click("#save-periods")
            await pilot.pause()
            assert isinstance(app.screen, EditPeriodsScreen)
            assert path.read_bytes() == original

    asyncio.run(run())


def test_about_dialog_offline_text_and_scrolling(tmp_path, monkeypatch):
    app = prepare_app(tmp_path, monkeypatch)
    license_text = files("pult").joinpath("legal/GPL-3.0.txt").read_text()
    assert license_text == (Path(__file__).parents[1] / "LICENSE").read_text()

    async def run():
        async with app.run_test(size=(100, 30)) as pilot:
            await app.push_screen(SettingsScreen())
            await pilot.pause()
            app.screen.query_one("#show-about").scroll_visible(animate=False)
            await pilot.pause()
            assert await pilot.click("#show-about")
            await pilot.pause()
            assert isinstance(app.screen, AboutScreen)
            content = str(app.screen.query_one("#about-text", Static).content)
            assert "GPL-3.0-or-later" in content
            assert license_text in content
            assert "LehrplanPLUS" in content
            assert "pending" not in content.lower()
            assert "angefragt" not in content.lower()
            assert app.screen.query_one("#about-content").max_scroll_y > 0
            assert app.screen.query_one("#close-about").region.bottom <= 30
            await pilot.press("escape")
            assert isinstance(app.screen, SettingsScreen)

    asyncio.run(run())
