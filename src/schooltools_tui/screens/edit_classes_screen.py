from typing import ClassVar

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Label, OptionList, Static
from textual.widgets.option_list import Option

from schooltools_tui.school.school_class import (
    delete_school_class,
    load_school_classes,
)
from schooltools_tui.school.timetable import (
    delete_timetable_entries_for_school_class,
    get_timetable_path,
)
from schooltools_tui.screens.base_screen import (
    SchooltoolsModalScreen,
    SchooltoolsScreen,
)
from schooltools_tui.screens.setup_school_class_screen import SchoolClassSetupScreen
from schooltools_tui.widgets.footer import SchooltoolsFooter


class ConfirmClassDeletionScreen(SchooltoolsModalScreen[bool]):
    BINDINGS: ClassVar = [("escape", "cancel", "Abbrechen")]

    def __init__(self, school_class_id: str) -> None:
        super().__init__()
        self.school_class_id = school_class_id

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-class-deletion-dialog"):
            yield Label("Klasse löschen", id="confirm-class-deletion-title")
            yield Label(
                f"Soll die Klasse '{self.school_class_id}' wirklich gelöscht werden?\n"
                "Zugehörige Stundenplaneinträge werden ebenfalls entfernt.",
                id="confirm-class-deletion-message",
            )
            with Horizontal(id="confirm-class-deletion-actions"):
                yield Button("Abbrechen", id="cancel-class-deletion")
                yield Button(
                    "Löschen",
                    variant="error",
                    id="confirm-class-deletion",
                )

    @on(Button.Pressed, "#confirm-class-deletion")
    def confirm_deletion(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#cancel-class-deletion")
    def cancel_deletion(self) -> None:
        self.action_cancel()

    def action_cancel(self) -> None:
        self.dismiss(False)


class EditClassesScreen(SchooltoolsScreen[None]):
    BINDINGS: ClassVar = [
        ("a", "create_class", "Anlegen"),
        ("d", "delete_class", "Löschen"),
        ("escape", "cancel", "Zurück"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.selected_school_class_id: str | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="edit-classes-screen"):
            classes = OptionList(id="school-classes")
            classes.border_title = "KLASSEN"
            yield classes

            with Horizontal(id="edit-classes-actions", classes="management-actions"):
                yield Button("Anlegen", variant="primary", id="create-school-class")
                yield Button(
                    "Löschen",
                    variant="error",
                    id="delete-school-class",
                    disabled=True,
                )
                yield Static(classes="action-spacer")
                yield Button("Zurück", id="close-class-management")

        yield SchooltoolsFooter()

    def on_mount(self) -> None:
        self.refresh_classes()

    def refresh_classes(self) -> None:
        config = self.app_config
        school_classes = load_school_classes(config.root, config.active_school_year)
        option_list = self.query_one("#school-classes", OptionList)
        option_list.clear_options()
        option_list.add_options(
            Option(school_class.id, id=school_class.id)
            for school_class in school_classes
        )

        self.selected_school_class_id = school_classes[0].id if school_classes else None
        self.query_one("#delete-school-class", Button).disabled = not school_classes

        if school_classes:
            option_list.highlighted = 0
            option_list.focus()

    @on(OptionList.OptionHighlighted, "#school-classes")
    def school_class_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        self.selected_school_class_id = event.option_id

    @on(Button.Pressed, "#create-school-class")
    def create_school_class_pressed(self) -> None:
        self.action_create_class()

    def action_create_class(self) -> None:
        self.app.push_screen(SchoolClassSetupScreen(), self.school_class_created)

    def school_class_created(self, _: None) -> None:
        self.refresh_classes()

    @on(Button.Pressed, "#delete-school-class")
    def delete_school_class_pressed(self) -> None:
        self.action_delete_class()

    def action_delete_class(self) -> None:
        if self.selected_school_class_id is None:
            return

        self.app.push_screen(
            ConfirmClassDeletionScreen(self.selected_school_class_id),
            self.school_class_deletion_confirmed,
        )

    def school_class_deletion_confirmed(self, confirmed: bool | None) -> None:
        if not confirmed or self.selected_school_class_id is None:
            return

        config = self.app_config
        school_class_id = self.selected_school_class_id
        delete_school_class(
            config.root,
            config.active_school_year,
            school_class_id,
        )
        delete_timetable_entries_for_school_class(
            get_timetable_path(config.root, config.active_school_year),
            school_class_id,
        )
        self.refresh_classes()

    @on(Button.Pressed, "#close-class-management")
    def close_class_management(self) -> None:
        self.action_cancel()

    def action_cancel(self) -> None:
        self.dismiss()
