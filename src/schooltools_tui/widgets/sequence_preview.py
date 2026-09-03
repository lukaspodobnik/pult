
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Label

from schooltools_tui.sequence import Sequence


class SequencePreview(VerticalScroll):
    def compose(self) -> ComposeResult:
        yield Label("Sequenzvorschau", id="sequence-preview-title")
        yield Label(
            "Wähle links eine Sequenz aus.",
            id="sequence-preview-placeholder",
        )

        def show_sequence(self, sequence: Sequence) -> None:
            sequence.id
