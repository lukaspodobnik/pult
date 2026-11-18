from typing import ClassVar

from textual import on
from textual.app import ComposeResult
from textual.widgets import Label

from pult.screens.base_screen import PultModalScreen
from pult.widgets.button import Button
from pult.widgets.form_dialog import FormDialog, FormFields
from pult.widgets.scrolling import Horizontal


class CompleteContinuedLessonScreen(PultModalScreen[bool | None]):
    """Wähle Restabschluss (True), ganzen Termin (False) oder Abbruch (None)."""

    BINDINGS: ClassVar = [("escape", "cancel", "Abbrechen")]

    def __init__(self, context_label: str, lesson_title: str) -> None:
        super().__init__()
        self.context_label = context_label
        self.lesson_title = lesson_title

    def compose(self) -> ComposeResult:
        with FormDialog(
            "Fortgesetzte Stunde abschließen", id="complete-continued-dialog", wide=True
        ):
            with FormFields(classes="form-fields"):
                yield Label(self.context_label, classes="form-context", markup=False)
                yield Label(self.lesson_title, classes="form-context", markup=False)
                yield Label(
                    "Diese Stunde wurde zuvor mit Fortsetzen gebucht.",
                    classes="form-hint",
                )
                yield Button(
                    "Abschließen und Termin buchen",
                    variant="primary",
                    id="complete-with-period",
                    classes="completion-choice",
                )
                yield Label(
                    "Das Fertigstellen hat den aktuellen Termin beansprucht.",
                    classes="form-hint",
                )
                yield Button(
                    "Nur den Rest abschließen",
                    id="complete-remainder",
                    classes="completion-choice",
                )
                yield Label(
                    "Im selben Termin mit der nächsten Planstunde weiterarbeiten. "
                    "Den Termin anschließend wie gewohnt mit n oder c buchen.",
                    classes="form-hint",
                )
            with Horizontal(classes="form-actions"):
                yield Button("Abbrechen", id="cancel-complete-continued")

    def on_mount(self) -> None:
        self.query_one("#complete-with-period", Button).focus()

    @on(Button.Pressed, "#complete-with-period")
    def complete_with_period(self) -> None:
        self.dismiss(False)

    @on(Button.Pressed, "#complete-remainder")
    def complete_remainder(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#cancel-complete-continued")
    def action_cancel(self) -> None:
        self.dismiss(None)
