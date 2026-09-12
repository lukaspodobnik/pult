import asyncio
from unittest.mock import Mock

from test_ui_integration import prepare_root
from textual.widgets import Input

from pult.app import PultApp
from pult.screens.binding_help_screen import BindingHelpScreen, group_help_rows
from pult.screens.cancel_lesson_screen import CancelLessonScreen
from pult.widgets.navigation import ViewPicker


def test_footer_resizes_help_preserves_focus_and_hidden_keys_work(
    tmp_path, monkeypatch
):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)

    async def run():
        app = PultApp()
        async with app.run_test(size=(180, 46)) as pilot:
            await pilot.pause()
            screen = app.screen
            picker = screen.query_one(ViewPicker)
            picker.highlighted = 1
            await pilot.pause()
            for width in (180, 100, 60, 180):
                await pilot.resize_terminal(width, 46)
                await pilot.pause()
                footer = screen.query_one("PultFooter")
                keys = list(footer.query("FooterKey"))
                assert footer.query_one(".help-key").region.width > 0
                assert footer.query_one(".quit-key").region.right == width - 2
                assert keys[0].region.x == picker.region.x
                assert all(key.region.right <= width for key in keys)
                assert all(a.region.right <= b.region.x for a, b in zip(keys, keys[1:]))
            await pilot.resize_terminal(60, 46)
            await pilot.pause()
            footer = screen.query_one("PultFooter")
            assert not any(key.key == "w" for key in footer.query("FooterKey"))
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
