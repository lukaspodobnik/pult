from typing import ClassVar

from textual import on
from textual.app import ComposeResult
from textual.widgets import Button, Static

from pult.screens.base_screen import PultModalScreen
from pult.widgets.scrolling import Horizontal, Vertical


class ConfirmationScreen(PultModalScreen[bool]):
    """Einheitliche Bestätigung; Escape und der Anfangsfokus brechen sicher ab."""

    BINDINGS: ClassVar = [("escape", "cancel", "Abbrechen")]

    def __init__(
        self,
        title: str,
        message: str,
        *,
        confirm_id: str,
        cancel_id: str,
    ) -> None:
        super().__init__()
        self.dialog_title = title
        self.message = message
        self.confirm_id = confirm_id
        self.cancel_id = cancel_id

    def compose(self) -> ComposeResult:
        dialog = Vertical(classes="confirmation-dialog")
        dialog.border_title = self.dialog_title
        with dialog:
            yield Static(self.message, classes="confirmation-message", markup=False)
            with Horizontal(classes="confirmation-actions"):
                yield Button(
                    "Abbrechen", id=self.cancel_id, classes="confirmation-cancel"
                )
                yield Button(
                    "Bestätigen",
                    variant="error",
                    id=self.confirm_id,
                    classes="confirmation-accept",
                )

    def on_mount(self) -> None:
        self.query_one(".confirmation-cancel", Button).focus()

    @on(Button.Pressed, ".confirmation-accept")
    def confirm(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, ".confirmation-cancel")
    def action_cancel(self) -> None:
        self.dismiss(False)
