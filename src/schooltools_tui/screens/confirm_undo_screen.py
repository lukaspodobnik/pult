from typing import ClassVar

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Label

from schooltools_tui.screens.base_screen import SchooltoolsModalScreen


class ConfirmUndoScreen(SchooltoolsModalScreen[bool]):
    BINDINGS: ClassVar = [("escape", "cancel", "Abbrechen")]

    def __init__(self, school_class_id: str) -> None:
        super().__init__()
        self.school_class_id = school_class_id

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-undo-dialog"):
            yield Label("Letzten Eintrag zurücknehmen", id="confirm-undo-title")
            yield Label(
                f"Der letzte Protokolleintrag der Klasse "
                f"'{self.school_class_id}' wird zurückgenommen.\n"
                "Möchtest du wirklich fortfahren?",
                id="confirm-undo-message",
            )

            with Horizontal(id="confirm-undo-actions"):
                yield Button("Abbrechen", id="cancel-undo")
                yield Button(
                    "Zurücknehmen",
                    variant="error",
                    id="confirm-undo",
                )

    @on(Button.Pressed, "#confirm-undo")
    def confirm_undo(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#cancel-undo")
    def cancel_undo(self) -> None:
        self.action_cancel()

    def action_cancel(self) -> None:
        self.dismiss(False)
