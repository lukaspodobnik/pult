from datetime import datetime

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import DataTable

from schooltools_tui.presentation import WEEKDAYS
from schooltools_tui.school.period import Period, get_period_at
from schooltools_tui.school.subject import Subject
from schooltools_tui.school.timetable import TimetableEntry


class TimetableDataTable(DataTable):
    can_focus = False


class TimetablePanel(Vertical):
    """Zeige den Stundenplan ohne Cursor mit Tages- und Stundenmarkierung."""

    COMPONENT_CLASSES = {"timetable--period", "timetable--current"}
    DEFAULT_CSS = """
    TimetablePanel > .timetable--period {
        background: $surface;
        background-tint: $accent 8%;
        text-style: none;
    }
    TimetablePanel > .timetable--current {
        background: $surface;
        background-tint: $accent 20%;
        text-style: none;
    }
    """

    def notify_style_update(self) -> None:
        super().notify_style_update()
        if self.is_mounted:
            self.call_after_refresh(self._refresh_table_styles)

    def _refresh_table_styles(self) -> None:
        table = self.query_one(DataTable)
        table.clear(columns=True)
        self.populate_timetable(*(self.current_time_position or (None, None)))

    def __init__(
        self,
        timetable_entries: list[TimetableEntry],
        subjects_by_id: dict[str, Subject],
        periods: list[Period],
    ) -> None:
        super().__init__(id="timetable-panel", classes="dashboard-panel")
        self.border_title = "STUNDENPLAN"
        self.styles.height = max(0, len(periods) * 3 - 1) + 3
        self._column_width = 10
        self.periods = periods
        self.subjects_by_id = subjects_by_id
        self.timetable_entries_by_slot = {
            (entry.weekday, entry.period): entry for entry in timetable_entries
        }
        self.current_time_position: tuple[str | None, int | None] | None = None

    def compose(self) -> ComposeResult:
        yield TimetableDataTable(
            id="schedule",
            cursor_type="none",
            cell_padding=0,
            header_height=2,
            show_row_labels=False,
        )

    def on_resize(self) -> None:
        if not self.is_mounted:
            return
        width = max(6, (self.content_size.width - 2 - 12 - 5) // 5)
        if width != self._column_width:
            self._column_width = width
            table = self.query_one(DataTable)
            table.clear(columns=True)
            self.populate_timetable(*(self.current_time_position or (None, None)))

    def update_data(
        self,
        timetable_entries: list[TimetableEntry],
        subjects_by_id: dict[str, Subject],
        periods: list[Period],
    ) -> None:
        """Aktualisiere Zellen; ändere die Tabellenstruktur nur bei neuen Stundenzeilen."""
        old_periods = self.periods
        self.periods = periods
        self.styles.height = max(0, len(periods) * 3 - 1) + 3
        self.subjects_by_id = subjects_by_id
        self.timetable_entries_by_slot = {
            (entry.weekday, entry.period): entry for entry in timetable_entries
        }
        table = self.query_one(DataTable)
        position = self.current_time_position or (None, None)
        if old_periods != periods or not table.columns:
            table.clear(columns=True)
            self.populate_timetable(*position)
            return
        for period in periods:
            for weekday, _ in WEEKDAYS:
                cell = self._cell(weekday, period.number, *position)
                if table.get_cell(str(period.number), weekday) != cell:
                    table.update_cell(str(period.number), weekday, cell)

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
            content = f"{entry.school_class_id} · {subject.short_name}\n{entry.room}"
        if period == current_period:
            row_index = next(
                i for i, item in enumerate(self.periods) if item.number == period
            )
            height = 2 if row_index >= len(self.periods) - 2 else 3
            lines = content.splitlines()
            content = "\n".join(
                (lines[i] if i < len(lines) else "").ljust(self._column_width)
                for i in range(height)
            )
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

        table.add_column(Text("\n" + "─" * 12, style="dim"), key="period", width=12)
        for index, (weekday, label) in enumerate(WEEKDAYS):
            table.add_column(
                Text("│\n┼", style="dim"),
                key=f"separator-{index}",
                width=1,
            )
            header = self.get_highlighted_text(
                label.center(self._column_width),
            )
            header.append("\n" + "─" * self._column_width, style="dim")
            table.add_column(
                header,
                key=weekday,
                width=self._column_width,
            )

        for row_index, period in enumerate(self.periods):
            height = 2 if row_index >= len(self.periods) - 2 else 3
            cells = []
            for index, (weekday, _) in enumerate(WEEKDAYS):
                separator = self.get_highlighted_text(
                    "\n".join(["│"] * height),
                    is_current_row=period.number == current_period,
                )
                separator.stylize("dim")
                cells.append(separator)
                cells.append(
                    self._cell(weekday, period.number, current_weekday, current_period)
                )

            row_label = self.get_highlighted_text(
                f"{period.number}. Std.".center(12),
                is_current_row=period.number == current_period,
            )
            row_label.append(f"\n{period.start:%H:%M}–{period.end:%H:%M} ", style="dim")
            if height > 2:
                row_label.append("\n" + " " * 12)
            table.add_row(
                row_label,
                *cells,
                key=str(period.number),
                label=row_label,
                height=height,
            )

    def get_highlighted_text(
        self,
        content: str,
        *,
        is_current_row: bool = False,
        is_current_column: bool = False,
    ) -> Text:
        text = Text(content, no_wrap=True, overflow="ellipsis")
        component = None
        if is_current_row:
            component = (
                "timetable--current" if is_current_column else "timetable--period"
            )
        if component is not None:
            text.style = self.get_component_rich_style(component)
        return text


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
