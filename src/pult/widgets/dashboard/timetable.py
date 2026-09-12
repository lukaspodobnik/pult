from datetime import datetime

from rich.text import Text
from textual.app import ComposeResult

from pult.presentation import WEEKDAYS
from pult.school.period import Period, get_period_at
from pult.school.subject import Subject
from pult.school.timetable import TimetableEntry
from pult.widgets.scrolling import DataTable, Vertical


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
        self.styles.height = 27
        self._column_width = 10
        self.periods = displayed_periods(periods, timetable_entries)
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
        self.periods = displayed_periods(periods, timetable_entries)
        self.styles.height = 27
        self.subjects_by_id = subjects_by_id
        self.timetable_entries_by_slot = {
            (entry.weekday, entry.period): entry for entry in timetable_entries
        }
        table = self.query_one(DataTable)
        position = self.current_time_position or (None, None)
        if old_periods != self.periods or not table.columns:
            table.clear(columns=True)
            self.populate_timetable(*position)
            return
        for period in self.periods:
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
        row_index = next(
            i for i, item in enumerate(self.periods) if item.number == period
        )
        height = 2 if row_index == len(self.periods) - 1 else 3
        lines = content.splitlines()
        centered = []
        for index in range(height):
            line = Text(lines[index] if index < len(lines) else "")
            line.truncate(self._column_width, overflow="ellipsis")
            line.align("center", self._column_width)
            centered.append(line.plain)
        content = "\n".join(centered)
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
            if position[1] is not None:
                from textual.coordinate import Coordinate

                row = next(
                    i for i, p in enumerate(self.periods) if p.number == position[1]
                )
                table.call_after_refresh(
                    table.scroll_to_region,
                    table._get_cell_region(Coordinate(row, 0)),
                    animate=False,
                )

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
            height = 2 if row_index == len(self.periods) - 1 else 3
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
        if is_current_row or is_current_column:
            component = (
                "timetable--current"
                if is_current_row and is_current_column
                else "timetable--period"
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
    # In Pausen zwischen zwei Schulstunden bereits die folgende Zeile markieren.
    if current_weekday is not None and current_period is None:
        now = current_datetime.time()
        if any(period.end <= now for period in periods):
            current_period = min(
                (period for period in periods if period.start > now),
                key=lambda period: period.start,
                default=None,
            )

    return (
        current_weekday,
        current_period.number if current_period is not None else None,
    )


def displayed_periods(
    periods: list[Period], entries: list[TimetableEntry]
) -> list[Period]:
    last = max(8, max((entry.period for entry in entries), default=0))
    return [period for period in periods if period.number <= last]
