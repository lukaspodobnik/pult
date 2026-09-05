from typing import ClassVar

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Label, Select

from schooltools_tui.curriculum.sequence import Sequence
from schooltools_tui.screens.base_screen import SchooltoolsModalScreen


class SelectNextSequenceScreen(SchooltoolsModalScreen[str | None]):
    BINDINGS: ClassVar = [("escape", "cancel", "Abbrechen")]

    def __init__(
        self,
        sequences: list[Sequence],
        suggested_sequence_id: str,
    ) -> None:
        super().__init__()
        self.sequences = sequences
        self.suggested_sequence_id = suggested_sequence_id

    def compose(self) -> ComposeResult:
        with Vertical(id="select-next-sequence-dialog"):
            yield Label("Nächste Sequenz wählen", id="select-next-sequence-title")
            yield Select(
                [
                    (
                        f"{sequence.curriculum_section_id} – {sequence.title}",
                        sequence.id,
                    )
                    for sequence in self.sequences
                ],
                value=self.suggested_sequence_id,
                allow_blank=False,
                id="next-sequence",
            )

            with Horizontal(id="select-next-sequence-actions"):
                yield Button("Abbrechen", id="cancel-next-sequence")
                yield Button(
                    "Speichern",
                    variant="primary",
                    id="save-next-sequence",
                )

    @on(Button.Pressed, "#save-next-sequence")
    def save_selection(self) -> None:
        value = self.query_one("#next-sequence", Select).value
        if value is Select.NULL:
            return
        self.dismiss(str(value))

    @on(Button.Pressed, "#cancel-next-sequence")
    def cancel_selection(self) -> None:
        self.action_cancel()

    def action_cancel(self) -> None:
        self.dismiss(None)
