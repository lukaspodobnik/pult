from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import DataTable

from schooltools_tui.timetable import TimetableEntry

WEEKDAYS = (
    ("monday", "Montag"),
    ("tuesday", "Dienstag"),
    ("wednesday", "Mittwoch"),
    ("thursday", "Donnerstag"),
    ("friday", "Freitag"),
)


class HomeView(Vertical):
    class EditTimetableSlot(Message):
        def __init__(
            self,
            weekday: str,
            period: int,
            entry: TimetableEntry | None,
        ) -> None:
            super().__init__()
            self.weekday = weekday
            self.period = period
            self.entry = entry

    def __init__(self, timetable_entries: list[TimetableEntry]):
        super().__init__()
        self.timetable_entries = timetable_entries
        self.timetable_entries_by_slot = {(entry.weekday, entry.period): entry for entry in timetable_entries}

    def compose(self) -> ComposeResult:
        yield DataTable(id="schedule", cursor_type="cell")

    def on_mount(self) -> None:
        self.populate_timetable(self.timetable_entries)

    def populate_timetable(self, entries: list[TimetableEntry]) -> None:
        table = self.query_one("#schedule", DataTable)

        for weekday, label in WEEKDAYS:
            table.add_column(label, key=weekday)

        max_period = max(
            (entry.period for entry in entries),
            default=6,
        )

        for period in range(1, max_period + 1):
            cells = []

            for weekday, label in WEEKDAYS:
                entry = self.timetable_entries_by_slot.get((weekday, period))
                if entry is None:
                    cells.append("--")
                else:
                    cells.append(f"{entry.class_name}-{entry.subject}{entry.room}")

            table.add_row(*cells, key=str(period), label=str(period))

    @on(DataTable.CellSelected, "#schedule")
    def select_timetable_slot(self, event: DataTable.CellSelected) -> None:
        weekday = event.cell_key.column_key.value
        period = event.cell_key.row_key.value

        assert weekday is not None
        assert period is not None

        weekday = str(weekday)
        period = int(period)
        entry = self.timetable_entries_by_slot.get((weekday, period))

        self.post_message(
            self.EditTimetableSlot(
                weekday=weekday,
                period=period,
                entry=entry,
            )
        )
