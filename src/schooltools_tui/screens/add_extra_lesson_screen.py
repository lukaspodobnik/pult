from dataclasses import dataclass
from datetime import date, datetime
from typing import ClassVar
from zoneinfo import ZoneInfo

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Button, Checkbox, Input, Label, Select

from schooltools_tui.school.school_class import SchoolClass
from schooltools_tui.school.subject import Subject
from schooltools_tui.screens.base_screen import SchooltoolsModalScreen


@dataclass(frozen=True)
class ExtraLessonFormResult:
    school_class_id: str
    subject_id: str
    date: date
    comment: str
    completes_next_lesson: bool


class AddExtraLessonScreen(
    SchooltoolsModalScreen[ExtraLessonFormResult | None]
):
    BINDINGS: ClassVar = [("escape", "cancel", "Abbrechen")]

    def __init__(
        self,
        school_classes: list[SchoolClass],
        subjects: list[Subject],
        fixed_school_class_id: str | None = None,
    ) -> None:
        super().__init__()
        self.school_classes = school_classes
        self.school_classes_by_id = {
            school_class.id: school_class for school_class in school_classes
        }
        self.subjects_by_id = {subject.id: subject for subject in subjects}
        self.fixed_school_class_id = fixed_school_class_id

    def compose(self) -> ComposeResult:
        selected_class_id = self.fixed_school_class_id or self.school_classes[0].id
        subject_options = self.get_subject_options(selected_class_id)

        with VerticalScroll(id="add-extra-lesson-dialog"):
            yield Label("Zusatzunterricht eintragen", id="add-extra-lesson-title")

            yield Label("Klasse", classes="field-label")
            if self.fixed_school_class_id is None:
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
                yield Label(selected_class_id, id="extra-school-class-label")

            yield Label("Fach", classes="field-label")
            yield Select(
                subject_options,
                value=subject_options[0][1],
                allow_blank=False,
                id="extra-subject",
            )

            yield Label("Datum", classes="field-label")
            yield Input(
                value=datetime.now(ZoneInfo("Europe/Berlin")).date().isoformat(),
                placeholder="JJJJ-MM-TT",
                id="extra-date",
            )

            yield Label("Beschreibung", classes="field-label")
            yield Input(
                placeholder="z. B. zusätzliche Wiederholungsstunde",
                id="extra-comment",
            )

            yield Checkbox(
                "Nächste Sequenz-Lesson abschließen",
                id="complete-next-extra-lesson",
            )

            with Horizontal(id="add-extra-lesson-actions"):
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

        subject_value = self.query_one("#extra-subject", Select).value
        if subject_value is Select.NULL:
            return

        try:
            entry_date = date.fromisoformat(
                self.query_one("#extra-date", Input).value.strip()
            )
        except ValueError:
            self.notify("Bitte gib das Datum als JJJJ-MM-TT an.", severity="warning")
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
