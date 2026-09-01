

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from schooltools_tui.school_class import SchoolClass


class SchoolClassView(Vertical):
    def __init__(self, school_class: SchoolClass):
        super().__init__()
        self.school_class = school_class

    def compose(self) -> ComposeResult:
        yield Static(f"{self.school_class.id}", id=f"class-{self.school_class.id}")

