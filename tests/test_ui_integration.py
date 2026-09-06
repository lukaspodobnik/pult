import asyncio
import shutil
from pathlib import Path

import pytest
from textual.widgets import Input, OptionList, Select

from schooltools_tui.app import SchooltoolsApp
from schooltools_tui.config import AppConfig
from schooltools_tui.initialization.school_class import initialize_school_class
from schooltools_tui.initialization.school_year import initialize_school_year
from schooltools_tui.school.school_class import SchoolClass
from schooltools_tui.screens.main_screen import MainScreen
from schooltools_tui.screens.setup_school_tools_screen import SetupScreen
from schooltools_tui.screens.teaching_log_screen import TeachingLogScreen
from schooltools_tui.views.home_view import HomeView
from schooltools_tui.views.school_class_view import SchoolClassView
from schooltools_tui.widgets.navigation import ManagementPicker, ViewPicker


@pytest.mark.parametrize("scope", ["school", "class:5A"])
def test_closure_modals_create_cancel_and_delete(tmp_path, monkeypatch, scope):
    from schooltools_tui.screens.add_closure_screen import AddClosureScreen
    from schooltools_tui.screens.confirm_closure_deletion_screen import (
        ConfirmClosureDeletionScreen,
    )
    from schooltools_tui.screens.edit_closures_screen import EditClosuresScreen

    config = prepare_root(tmp_path)
    monkeypatch.setattr("schooltools_tui.app.load_app_config", lambda: config)

    async def run():
        app = SchooltoolsApp()
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
            app.screen.confirm_deletion()
            await pilot.pause()
            assert screen.query_one("#closures", OptionList).option_count == 0

    asyncio.run(run())


def prepare_root(root: Path) -> AppConfig:
    defaults = Path(__file__).parents[1] / "src" / "schooltools_tui" / "defaults"
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
    monkeypatch.setattr("schooltools_tui.app.load_app_config", lambda: None)

    async def run() -> None:
        app = SchooltoolsApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            assert isinstance(app.screen, SetupScreen)

    asyncio.run(run())


def test_existing_config_opens_home_dashboard(tmp_path, monkeypatch):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("schooltools_tui.app.load_app_config", lambda: config)

    async def run() -> None:
        app = SchooltoolsApp()
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            await pilot.pause()
            assert isinstance(app.screen, MainScreen)
            assert app.screen.query_one(HomeView)
            assert app.screen.query_one("#schedule").row_count == 8

    asyncio.run(run())


def test_highlighting_class_switches_to_class_view(tmp_path, monkeypatch):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("schooltools_tui.app.load_app_config", lambda: config)

    async def run() -> None:
        app = SchooltoolsApp()
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
    monkeypatch.setattr("schooltools_tui.app.load_app_config", lambda: config)

    async def run() -> None:
        app = SchooltoolsApp()
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            picker = app.screen.query_one(ManagementPicker)
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
    monkeypatch.setattr("schooltools_tui.app.load_app_config", lambda: config)

    async def run() -> None:
        app = SchooltoolsApp()
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
            await pilot.press("l")
            await pilot.pause()
            assert isinstance(app.screen, TeachingLogScreen)
            title = app.screen.query_one(".teaching-log-title").render().plain
            assert title.endswith("5A")
            await pilot.press("escape")
            assert isinstance(app.screen, MainScreen)

    asyncio.run(run())
