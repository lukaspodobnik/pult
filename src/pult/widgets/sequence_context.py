"""Gemeinsamer Sequenzkopf für Unterricht und Aufgaben."""

from pathlib import Path

from rich.text import Text
from textual.widgets import Static

from pult.curriculum.sequence import Sequence
from pult.school.subject import load_subjects
from pult.widgets.scrolling import Vertical


class SequenceContext(Vertical):
    DEFAULT_CSS = """
    SequenceContext {
        height: auto;
        margin-bottom: 1;
        padding: 1;
        border: round $primary;
        border-title-color: $text-accent;
        background: $surface;
    }
    SequenceContext Static { height: auto; }
    """

    def __init__(self, sequence: Sequence, root: Path, *, id: str):
        super().__init__(id=id)
        self.sequence = sequence
        self.subjects = {subject.id: subject.name for subject in load_subjects(root)}
        self.border_title = "SEQUENZ"

    def content(self) -> Text:
        sequence = self.sequence
        subject = self.subjects.get(sequence.subject_id, sequence.subject_id)
        text = Text(f"{subject}\n\n")
        text.append(
            f"{sequence.curriculum_section_id} · {sequence.title}", style="bold"
        )
        return text

    def compose(self):
        yield Static(self.content(), markup=False)

    def update_sequence(self, sequence: Sequence) -> None:
        self.sequence = sequence
        self.query_one(Static).update(self.content())
