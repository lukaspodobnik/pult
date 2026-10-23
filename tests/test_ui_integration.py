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
from pult.screens.progress.teaching_log_screen import TeachingLogScreen
from pult.storage import load_toml, save_toml
from pult.widgets.navigation import TeachingPicker, ViewPicker


@pytest.mark.parametrize("scope", ["school", "class:5A"])
def test_closure_modals_create_cancel_and_delete(tmp_path, monkeypatch, scope):
    from pult.screens.management.add_closure_screen import AddClosureScreen
    from pult.screens.management.confirm_closure_deletion_screen import (
        ConfirmClosureDeletionScreen,
    )
    from pult.screens.management.edit_closures_screen import EditClosuresScreen

    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)

    async def run():
        app = PultApp()
        async with app.run_test(size=(160, 46)) as pilot:
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
    # UI scenarios need multiple classes, subjects and sequence choices, not
    # every shipped lesson. Initialization tests cover the complete library.
    examples = {
        "5/mathematik": [
            "natuerliche-zahlen",
            "addition-und-subtraktion-ganzer-zahlen",
        ],
        "6/mathematik": [
            "bruchteile-und-bruchzahlen",
            "prozentrechnung-daten-und-diagramme",
        ],
        "7/mathematik": [
            "aufstellen-und-interpretieren-von-termen",
            "umformen-von-termen",
        ],
        "9/mathematik": [
            "quadratwurzeln",
            "quadratische-funktionen-und-quadratische-gleichungen",
        ],
        "9/informatik-ntg": [
            "grundlagen-der-objektorientierten-modellierung-und-programmierung",
            "grundlagen-der-datenmodellierung-und-relationaler-datenbanksysteme",
        ],
    }
    for scope, sequence_ids in examples.items():
        for sequence_id in sequence_ids:
            relative = Path("sequences") / scope / sequence_id / "sequenz.toml"
            target = root / relative
            target.parent.mkdir(parents=True)
            metadata = load_toml(defaults / relative)
            metadata["stunden"] = metadata["stunden"][:2]
            save_toml(target, metadata)
    shutil.copytree(defaults / "calendars", root / "calendars")
    from pult.initialization.pult import _create_material_directories

    _create_material_directories(root)
    (root / "school-years").mkdir()
    initialize_school_year(root, "2026-2027")
    initialize_school_class(
        root,
        "2026-2027",
        SchoolClass("5A", 5, ["mathematik"]),
    )
    return AppConfig(root, "true", "2026-2027")


def test_management_opens_teaching_log_with_class_picker(tmp_path, monkeypatch):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)

    async def run() -> None:
        app = PultApp()
        async with app.run_test(size=(160, 46)) as pilot:
            await pilot.pause()
            await pilot.wait_for_scheduled_animations()
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
        async with app.run_test(size=(160, 46)) as pilot:
            await pilot.pause()
            await pilot.wait_for_scheduled_animations()
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
            await pilot.press("escape")
            assert isinstance(app.screen, MainScreen)

    asyncio.run(run())
