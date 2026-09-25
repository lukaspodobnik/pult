from typing import ClassVar

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.widgets import Static
from textual.widgets.option_list import Option

from pult.presentation import WEEKDAYS
from pult.school.school_class import (
    SchoolClass,
    delete_school_class,
    load_school_classes,
)
from pult.school.subject import load_subjects
from pult.school.timetable import (
    delete_timetable_entries_for_school_class,
    get_timetable_path,
    load_timetable,
)
from pult.screens.base_screen import (
    PultScreen,
)
from pult.screens.confirmation_screen import ConfirmationScreen
from pult.screens.setup_school_class_screen import SchoolClassSetupScreen
from pult.widgets.button import Button
from pult.widgets.detail_table import format_detail_table
from pult.widgets.footer import PultFooter
from pult.widgets.scrolling import Horizontal, OptionList, Vertical, VerticalScroll


class ConfirmClassDeletionScreen(ConfirmationScreen):
    def __init__(self, school_class_id: str) -> None:
        super().__init__(
            "Klasse löschen",
            f"Klasse {school_class_id}\n\n"
            "Die Klasse wird einschließlich ihres Unterrichtsprotokolls und "
            "ihrer lokalen Ausfälle gelöscht. Ihre Stundenplaneinträge werden "
            "ebenfalls entfernt.\n\n"
            "Diese Löschung kann in der App nicht rückgängig gemacht werden.",
            confirm_id="confirm-class-deletion",
            cancel_id="cancel-class-deletion",
        )


class EditClassesScreen(PultScreen[None]):
    BINDINGS: ClassVar = [
        ("a", "create_class", "Anlegen"),
        ("d", "delete_class", "Löschen"),
        ("escape", "cancel", "Zurück"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.selected_school_class_id: str | None = None
        self.school_classes: list[SchoolClass] = []

    def compose(self) -> ComposeResult:
        with Vertical(id="edit-classes-screen"):
            with Vertical(id="classes-frame") as frame:
                frame.border_title = "KLASSEN"
                yield Static(id="classes-headings")
                yield Static("Noch keine Klassen angelegt.", id="classes-empty")
                yield OptionList(id="school-classes")
            with VerticalScroll(
                id="class-timetable-details", can_focus=False
            ) as details:
                details.border_title = "UNTERRICHTSTERMINE"
                yield Static(
                    "Wähle eine Klasse aus.", id="class-timetable-text", markup=False
                )

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

        yield PultFooter()

    def on_mount(self) -> None:
        self.refresh_classes()

    def refresh_classes(self) -> None:
        config = self.app_config
        school_classes = load_school_classes(config.root, config.active_school_year)
        self.school_classes = school_classes
        self.subjects = {subject.id: subject for subject in load_subjects(config.root)}
        timetable = load_timetable(
            get_timetable_path(config.root, config.active_school_year)
        )
        weekday_order = {weekday: index for index, (weekday, _) in enumerate(WEEKDAYS)}
        self.lessons_by_class = {
            school_class.id: sorted(
                (
                    entry
                    for entry in timetable
                    if entry.school_class_id == school_class.id
                ),
                key=lambda entry: (
                    weekday_order[entry.weekday],
                    entry.period,
                    entry.subject_id,
                ),
            )
            for school_class in school_classes
        }
        option_list = self.query_one("#school-classes", OptionList)
        self.query_one("#classes-headings", Static).update(self._headings())
        option_list.clear_options()
        option_list.add_options(
            Option(self._format_class(school_class), id=school_class.id)
            for school_class in school_classes
        )

        ids = [school_class.id for school_class in school_classes]
        if self.selected_school_class_id not in ids:
            self.selected_school_class_id = ids[0] if ids else None
        self.query_one("#classes-empty").display = not school_classes
        self.update_details()
        self.query_one("#delete-school-class", Button).disabled = not school_classes

        if school_classes:
            assert self.selected_school_class_id is not None
            option_list.highlighted = ids.index(self.selected_school_class_id)
            option_list.focus()

    def _columns(self, values: tuple[str, str, str]) -> Text:
        width = max(
            72, self.query_one("#school-classes", OptionList).content_size.width
        )
        widths = (12, max(20, width - 12 - 20 - 4), 20)
        result = Text(no_wrap=True, overflow="ellipsis")
        for index, (value, size) in enumerate(zip(values, widths)):
            part = Text(value)
            part.truncate(size, overflow="ellipsis")
            part.align("left", size)
            if index:
                result.append("  ")
            result.append_text(part)
        return result

    def _headings(self) -> Text:
        return self._columns(("Klasse", "Fächer", "Stunden pro Woche"))

    def _format_class(self, school_class: SchoolClass) -> Text:
        subjects = ", ".join(
            self.subjects[key].name for key in school_class.subject_ids
        )
        return self._columns(
            (
                school_class.id,
                subjects,
                str(len(self.lessons_by_class[school_class.id])),
            )
        )

    def on_resize(self) -> None:
        if self.is_mounted:
            self.call_after_refresh(self.refresh_columns)

    def refresh_columns(self) -> None:
        self.update_details()
        listing = self.query_one("#school-classes", OptionList)
        self.query_one("#classes-headings", Static).update(self._headings())
        for school_class in self.school_classes:
            listing.replace_option_prompt(
                school_class.id, self._format_class(school_class)
            )

    def update_details(self) -> None:
        selected = next(
            (
                item
                for item in self.school_classes
                if item.id == self.selected_school_class_id
            ),
            None,
        )
        if selected is None:
            text = (
                "Noch keine Klassen angelegt."
                if not self.school_classes
                else "Wähle eine Klasse aus."
            )
        else:
            text = f"Klasse {selected.id}\n\n"
            lessons = self.lessons_by_class[selected.id]
            if not lessons:
                text += "Noch kein Unterricht im Stundenplan eingetragen."
            else:
                text += f"{'Wochentag':<13} {'Stunde':<8} {'Fach':<30} Raum\n"
                weekdays: dict[str, str] = dict(WEEKDAYS)
                for entry in lessons:
                    text += f"{weekdays[entry.weekday]:<13} {entry.period:<8} {self.subjects[entry.subject_id].name:<30} {entry.room or '—'}\n"
                text = text.rstrip("\n")
        widget = self.query_one("#class-timetable-text", Static)
        widget.update(
            format_detail_table(text, widget.content_size.width)
            if selected is not None and self.lessons_by_class[selected.id]
            else text
        )
        self.query_one("#class-timetable-details", VerticalScroll).scroll_home(
            animate=False
        )

    @on(OptionList.OptionHighlighted, "#school-classes")
    def school_class_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        self.selected_school_class_id = event.option_id
        self.update_details()

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
        try:
            delete_school_class(
                config.root,
                config.active_school_year,
                school_class_id,
            )
            delete_timetable_entries_for_school_class(
                get_timetable_path(config.root, config.active_school_year),
                school_class_id,
            )
        except (OSError, ValueError) as error:
            self.notify(
                f"Beim Löschen der Klasse {school_class_id} ist ein Fehler aufgetreten: {error}",
                severity="error",
            )
            return
        self.refresh_classes()
        self.notify(f"Klasse {school_class_id} und ihre Stundenplaneinträge gelöscht.")

    @on(Button.Pressed, "#close-class-management")
    def close_class_management(self) -> None:
        self.action_cancel()

    def action_cancel(self) -> None:
        self.dismiss()
