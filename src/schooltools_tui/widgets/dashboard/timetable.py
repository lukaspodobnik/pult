from datetime import datetime

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import DataTable, Static

from schooltools_tui.presentation import WEEKDAYS
from schooltools_tui.school.period import Period, get_period_at
from schooltools_tui.school.subject import Subject
from schooltools_tui.school.timetable import TimetableEntry


class TimetableDataTable(DataTable):
    can_focus = False


class TimetablePanel(Vertical):
    """Zeige den Stundenplan ohne Cursor mit Tages- und Stundenmarkierung."""

    def __init__(
        self,
        timetable_entries: list[TimetableEntry],
        subjects_by_id: dict[str, Subject],
        periods: list[Period],
    ) -> None:
        super().__init__(id="timetable-panel", classes="dashboard-panel")
        self.periods = periods
        self.subjects_by_id = subjects_by_id
        self.timetable_entries_by_slot = {
            (entry.weekday, entry.period): entry for entry in timetable_entries
        }
        self.current_time_position: tuple[str | None, int | None] | None = None

    def compose(self) -> ComposeResult:
        yield Static("STUNDENPLAN", classes="dashboard-heading")
        yield TimetableDataTable(id="schedule", cursor_type="none")

    def update_data(
        self,
        timetable_entries: list[TimetableEntry],
        subjects_by_id: dict[str, Subject],
        periods: list[Period],
    ) -> None:
        """Aktualisiere Zellen; ändere die Tabellenstruktur nur bei neuen Stundenzeilen."""
        old_numbers = [period.number for period in self.periods]
        self.periods = periods
        self.subjects_by_id = subjects_by_id
        self.timetable_entries_by_slot = {
            (entry.weekday, entry.period): entry for entry in timetable_entries
        }
        table = self.query_one(DataTable)
        position = self.current_time_position or (None, None)
        if old_numbers != [period.number for period in periods] or not table.columns:
            table.clear(columns=True)
            self.populate_timetable(*position)
            return
        for period in periods:
            for weekday, _ in WEEKDAYS:
                cell = self._cell(weekday, period.number, *position)
                if table.get_cell(str(period.number), weekday) != cell:
                    table.update_cell(
                        str(period.number), weekday, cell, update_width=True
                    )

    def _cell(
        self,
        weekday: str,
        period: int,
        current_weekday: str | None,
        current_period: int | None,
    ) -> Text:
        entry = self.timetable_entries_by_slot.get((weekday, period))
        content = "--"
        if entry is not None:
            subject = self.subjects_by_id[entry.subject_id]
            content = f"{entry.school_class_id}-{subject.short_name} {entry.room}"
        return self.get_highlighted_text(
            content,
            is_current_row=period == current_period,
            is_current_column=weekday == current_weekday,
        )

    def refresh_time_highlight(self, current_datetime: datetime) -> None:
        """Baue die Tabelle nur bei veränderter Zeitmarkierung neu auf."""
        position = get_current_timetable_position(self.periods, current_datetime)
        if position != self.current_time_position:
            self.current_time_position = position
            table = self.query_one("#schedule", DataTable)
            table.clear(columns=True)
            self.populate_timetable(*position)

    def populate_timetable(
        self,
        current_weekday: str | None,
        current_period: int | None,
    ) -> None:
        table = self.query_one("#schedule", DataTable)

        for weekday, label in WEEKDAYS:
            table.add_column(
                self.get_highlighted_text(
                    label,
                    is_current_column=weekday == current_weekday,
                ),
                key=weekday,
            )

        for period in self.periods:
            cells = [
                self._cell(weekday, period.number, current_weekday, current_period)
                for weekday, _ in WEEKDAYS
            ]

            row_label = self.get_highlighted_text(
                str(period.number),
                is_current_row=period.number == current_period,
            )
            table.add_row(
                *cells,
                key=str(period.number),
                label=row_label,
            )

    @staticmethod
    def get_highlighted_text(
        content: str,
        *,
        is_current_row: bool = False,
        is_current_column: bool = False,
    ) -> Text:
        styles = []
        if is_current_column:
            styles.append("bold")
        if is_current_row:
            styles.append("underline")
        if is_current_row and is_current_column:
            styles.append("reverse")

        return Text(content, style=" ".join(styles))


def get_current_timetable_position(
    periods: list[Period],
    current_datetime: datetime,
) -> tuple[str | None, int | None]:
    """Bestimme Wochentag und laufende Schulstunde für das Tabellenhighlight."""
    weekday_index = current_datetime.weekday()
    current_weekday = (
        WEEKDAYS[weekday_index][0] if weekday_index < len(WEEKDAYS) else None
    )
    current_period = (
        get_period_at(periods, current_datetime.time())
        if current_weekday is not None
        else None
    )

    return (
        current_weekday,
        current_period.number if current_period is not None else None,
    )
