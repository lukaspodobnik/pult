"""Titel und fachliche Einordnung einer neuen Aufgabe erfassen."""

from typing import ClassVar

from textual import on
from textual.widgets import Input, Label, Select

from pult.curriculum.material import TaskMetadata
from pult.screens.base_screen import PultModalScreen
from pult.widgets.button import Button
from pult.widgets.form_dialog import FormDialog, FormFields
from pult.widgets.scrolling import Horizontal


class CreateTaskScreen(PultModalScreen[TaskMetadata | None]):
    BINDINGS: ClassVar = [("escape", "cancel", "Abbrechen")]

    def compose(self):
        with FormDialog("Neue Aufgabe", id="create-task-dialog"):
            with FormFields(classes="form-fields"):
                yield Label("Aufgabentitel", classes="field-label")
                yield Input(
                    placeholder="Zum Beispiel: Brüche vergleichen", id="new-task-title"
                )
                yield Label(
                    "Hauptkompetenzen (durch Komma getrennt)", classes="field-label"
                )
                yield Input(
                    placeholder="Zum Beispiel: K1, K6", id="new-task-competencies"
                )
                yield Label("Höchster Anforderungsbereich", classes="field-label")
                yield Select(
                    [("I", "I"), ("II", "II"), ("III", "III")],
                    prompt="Bitte auswählen",
                    id="new-task-requirement-level",
                )
            with Horizontal(classes="form-actions"):
                yield Button("Erstellen", variant="primary", id="create-task")
                yield Button("Abbrechen", id="cancel-task")

    @on(Input.Submitted)
    @on(Button.Pressed, "#create-task")
    def submit(self):
        try:
            level = self.query_one("#new-task-requirement-level", Select).value
            if not isinstance(level, str):
                raise ValueError("Bitte einen Anforderungsbereich auswählen.")
            metadata = TaskMetadata(
                self.query_one("#new-task-title", Input).value,
                self.query_one("#new-task-competencies", Input).value.split(","),
                level,
            )
        except ValueError as error:
            self.notify(str(error), severity="warning")
            return
        self.dismiss(metadata)

    @on(Button.Pressed, "#cancel-task")
    def action_cancel(self):
        self.dismiss(None)
