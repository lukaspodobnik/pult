from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Header, OptionList, Static
from textual.widgets.option_list import Option

from schooltools_tui.school_class import load_school_classes
from schooltools_tui.screens.base import SchooltoolsScreen
from schooltools_tui.screens.setup_school_class import SchoolClassSetupScreen
from schooltools_tui.timetable import TimetableEntry, get_timetable_path, load_timetable

WEEKDAYS = (
    ("monday", "Montag"),
    ("tuesday", "Dienstag"),
    ("wednesday", "Mittwoch"),
    ("thursday", "Donnerstag"),
    ("friday", "Freitag"),
)


class MainScreen(SchooltoolsScreen[None]):
    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal(id="main"):
            with Vertical(id="picker"):
                yield OptionList(id="picker-options")
                yield Button("Klasse anlegen", variant="primary", id="register-class")

            with Vertical(id="content"):
                yield Static("Stundenplan", id="page-title")
                yield DataTable(id="schedule")
                yield Static("Nächste Stunde", id="next-lesson")
                yield Static("Schuljahr", id="school-year")

        yield Footer()

    def on_mount(self) -> None:
        config = self.app_config
        self.refresh_picker()
        path = get_timetable_path(config.root, config.active_school_year)
        entries = load_timetable(path)
        self.populate_timetable(entries)

    def refresh_picker(self) -> None:
        config = self.app_config
        school_classes = load_school_classes(config.root, config.active_school_year)

        picker = self.query_one("#picker-options", OptionList)
        picker.clear_options()

        picker.add_option(Option("HOME", id="home"))
        for school_class in school_classes:
            picker.add_option(Option(school_class.id, id=f"class-{school_class.id}"))

        picker.highlighted = 0
        picker.focus()

    def populate_timetable(self, entries: list[TimetableEntry]) -> None:
        table = self.query_one("#schedule", DataTable)

        table.add_column("Stunde", key="period")
        for weekday, label in WEEKDAYS:
            table.add_column(label, key=weekday)

        max_period = max(
            (entry.period for entry in entries),
            default=6,
        )

        entries_by_slot = {(entry.weekday, entry.period): entry for entry in entries}

        for period in range(1, max_period + 1):
            cells = [str(period)]

            for weekday, label in WEEKDAYS:
                entry = entries_by_slot.get((weekday, period))
                if entry is None:
                    cells.append("--")
                else:
                    cells.append(f"{entry.class_name}-{entry.subject}{entry.room}")

            table.add_row(*cells)

    @on(Button.Pressed, "#register-class")
    def register_class(self) -> None:
        self.app.push_screen(SchoolClassSetupScreen(), self.school_class_registered)

    def school_class_registered(self, _result: None) -> None:
        self.refresh_picker()
