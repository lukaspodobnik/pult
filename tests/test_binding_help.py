import asyncio
from unittest.mock import Mock

from test_ui_integration import prepare_root
from textual.widgets import Input

from pult.app import PultApp
from pult.screens.common.binding_help_screen import BindingHelpScreen, group_help_rows
from pult.screens.progress.cancel_lesson_screen import CancelLessonScreen
from pult.widgets.navigation import ViewPicker


def test_help_groups_actions_and_preserves_modal_input_and_focus(tmp_path, monkeypatch):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)

    async def run():
        app = PultApp()
        async with app.run_test(size=(180, 46)) as pilot:
            await pilot.pause()
            await pilot.wait_for_scheduled_animations()
            screen = app.screen
            picker = screen.query_one(ViewPicker)
            picker.highlighted = 1
            for _ in range(40):
                await pilot.pause(0.05)
                if screen._pending_view_id is None:
                    break
            change = Mock()
            monkeypatch.setattr(
                screen, "action_change_active_sequence", lambda: change()
            )
            await pilot.press("w")
            change.assert_called_once()
            await pilot.press("f1")
            await pilot.pause()
            help_screen = app.screen
            assert isinstance(help_screen, BindingHelpScreen)
            labels = {key for key, _, _ in help_screen.rows}
            assert {"↑, k", "↓, j"} <= labels
            assert not {key.lower() for key in labels}.intersection(
                {"home", "end", "pgup", "pgdn", "pageup", "pagedown", "f1"}
            )
            groups = group_help_rows(help_screen.rows)
            assert list(groups) == ["Navigation", "Aktionen der Ansicht", "Allgemein"]
            assert any(key == "↑, k" for key, _, _ in groups["Navigation"])
            assert any(key == "w" for key, _, _ in groups["Aktionen der Ansicht"])
            assert any(key == "q" for key, _, _ in groups["Allgemein"])
            assert not labels.intersection({"h", "j", "k", "l"})
            assert any(
                key == "w" and description == "Sequenz wechseln" and enabled
                for key, description, enabled in help_screen.rows
            )
            await pilot.press("escape")
            assert app.screen is screen
            assert app.focused is picker
            await app.push_screen(CancelLessonScreen("5A"))
            await pilot.pause()
            modal = app.screen
            field = modal.query_one(Input)
            field.value = "Unfertige Eingabe"
            field.focus()
            await pilot.press("f1")
            await pilot.pause()
            assert isinstance(app.screen, BindingHelpScreen)
            assert not any(
                key.endswith((", h", ", j", ", k", ", l"))
                for key, _, _ in app.screen.rows
            )
            await pilot.press("f1")
            await pilot.pause()
            assert app.screen is modal
            assert app.focused is field
            assert field.value == "Unfertige Eingabe"

    asyncio.run(run())
