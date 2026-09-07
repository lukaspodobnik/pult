import asyncio
from datetime import date

import pytest
from textual.app import App

from schooltools_tui.school.calendar import Closure, ClosureKind
from schooltools_tui.screens.confirm_closure_deletion_screen import (
    ConfirmClosureDeletionScreen,
)
from schooltools_tui.screens.confirm_undo_screen import ConfirmUndoScreen
from schooltools_tui.screens.edit_classes_screen import ConfirmClassDeletionScreen
from schooltools_tui.services.closures import ScopedClosure


@pytest.mark.parametrize("kind", ["class", "closure", "undo"])
def test_confirmation_layout_and_actions(kind):
    def make_screen():
        if kind == "class":
            return ConfirmClassDeletionScreen("9B")
        if kind == "undo":
            return ConfirmUndoScreen(
                "9B", "Informatik mit einer sehr langen Fachbezeichnung"
            )
        return ConfirmClosureDeletionScreen(
            ScopedClosure(
                Closure(
                    "Ein sehr langer Name für einen geplanten schulweiten Ausfall",
                    ClosureKind.LOCAL,
                    date(2026, 10, 1),
                    date(2026, 10, 1),
                ),
                None,
            )
        )

    class TestApp(App):
        CSS_PATH = "../src/schooltools_tui/styles/app.tcss"

    async def run():
        app = TestApp()
        async with app.run_test(size=(100, 35)) as pilot:
            results = []
            for action, expected in [
                ("escape", False),
                ("enter", False),
                ("confirm", True),
            ]:
                screen = make_screen()
                await app.push_screen(screen, results.append)
                await pilot.pause()
                dialog = screen.query_one(".confirmation-dialog")
                assert dialog.region.width == 68
                assert dialog.region.height >= 13
                assert dialog.border_title
                buttons = list(screen.query("Button"))
                for button in buttons:
                    assert str(button.label) in button.render_line(0).text
                assert [str(button.label) for button in buttons] == [
                    "Abbrechen",
                    "Bestätigen",
                ]
                assert all(button.region.height == 1 for button in buttons)
                assert [button.region.width for button in buttons] == [16, 16]
                assert app.focused is screen.query_one(".confirmation-cancel")
                message = screen.query_one(".confirmation-message")
                assert message.region.height >= 2
                assert (
                    message.region.bottom
                    < screen.query_one(".confirmation-actions").region.y
                )
                if action == "confirm":
                    await pilot.click(".confirmation-accept")
                else:
                    await pilot.press(action)
                assert results[-1] is expected

    asyncio.run(run())
