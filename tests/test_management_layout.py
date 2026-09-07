import asyncio

import pytest
from test_ui_integration import prepare_root
from textual.widgets import Button

from schooltools_tui.app import SchooltoolsApp
from schooltools_tui.screens.edit_classes_screen import EditClassesScreen
from schooltools_tui.screens.edit_closures_screen import EditClosuresScreen
from schooltools_tui.screens.edit_timetable_screen import EditTimetableScreen


@pytest.mark.parametrize(
    "screen_type, selector, title",
    [
        (EditClassesScreen, "#school-classes", "KLASSEN"),
        (EditClosuresScreen, "#closures", "AUSFÄLLE"),
        (EditTimetableScreen, "#edit-schedule", "STUNDENPLAN"),
    ],
)
def test_management_layout(tmp_path, monkeypatch, screen_type, selector, title):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("schooltools_tui.app.load_app_config", lambda: config)

    async def run():
        app = SchooltoolsApp()
        async with app.run_test(size=(206, 46)) as pilot:
            await pilot.pause()
            screen = screen_type()
            await app.push_screen(screen)
            await pilot.pause()
            assert not screen.query("Header")
            footer = screen.query_one("SchooltoolsFooter")
            assert footer.query_one(".quit-key").region.right == footer.region.right
            content = screen.query_one(selector)
            assert content.border_title == title
            assert content.region.x == 2
            assert content.region.y == 1
            actions = screen.query_one(".management-actions")
            assert actions.region.height == 1
            assert actions.region.y == content.region.bottom + 1
            buttons = list(actions.query(Button))
            assert all(button.region.height == 1 for button in buttons)
            assert buttons[-1].region.right == actions.region.right
            if screen_type is EditTimetableScreen:
                content.focus()
                await pilot.pause()
                assert content.show_cursor
                assert (
                    content.get_component_styles("datatable--header").background_tint.a
                    == 0
                )
                buttons[-1].focus()
                await pilot.pause()
                assert not content.show_cursor
            if screen_type is not EditTimetableScreen:
                assert buttons[0].region.x == actions.region.x
                assert str(buttons[-1].label) == "Zurück"
                content.focus()
                await pilot.pause()
                border = content.styles.border
                assert content.styles.background_tint.a == 0
                assert content.get_component_rich_style(
                    "option-list--option-highlighted"
                ).bold
                buttons[0].focus()
                await pilot.pause()
                assert content.styles.border == border
                assert not content.get_component_rich_style(
                    "option-list--option-highlighted"
                ).bold

    asyncio.run(run())
