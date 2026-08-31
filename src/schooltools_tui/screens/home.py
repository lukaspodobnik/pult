from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Static

from schooltools_tui.screens.base import SchooltoolsScreen
from schooltools_tui.timetable import TimetableEntry, get_timetable_path, load_timetable

WEEKDAYS = (
    ("monday", "Montag"),
    ("tuesday", "Dienstag"),
    ("wednesday", "Mittwoch"),
    ("thursday", "Donnerstag"),
    ("friday", "Freitag"),
)

class HomeScreen(SchooltoolsScreen[None]):
    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal(id="main"):
            with Vertical(id="picker"):
                yield Static("Home", classes="picker-entry")
                yield Static("7A", classes="picker-entry")
                yield Static("8B", classes="picker-entry")

            with Vertical(id="content"):
                yield Static("Stundenplan", id="page-title")
                yield DataTable(id="schedule")
                yield Static("Nächste Stunde", id="next-lesson")
                yield Static("Schuljahr", id="school-year")

        yield Footer()

    def on_mount(self) -> None:
        config = self.app_config
        school_year = config.active_school_year

        assert school_year is not None

        path = get_timetable_path(config.root, school_year)
        entries = load_timetable(path)
        self.populate_timetable(entries)

    def populate_timetable(self, entries: list[TimetableEntry]) -> None:
        table = self.query_one("#schedule", DataTable)

        table.add_column("Stunde", key="period")
        for weekday, label in WEEKDAYS:
            table.add_column(label, key=weekday)

        max_period = max(
            (entry.period for entry in entries),
            default=6,
        )
        
        entries_by_slot = {
            (entry.weekday, entry.period): entry
            for entry in entries
        }

        for period in range(1, max_period + 1):
            cells = [str(period)]

            for weekday, label in WEEKDAYS:
                entry = entries_by_slot.get((weekday, period))
                if entry is None:
                    cells.append("--")
                else:
                    cells.append(f"{entry.class_name}-{entry.subject}{entry.room}")

            table.add_row(*cells)



