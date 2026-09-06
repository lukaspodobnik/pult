from typing import ClassVar

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Input, Label, SelectionList
from textual.widgets.selection_list import Selection

from schooltools_tui.initialization.school_class import (
    SchoolClassSetupError,
    initialize_school_class,
)
from schooltools_tui.school.school_class import (
    SchoolClass,
    get_grade_level_from_school_class_id,
)
from schooltools_tui.school.subject import Subject, load_subjects
from schooltools_tui.screens.base_screen import SchooltoolsModalScreen


class SchoolClassSetupScreen(SchooltoolsModalScreen[None]):
    BINDINGS: ClassVar = [("escape", "cancel", "Abbrechen")]

    def compose(self) -> ComposeResult:
        self.subjects = load_subjects(self.app_config.root)
        self.current_grade_level: int | None = None

        with Vertical(id="school-class-setup-form"):
            yield Label("Klasse anlegen", id="school-class-setup-title")
            yield Input(placeholder="Klassenname, z. B. '8A'", id="class-name")
            yield SelectionList(id="subjects")
            with Horizontal(id="school-class-setup-actions"):
                yield Button("Abbrechen", id="cancel-class-setup")
                yield Button("Anlegen", variant="primary", id="submit-class")

    def get_subject_selections(self, grade_level: int) -> list[Selection]:
        return [
            self.get_subject_selection(subject)
            for subject in self.subjects
            if grade_level in subject.grade_levels
        ]

    @staticmethod
    def get_subject_selection(subject: Subject) -> Selection:
        return Selection(subject.name, subject.id, id=subject.id)

    @on(Input.Changed, "#class-name")
    def update_subject_selections(self, event: Input.Changed) -> None:
        try:
            grade_level = get_grade_level_from_school_class_id(event.value)
        except ValueError:
            grade_level = None

        if grade_level == self.current_grade_level:
            return

        self.current_grade_level = grade_level
        selection_list = self.query_one("#subjects", SelectionList)
        selection_list.clear_options()

        if grade_level is not None:
            selection_list.add_options(self.get_subject_selections(grade_level))
            selection_list.highlighted = 0

    @on(Button.Pressed, "#submit-class")
    def submit_class(self) -> None:
        school_class_id_input = self.query_one("#class-name", Input)
        subjects = self.query_one("#subjects", SelectionList).selected

        try:
            school_class = SchoolClass(
                id=school_class_id_input.value,
                grade_level=get_grade_level_from_school_class_id(
                    school_class_id_input.value
                ),
                subject_ids=subjects,
            )
        except ValueError as error:
            self.notify(str(error), severity="error")
            return

        try:
            initialize_school_class(
                self.app_config.root, self.app_config.active_school_year, school_class
            )
        except SchoolClassSetupError as error:
            self.notify(str(error), severity="error")
            return

        self.dismiss()

    @on(Button.Pressed, "#cancel-class-setup")
    def cancel_setup(self) -> None:
        self.action_cancel()

    def action_cancel(self) -> None:
        self.dismiss(None)
