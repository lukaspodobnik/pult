from typing import ClassVar

from textual import on
from textual.app import ComposeResult
from textual.widgets import Input, Label

from pult.screens.base_screen import PultModalScreen
from pult.widgets.button import Button
from pult.widgets.form_dialog import FormDialog, FormFields
from pult.widgets.scrolling import Horizontal


class SpontaneousLessonScreen(PultModalScreen[str | None]):
    BINDINGS: ClassVar = [("escape", "cancel", "Abbrechen")]

    def __init__(self, context_label: str) -> None:
        super().__init__()
        self.context_label = context_label

    def compose(self) -> ComposeResult:
        with FormDialog("Spontanunterricht", id="spontaneous-lesson-dialog"):
            with FormFields(classes="form-fields"):
                yield Label(self.context_label, classes="form-context", markup=False)
                yield Label("Beschreibung", classes="field-label")
                yield Input(
                    placeholder="z. B. Übung vor der Schulaufgabe",
                    id="spontaneous-lesson-description",
                )
            with Horizontal(classes="form-actions"):
                yield Button("Abbrechen", id="cancel-spontaneous-lesson")
                yield Button(
                    "Speichern", variant="primary", id="save-spontaneous-lesson"
                )

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    @on(Button.Pressed, "#save-spontaneous-lesson")
    def save_lesson(self) -> None:
        description = self.query_one(Input).value.strip()
        if not description:
            self.notify("Bitte beschreibe den Spontanunterricht.", severity="warning")
            return
        self.dismiss(description)

    @on(Button.Pressed, "#cancel-spontaneous-lesson")
    def action_cancel(self) -> None:
        self.dismiss(None)
