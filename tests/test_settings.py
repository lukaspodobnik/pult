import asyncio
from dataclasses import replace
from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from test_ui_integration import prepare_root
from textual.widgets import Select

from pult.app import PultApp
from pult.config import load_app_config
from pult.school.timetable import get_timetable_path
from pult.screens.confirmation_screen import ConfirmationScreen
from pult.screens.main_screen import MainScreen
from pult.screens.sequence_library_screen import SequenceLibraryScreen
from pult.screens.settings_screen import SettingsScreen
from pult.screens.setup_pult_screen import SetupScreen
from pult.services.settings import (
    get_editor_options,
    get_suggested_school_year,
    update_settings,
)


def test_settings_preserve_years_and_save_last(tmp_path, monkeypatch):
    config = prepare_root(tmp_path)
    config_path = tmp_path / "config.toml"
    monkeypatch.setattr("pult.config.app_config.APP_CONFIG_PATH", config_path)
    existing_path = get_timetable_path(tmp_path, config.active_school_year)
    original_bytes = existing_path.read_bytes()
    updated = update_settings(config, "nano", "2027-2028")
    assert updated.editor == "nano"
    assert config.editor == "true"
    assert load_app_config() == updated
    assert get_timetable_path(tmp_path, "2027-2028").is_file()
    update_settings(updated, "nvim", config.active_school_year)
    assert existing_path.read_bytes() == original_bytes
    saved = config_path.read_bytes()
    with pytest.raises(ValueError):
        update_settings(config, "nano", "2099-2100")
    assert config_path.read_bytes() == saved


def test_year_offer_uses_first_school_day(tmp_path):
    config = replace(prepare_root(tmp_path), active_school_year="2025-2026")
    assert get_suggested_school_year(config, date(2026, 9, 14)) is None
    assert get_suggested_school_year(config, date(2026, 9, 15)) == "2026-2027"
    assert (
        get_suggested_school_year(
            replace(config, active_school_year="2026-2027"), date(2026, 9, 15)
        )
        is None
    )


def test_missing_config_returns_none_without_creating_file(tmp_path, monkeypatch):
    config_path = tmp_path / "config.toml"
    monkeypatch.setattr("pult.config.app_config.APP_CONFIG_PATH", config_path)
    assert load_app_config() is None
    assert not config_path.exists()


def test_missing_editor_notifies_without_starting_process(
    tmp_path, monkeypatch, sequences
):
    config = replace(prepare_root(tmp_path), editor="missing-pult-editor")
    notify = Mock()
    screen = SimpleNamespace(app_config=config, notify=notify)
    run = Mock()
    monkeypatch.setattr(
        "pult.screens.sequence_library_screen.shutil.which", lambda _: None
    )
    monkeypatch.setattr("pult.screens.sequence_library_screen.subprocess.run", run)
    SequenceLibraryScreen.open_sequence_in_editor(
        screen, SimpleNamespace(data=sequences[0])
    )
    run.assert_not_called()
    assert "nicht installiert" in notify.call_args.args[0]
    assert notify.call_args.kwargs["severity"] == "warning"


def test_settings_screen_switches_year_without_restart(tmp_path, monkeypatch):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)
    monkeypatch.setattr(
        "pult.config.app_config.APP_CONFIG_PATH", tmp_path / "config.toml"
    )
    monkeypatch.setattr("pult.app.get_suggested_school_year", lambda *_: None)

    async def run():
        app = PultApp()
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause(0.3)
            main = app.screen
            await app.push_screen(SettingsScreen(), main.settings_changed)
            await pilot.pause()
            app.screen.query_one("#settings-editor", Select).value = "nano"
            app.screen.query_one("#settings-year", Select).value = "2027-2028"
            await pilot.click("#save-settings")
            await pilot.pause(0.3)
            assert isinstance(app.screen, MainScreen) and app.screen is not main
            assert app.require_config().active_school_year == "2027-2028"
            assert app.require_config().editor == "nano"
            assert not app.screen.school_classes_by_id

    asyncio.run(run())


def test_initial_setup_offers_editor_select(monkeypatch):
    monkeypatch.setattr("pult.app.load_app_config", lambda: None)

    async def run():
        app = PultApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            assert isinstance(app.screen, SetupScreen)
            assert app.screen.query_one("#editor", Select).value == "nvim"
            assert ("Neovim (btw)", "nvim") in get_editor_options()

    asyncio.run(run())


@pytest.mark.parametrize("confirm", [True, False])
def test_startup_year_offer(tmp_path, monkeypatch, confirm):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)
    monkeypatch.setattr(
        "pult.config.app_config.APP_CONFIG_PATH", tmp_path / "config.toml"
    )
    monkeypatch.setattr("pult.app.get_suggested_school_year", lambda *_: "2027-2028")

    async def run():
        app = PultApp()
        async with app.run_test(size=(140, 42)) as pilot:
            for _ in range(60):
                await pilot.pause(0.05)
                if (
                    isinstance(app.screen, ConfirmationScreen)
                    and app.focused is not None
                    and app.focused.id == "cancel-year-change"
                ):
                    break
            assert isinstance(app.screen, ConfirmationScreen)
            # Erst nach dem Startfokus ist das Modal bereit für Benutzereingaben.
            assert app.focused is not None
            assert app.focused.id == "cancel-year-change"
            if confirm:
                confirm_button = app.screen.query_one("#confirm-year-change")
                confirm_button.focus()
                # Textual übernimmt den Fokus erst im nächsten Eventloop-Durchlauf.
                await pilot.pause()
                assert app.focused is confirm_button
                await pilot.press("enter")
            else:
                await pilot.press("escape")
            await pilot.pause(0.3)
            assert isinstance(app.screen, MainScreen)
            assert app.require_config().active_school_year == (
                "2027-2028" if confirm else "2026-2027"
            )

    asyncio.run(run())
