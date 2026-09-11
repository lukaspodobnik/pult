import asyncio
import shutil
from pathlib import Path

import pytest
from textual.widgets import Input, OptionList, Select

from pult.app import PultApp
from pult.config import AppConfig
from pult.initialization.school_class import initialize_school_class
from pult.initialization.school_year import initialize_school_year
from pult.school.school_class import SchoolClass
from pult.screens.main_screen import MainScreen
from pult.screens.setup_pult_screen import SetupScreen
from pult.screens.teaching_log_screen import TeachingLogScreen
from pult.views.home_view import HomeView
from pult.views.school_class_view import SchoolClassView
from pult.widgets.navigation import TeachingPicker, ViewPicker


@pytest.mark.parametrize("scope", ["school", "class:5A"])
def test_closure_modals_create_cancel_and_delete(tmp_path, monkeypatch, scope):
    from pult.screens.add_closure_screen import AddClosureScreen
    from pult.screens.confirm_closure_deletion_screen import (
        ConfirmClosureDeletionScreen,
    )
    from pult.screens.edit_closures_screen import EditClosuresScreen

    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)

    async def run():
        app = PultApp()
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            await app.push_screen(EditClosuresScreen())
            await pilot.pause()
            screen = app.screen
            screen.action_create_closure()
            await pilot.pause()
            modal = app.screen
            assert isinstance(modal, AddClosureScreen)
            assert "." in modal.query_one("#closure-start", Input).value
            modal.query_one("#closure-name", Input).value = "Wandertag"
            modal.query_one("#closure-scope", Select).value = scope
            modal.submit_closure()
            await pilot.pause()
            assert app.screen is screen
            assert screen.query_one("#closures", OptionList).option_count == 1
            screen.action_delete_closure()
            await pilot.pause()
            assert isinstance(app.screen, ConfirmClosureDeletionScreen)
            app.screen.action_cancel()
            await pilot.pause()
            assert screen.query_one("#closures", OptionList).option_count == 1
            screen.action_delete_closure()
            await pilot.pause()
            await pilot.click("#confirm-closure-deletion")
            await pilot.pause()
            assert screen.query_one("#closures", OptionList).option_count == 0

    asyncio.run(run())


def prepare_root(root: Path) -> AppConfig:
    defaults = Path(__file__).parents[1] / "src" / "pult" / "defaults"
    shutil.copy2(defaults / "subjects.toml", root / "subjects.toml")
    shutil.copy2(defaults / "periods.toml", root / "periods.toml")
    shutil.copytree(defaults / "sequences", root / "sequences")
    shutil.copytree(defaults / "calendars", root / "calendars")
    (root / "school-years").mkdir()
    initialize_school_year(root, "2026-2027")
    initialize_school_class(
        root,
        "2026-2027",
        SchoolClass("5A", 5, ["mathematik"]),
    )
    return AppConfig(root, "true", "2026-2027")


def test_missing_config_opens_setup(monkeypatch):
    monkeypatch.setattr("pult.app.load_app_config", lambda: None)

    async def run() -> None:
        app = PultApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            assert isinstance(app.screen, SetupScreen)

    asyncio.run(run())


def test_existing_config_opens_home_dashboard(tmp_path, monkeypatch):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)

    async def run() -> None:
        app = PultApp()
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            await pilot.pause()
            assert isinstance(app.screen, MainScreen)
            assert app.screen.query_one(HomeView)
            assert app.screen.query_one("#schedule").row_count == 8

    asyncio.run(run())


def test_highlighting_class_switches_to_class_view(tmp_path, monkeypatch):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)

    async def run() -> None:
        app = PultApp()
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            picker = app.screen.query_one(ViewPicker)
            picker.highlighted = 1
            # Ein leerer Event-Queue bedeutet nicht, dass der Debounce-Timer ablief.
            for _ in range(20):
                await pilot.pause(0.05)
                if app.screen.query(SchoolClassView):
                    break
            assert app.screen.query_one(SchoolClassView).school_class.id == "5A"

    asyncio.run(run())


def test_management_opens_teaching_log_with_class_picker(tmp_path, monkeypatch):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)

    async def run() -> None:
        app = PultApp()
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            picker = app.screen.query_one(TeachingPicker)
            picker.focus()
            option_ids = [
                picker.get_option_at_index(index).id
                for index in range(picker.option_count)
            ]
            picker.highlighted = option_ids.index("teaching-log")
            await pilot.press("enter")
            await pilot.pause()
            assert isinstance(app.screen, TeachingLogScreen)
            assert app.screen.query_one("#teaching-log-class-picker")

    asyncio.run(run())


def test_class_view_log_binding_preselects_current_class(tmp_path, monkeypatch):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)

    async def run() -> None:
        app = PultApp()
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app.screen.query_one(ViewPicker).highlighted = 1
            # Der Befehl ist bis zum abgeschlossenen Ansichtswechsel gesperrt.
            for _ in range(20):
                await pilot.pause(0.05)
                if (
                    app.screen.active_school_class_id == "5A"
                    and app.screen._pending_view_id is None
                ):
                    break
            await pilot.press("u")
            await pilot.pause()
            assert isinstance(app.screen, TeachingLogScreen)
            title = app.screen.query_one("#teaching-log-content").border_title
            assert title == "Unterrichtsprotokoll · 5A · Mathematik"
            picker = app.screen.query_one("#teaching-log-class-picker")
            content = app.screen.query_one("#teaching-log-content")
            picker.focus()
            await pilot.pause()
            assert picker.styles.background_tint.a == 0
            assert picker.styles.border.top[1] != content.styles.border.top[1]
            active_color = picker.styles.border.top[1]
            await pilot.press("tab")
            await pilot.pause()
            assert content.styles.border.top[1] == active_color
            assert picker.styles.border.top[1] != active_color
            await pilot.press("escape")
            assert isinstance(app.screen, MainScreen)

    asyncio.run(run())
