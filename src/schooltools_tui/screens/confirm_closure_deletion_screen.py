from typing import ClassVar

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Button,
    Label,
)

from schooltools_tui.screens.base_screen import (
    SchooltoolsModalScreen,
)
from schooltools_tui.services.closures import ScopedClosure


class ConfirmClosureDeletionScreen(SchooltoolsModalScreen[bool]):
    BINDINGS: ClassVar = [("escape", "cancel", "Abbrechen")]

    def __init__(self, entry: ScopedClosure) -> None:
        super().__init__()
        self.entry = entry

    def compose(self) -> ComposeResult:
        scope = self.entry.school_class_id or "gesamte Schule"
        with Vertical(id="confirm-closure-deletion-dialog"):
            yield Label("Ausfall löschen", id="confirm-closure-deletion-title")
            yield Label(
                f"Soll '{self.entry.closure.name}' für {scope} wirklich "
                "gelöscht werden?",
                id="confirm-closure-deletion-message",
            )
            with Horizontal(id="confirm-closure-deletion-actions"):
                yield Button("Abbrechen", id="cancel-closure-deletion")
                yield Button(
                    "Löschen",
                    variant="error",
                    id="confirm-closure-deletion",
                )

    @on(Button.Pressed, "#confirm-closure-deletion")
    def confirm_deletion(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#cancel-closure-deletion")
    def cancel_deletion(self) -> None:
        self.action_cancel()

    def action_cancel(self) -> None:
        self.dismiss(False)
