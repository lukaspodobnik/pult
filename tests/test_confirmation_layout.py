import asyncio
from datetime import date

import pytest
from textual.app import App

from pult.school.calendar import Closure, ClosureKind
from pult.screens.management.confirm_closure_deletion_screen import (
    ConfirmClosureDeletionScreen,
)
from pult.screens.management.edit_classes_screen import ConfirmClassDeletionScreen
from pult.screens.progress.confirm_undo_screen import ConfirmUndoScreen
from pult.services.closures import ScopedClosure


@pytest.mark.parametrize("kind", ["class", "closure", "undo"])
def test_confirmation_defaults_to_cancel_and_requires_explicit_acceptance(kind):
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
        CSS_PATH = "../src/pult/styles/app.tcss"

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
                assert app.focused is screen.query_one(".confirmation-cancel")
                if action == "confirm":
                    await pilot.click(".confirmation-accept")
                else:
                    await pilot.press(action)
                assert results[-1] is expected

    asyncio.run(run())
