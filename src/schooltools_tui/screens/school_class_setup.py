from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, Footer, Header, Input, Label, SelectionList
from textual.widgets.selection_list import Selection

from schooltools_tui.initialization.school_class import initialize_school_class
from schooltools_tui.school_class import SchoolClass
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
            Selection(f"{subject.name}", f"{subject.id}", id=f"{subject.id}") for subject in subjects
        ]

    @on(Button.Pressed, "#submit-class")
    def submit_class(self) -> None:
        school_class_id_input = self.query_one("#class-name", Input)
        subjects = self.query_one("#subjects", SelectionList).selected
        school_class = SchoolClass(id=school_class_id_input.value, subject_ids=subjects)
        initialize_school_class(self.app_config.root, self.app_config.active_school_year, school_class)



