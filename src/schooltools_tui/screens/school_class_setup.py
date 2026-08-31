from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, Footer, Header, Input, Label, SelectionList
from textual.widgets.selection_list import Selection

from schooltools_tui.screens.base import SchooltoolsScreen
from schooltools_tui.subject import load_subjects


class SchoolClassSetup(SchooltoolsScreen):
    def compose(self) -> ComposeResult:
        yield Header()

        with Vertical(id="school-class-setup-form"):
            yield Label("Klasse anlegen", id="school-class-setup-title")
            yield Input(placeholder="Klassenname, z. B. '8A'", id="class-name")
            yield SelectionList(*self.get_subject_selections(), id="subjects")
            yield Button("Anlegen", variant="primary", id="submit-class")

        yield Footer()

    def get_subject_selections(self) -> list[Selection]:
        subjects = load_subjects(self.app_config.root)
        return [
            Selection(f"{subject.name}", id=f"{subject.id}") for subject in subjects
        ]

    @on(Button.Pressed, "#submit-class")
    def submit_class(self) -> None:
        selections = self.query_one("#subjects")
