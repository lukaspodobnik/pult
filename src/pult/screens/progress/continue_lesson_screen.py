from typing import ClassVar

from textual import on
from textual.app import ComposeResult
from textual.widgets import Input, Label

from pult.screens.base_screen import PultModalScreen
from pult.widgets.button import Button
from pult.widgets.form_dialog import FormDialog, FormFields
from pult.widgets.scrolling import Horizontal


class ContinueLessonScreen(PultModalScreen[str | None]):
    BINDINGS: ClassVar = [("escape", "cancel", "Abbrechen")]

    def __init__(self, context_label: str) -> None:
        super().__init__()
        self.context_label = context_label

    def compose(self) -> ComposeResult:
        with FormDialog("Stunde fortsetzen", id="continue-lesson-dialog"):
            with FormFields(classes="form-fields"):
                yield Label(self.context_label, classes="form-context", markup=False)
                yield Label("Grund der Fortsetzung", classes="field-label")
                yield Input(
                    placeholder="z. B. Sicherung noch offen",
                    id="continue-lesson-comment",
                )
            with Horizontal(classes="form-actions"):
                yield Button("Abbrechen", id="cancel-continue-lesson")
                yield Button("Speichern", variant="primary", id="save-continue-lesson")

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    @on(Input.Submitted, "#continue-lesson-comment")
    @on(Button.Pressed, "#save-continue-lesson")
    def save_lesson(self) -> None:
        field = self.query_one(Input)
        comment = field.value.strip()
        if not comment:
            self.notify(
                "Bitte gib einen Grund für die Fortsetzung an.", severity="warning"
            )
            field.focus()
            return
        self.dismiss(comment)

    @on(Button.Pressed, "#cancel-continue-lesson")
    def action_cancel(self) -> None:
        self.dismiss(None)
