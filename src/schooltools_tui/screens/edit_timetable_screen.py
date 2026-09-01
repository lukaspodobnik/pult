



from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Static

from schooltools_tui.timetable import TimetableEntry


class EditTimetableScreen(ModalScreen[TimetableEntry | None]):
    def __init__(self, weekday: str, period: int, entry: TimetableEntry | None) -> None:
        super().__init__()
        self.weekday = weekday
        self.period = period
        self.entry = entry

    def compose(self) -> ComposeResult:
        yield Static("test")
