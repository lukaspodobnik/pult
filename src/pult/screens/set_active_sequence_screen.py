from dataclasses import dataclass
from typing import ClassVar

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Button, Label, Select

from pult.curriculum.sequence import Sequence
from pult.progress.class_progress import ClassProgress
from pult.progress.queries import (
    get_available_next_sequences,
    get_suggested_next_sequence,
)
from pult.school.school_class import SchoolClass
from pult.school.subject import Subject
from pult.screens.base_screen import PultModalScreen
from pult.widgets.form_dialog import FormDialog, FormFields


@dataclass(frozen=True)
class ActiveSequenceFormResult:
    subject_id: str
    sequence_id: str


class SetActiveSequenceScreen(PultModalScreen[ActiveSequenceFormResult | None]):
    BINDINGS: ClassVar = [("escape", "cancel", "Abbrechen")]

    def __init__(
        self,
        school_class: SchoolClass,
        progress: ClassProgress,
        sequences: list[Sequence],
        subjects: list[Subject],
        fixed_subject_id: str | None = None,
    ) -> None:
        super().__init__()
        self.school_class = school_class
        self.progress = progress
        self.sequences = sequences
        self.subjects_by_id = {subject.id: subject for subject in subjects}
        self.available_subject_ids = [
            subject_id
            for subject_id in school_class.subject_ids
            if fixed_subject_id is None or subject_id == fixed_subject_id
            if self.get_available_sequences(subject_id)
        ]

    def compose(self) -> ComposeResult:
        selected_subject_id = self.available_subject_ids[0]
        sequence_options, suggested_sequence_id = self.get_sequence_options(
            selected_subject_id
        )

        with FormDialog(
            "Aktive Sequenz wechseln", id="set-active-sequence-dialog", wide=True
        ):
            with FormFields(classes="form-fields"):
                if len(self.available_subject_ids) > 1:
                    yield Label(
                        f"Klasse {self.school_class.id}", classes="form-context"
                    )
                    yield Label("Fach", classes="field-label")
                    yield Select(
                        [
                            (self.subjects_by_id[subject_id].name, subject_id)
                            for subject_id in self.available_subject_ids
                        ],
                        value=selected_subject_id,
                        allow_blank=False,
                        id="active-sequence-subject",
                    )
                else:
                    yield Label(
                        f"Klasse {self.school_class.id} · {self.subjects_by_id[selected_subject_id].name}",
                        id="active-sequence-subject-label",
                        classes="form-context",
                    )

                yield Label("Sequenz", classes="field-label")
                yield Select(
                    sequence_options,
                    value=suggested_sequence_id,
                    allow_blank=False,
                    id="active-sequence",
                )

            with Horizontal(id="set-active-sequence-actions", classes="form-actions"):
                yield Button("Abbrechen", id="cancel-active-sequence")
                yield Button(
                    "Speichern",
                    variant="primary",
                    id="save-active-sequence",
                )

    def get_available_sequences(self, subject_id: str) -> list[Sequence]:
        return get_available_next_sequences(
            self.progress,
            self.sequences,
            subject_id,
            self.school_class.grade_level,
        )

    def get_sequence_options(
        self,
        subject_id: str,
    ) -> tuple[list[tuple[str, str]], str]:
        available_sequences = self.get_available_sequences(subject_id)
        suggested_sequence = get_suggested_next_sequence(
            self.progress,
            self.sequences,
            subject_id,
            self.school_class.grade_level,
        )
        assert suggested_sequence is not None
        return (
            [
                (
                    f"{sequence.curriculum_section_id} – {sequence.title}",
                    sequence.id,
                )
                for sequence in available_sequences
            ],
            suggested_sequence.id,
        )

    def get_selected_subject_id(self) -> str:
        if len(self.available_subject_ids) == 1:
            return self.available_subject_ids[0]

        value = self.query_one("#active-sequence-subject", Select).value
        assert value is not Select.NULL
        return str(value)

    @on(Select.Changed, "#active-sequence-subject")
    def subject_changed(self, event: Select.Changed) -> None:
        if event.value is Select.NULL:
            return

        options, suggested_sequence_id = self.get_sequence_options(str(event.value))
        sequence_select = self.query_one("#active-sequence", Select)
        sequence_select.set_options(options)
        sequence_select.value = suggested_sequence_id

    @on(Button.Pressed, "#save-active-sequence")
    def save_active_sequence(self) -> None:
        sequence_value = self.query_one("#active-sequence", Select).value
        if sequence_value is Select.NULL:
            return

        self.dismiss(
            ActiveSequenceFormResult(
                subject_id=self.get_selected_subject_id(),
                sequence_id=str(sequence_value),
            )
        )

    @on(Button.Pressed, "#cancel-active-sequence")
    def cancel_active_sequence(self) -> None:
        self.action_cancel()

    def action_cancel(self) -> None:
        self.dismiss(None)
