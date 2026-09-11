from dataclasses import dataclass
from datetime import date, datetime
from typing import ClassVar
from zoneinfo import ZoneInfo

from textual import on
from textual.app import ComposeResult
from textual.widgets import Button, Checkbox, Input, Label, Select

from pult.presentation import DATE_INPUT_HINT, format_date, parse_date
from pult.school.school_class import SchoolClass
from pult.school.subject import Subject
from pult.screens.base_screen import PultModalScreen
from pult.widgets.form_dialog import FormDialog, FormFields
from pult.widgets.scrolling import Horizontal


@dataclass(frozen=True)
class ExtraLessonFormResult:
    school_class_id: str
    subject_id: str
    date: date
    comment: str
    completes_next_lesson: bool


class AddExtraLessonScreen(PultModalScreen[ExtraLessonFormResult | None]):
    BINDINGS: ClassVar = [("escape", "cancel", "Abbrechen")]

    def __init__(
        self,
        school_classes: list[SchoolClass],
        subjects: list[Subject],
        fixed_school_class_id: str | None = None,
        fixed_subject_id: str | None = None,
    ) -> None:
        super().__init__()
        self.school_classes = school_classes
        self.school_classes_by_id = {
            school_class.id: school_class for school_class in school_classes
        }
        self.subjects_by_id = {subject.id: subject for subject in subjects}
        self.fixed_school_class_id = fixed_school_class_id
        self.fixed_subject_id = fixed_subject_id
        if fixed_subject_id is not None and (
            fixed_school_class_id not in self.school_classes_by_id
            or fixed_subject_id
            not in self.school_classes_by_id[fixed_school_class_id].subject_ids
        ):
            raise ValueError("Das feste Fach muss zur festgelegten Klasse gehören.")

    def compose(self) -> ComposeResult:
        selected_class_id = self.fixed_school_class_id or self.school_classes[0].id
        subject_options = self.get_subject_options(selected_class_id)

        with FormDialog("Zusatzunterricht", id="add-extra-lesson-dialog"):
            with FormFields(classes="form-fields"):
                if self.fixed_school_class_id is None:
                    yield Label("Klasse", classes="field-label")
                    yield Select(
                        [
                            (school_class.id, school_class.id)
                            for school_class in self.school_classes
                        ],
                        value=selected_class_id,
                        allow_blank=False,
                        id="extra-school-class",
                    )
                else:
                    context = f"Klasse {selected_class_id}"
                    if self.fixed_subject_id is not None:
                        context += (
                            f" · {self.subjects_by_id[self.fixed_subject_id].name}"
                        )
                    yield Label(
                        context, id="extra-school-class-label", classes="form-context"
                    )

                if self.fixed_subject_id is None:
                    yield Label("Fach", classes="field-label")
                    yield Select(
                        subject_options,
                        value=subject_options[0][1],
                        allow_blank=False,
                        id="extra-subject",
                    )

                yield Label("Datum", classes="field-label")
                yield Input(
                    value=format_date(datetime.now(ZoneInfo("Europe/Berlin")).date()),
                    placeholder=DATE_INPUT_HINT,
                    id="extra-date",
                )

                yield Label("Beschreibung", classes="field-label")
                yield Input(
                    placeholder="z. B. zusätzliche Wiederholungsstunde",
                    id="extra-comment",
                )

                yield Checkbox(
                    "Nächste geplante Stunde abschließen",
                    id="complete-next-extra-lesson",
                )

            with Horizontal(id="add-extra-lesson-actions", classes="form-actions"):
                yield Button("Abbrechen", id="cancel-extra-lesson")
                yield Button(
                    "Speichern",
                    variant="primary",
                    id="save-extra-lesson",
                )

    def get_subject_options(self, school_class_id: str) -> list[tuple[str, str]]:
        school_class = self.school_classes_by_id[school_class_id]
        return [
            (self.subjects_by_id[subject_id].name, subject_id)
            for subject_id in school_class.subject_ids
        ]

    @on(Select.Changed, "#extra-school-class")
    def school_class_changed(self, event: Select.Changed) -> None:
        if event.value is Select.NULL:
            return

        subject_select = self.query_one("#extra-subject", Select)
        options = self.get_subject_options(str(event.value))
        subject_select.set_options(options)
        subject_select.value = options[0][1]

    @on(Button.Pressed, "#save-extra-lesson")
    def save_extra_lesson(self) -> None:
        if self.fixed_school_class_id is None:
            school_class_value = self.query_one("#extra-school-class", Select).value
            if school_class_value is Select.NULL:
                return
            school_class_id = str(school_class_value)
        else:
            school_class_id = self.fixed_school_class_id

        subject_value = (
            self.fixed_subject_id
            if self.fixed_subject_id is not None
            else self.query_one("#extra-subject", Select).value
        )
        if subject_value is Select.NULL:
            return

        try:
            entry_date = parse_date(self.query_one("#extra-date", Input).value.strip())
        except ValueError as error:
            self.notify(str(error), severity="warning")
            return

        comment = self.query_one("#extra-comment", Input).value.strip()
        if not comment:
            self.notify("Bitte beschreibe den Zusatzunterricht.", severity="warning")
            return

        self.dismiss(
            ExtraLessonFormResult(
                school_class_id=school_class_id,
                subject_id=str(subject_value),
                date=entry_date,
                comment=comment,
                completes_next_lesson=self.query_one(
                    "#complete-next-extra-lesson",
                    Checkbox,
                ).value,
            )
        )

    @on(Button.Pressed, "#cancel-extra-lesson")
    def cancel_extra_lesson(self) -> None:
        self.action_cancel()

    def action_cancel(self) -> None:
        self.dismiss(None)
