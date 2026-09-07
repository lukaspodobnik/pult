from typing import ClassVar

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Input, Label

from schooltools_tui.screens.base_screen import SchooltoolsModalScreen


class CancelLessonScreen(SchooltoolsModalScreen[str | None]):
    BINDINGS: ClassVar = [("escape", "cancel", "Abbrechen")]

    def __init__(self, school_class_id: str | None = None) -> None:
        super().__init__()
        self.school_class_id = school_class_id

    def compose(self) -> ComposeResult:
        with Vertical(id="cancel-lesson-dialog"):
            yield Label("Spontanen Ausfall eintragen", id="cancel-lesson-title")
            if self.school_class_id is not None:
                yield Label(f"Klasse: {self.school_class_id}", id="cancel-lesson-class")
            yield Label("Grund", classes="field-label")
            yield Input(
                placeholder="z. B. Feueralarm",
                id="cancel-lesson-comment",
            )

            with Horizontal(id="cancel-lesson-actions"):
                yield Button("Abbrechen", id="abort-cancel-lesson")
                yield Button(
                    "Speichern",
                    variant="primary",
                    id="save-cancelled-lesson",
                )

    def on_mount(self) -> None:
        self.query_one("#cancel-lesson-comment", Input).focus()

    @on(Button.Pressed, "#save-cancelled-lesson")
    def save_cancelled_lesson(self) -> None:
        comment = self.query_one("#cancel-lesson-comment", Input).value.strip()
        if not comment:
            self.notify("Bitte gib einen Grund für den Ausfall an.", severity="warning")
            return

        self.dismiss(comment)

    @on(Button.Pressed, "#abort-cancel-lesson")
    def abort_cancel_lesson(self) -> None:
        self.action_cancel()

    def action_cancel(self) -> None:
        self.dismiss(None)
