"""Titel einer neuen Aufgabe erfassen."""

from typing import ClassVar

from textual import on
from textual.widgets import Button, Input, Label

from pult.screens.base_screen import PultModalScreen
from pult.widgets.form_dialog import FormDialog, FormFields
from pult.widgets.scrolling import Horizontal


class CreateTaskScreen(PultModalScreen[str | None]):
    BINDINGS: ClassVar = [("escape", "cancel", "Abbrechen")]

    def compose(self):
        with FormDialog("Neue Aufgabe", id="create-task-dialog"):
            with FormFields(classes="form-fields"):
                yield Label("Aufgabentitel", classes="field-label")
                yield Input(
                    placeholder="Zum Beispiel: Brüche vergleichen", id="new-task-title"
                )
            with Horizontal(classes="form-actions"):
                yield Button("Erstellen", variant="primary", id="create-task")
                yield Button("Abbrechen", id="cancel-task")

    @on(Input.Submitted, "#new-task-title")
    @on(Button.Pressed, "#create-task")
    def submit(self):
        title = self.query_one(Input).value.strip()
        if not title:
            self.notify("Bitte einen Aufgabentitel eingeben.", severity="warning")
            return
        self.dismiss(title)

    @on(Button.Pressed, "#cancel-task")
    def action_cancel(self):
        self.dismiss(None)
