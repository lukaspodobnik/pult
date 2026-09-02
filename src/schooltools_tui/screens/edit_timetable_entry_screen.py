from dataclasses import dataclass
from enum import Enum, auto
from typing import ClassVar

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select

from schooltools_tui.school_class import SchoolClass
from schooltools_tui.subject import Subject
from schooltools_tui.timetable import TimetableEntry


class TimetableEditAction(Enum):
    SAVE = auto()
    DELETE = auto()


@dataclass(frozen=True)
class TimetableEditResult:
    action: TimetableEditAction
    entry: TimetableEntry


class EditTimetabelEntryScreen(ModalScreen[TimetableEditResult | None]):
    BINDINGS: ClassVar = [("escape", "cancel", "Abbrechen")]

    def __init__(
        self,
        weekday: str,
        period: int,
        entry: TimetableEntry | None,
        school_classes: list[SchoolClass],
        subjects: list[Subject],
    ) -> None:
        super().__init__()
        self.weekday = weekday
        self.period = period
        self.entry = entry
        self.school_classes = school_classes
        self.subjects_by_id = {subject.id: subject for subject in subjects}

    def compose(self) -> ComposeResult:
        selected_class_id = (
            self.entry.school_class_id
            if self.entry is not None
            else self.school_classes[0].id
        )
        subject_options = self.get_subject_options(selected_class_id)
        selected_subject_id = (
            self.entry.subject_id if self.entry is not None else subject_options[0][1]
        )

        with Vertical(id="edit-timetable-dialog"):
            yield Label(
                f"{self.weekday}, {self.period}. Stunde",
                id="edit-timetable-title",
            )

            yield Label("Klasse", classes="field-label")
            yield Select(
                [
                    (school_class.id, school_class.id)
                    for school_class in self.school_classes
                ],
                value=selected_class_id,
                allow_blank=False,
                id="school-class",
            )

            yield Label("Fach", classes="field-label")
            yield Select(
                subject_options,
                value=selected_subject_id,
                allow_blank=False,
                id="subject",
            )

            yield Label("Raum", classes="field-label")
            yield Input(
                value=self.entry.room if self.entry is not None else "",
                placeholder="Raum",
                id="room",
            )

            with Horizontal(id="edit-timetable-actions"):
                if self.entry is not None:
                    yield Button(
                        "Löschen",
                        variant="error",
                        id="delete-timetable-entry",
                    )

                yield Button("Abbrechen", id="cancel-timetable-entry-edit")
                yield Button(
                    "Speichern",
                    variant="primary",
                    id="save-timetable-entry",
                )

    def get_subject_options(self, school_class_id: str) -> list[tuple[str, str]]:
        school_class = next(
            school_class
            for school_class in self.school_classes
            if school_class.id == school_class_id
        )

        return [
            (self.subjects_by_id[subject_id].name, subject_id)
            for subject_id in school_class.subject_ids
        ]

    @on(Select.Changed, "#school-class")
    def school_class_changed(self, event: Select.Changed) -> None:
        if event.value is Select.NULL:
            return

        subject_select = self.query_one("#subject", Select)
        subject_select.set_options(self.get_subject_options(str(event.value)))

    @on(Button.Pressed, "#save-timetable-entry")
    def save_timetable_entry(self) -> None:
        school_class = self.query_one("#school-class", Select).value
        subject = self.query_one("#subject", Select).value
        room = self.query_one("#room", Input).value.strip()

        if school_class is Select.NULL or subject is Select.NULL:
            return

        self.dismiss(
            TimetableEditResult(
                action=TimetableEditAction.SAVE,
                entry=TimetableEntry(
                    weekday=self.weekday,
                    period=self.period,
                    school_class_id=str(school_class),
                    subject_id=str(subject),
                    room=room,
                ),
            )
        )

    @on(Button.Pressed, "#delete-timetable-entry")
    def delete_timetable_entry(self) -> None:
        if self.entry is None:
            return

        self.dismiss(
            TimetableEditResult(
                action=TimetableEditAction.DELETE,
                entry=self.entry,
            )
        )

    @on(Button.Pressed, "#cancel-timetable-entry-edit")
    def cancel_timetable_entry_edit(self) -> None:
        self.action_cancel()

    def action_cancel(self) -> None:
        self.dismiss(None)
