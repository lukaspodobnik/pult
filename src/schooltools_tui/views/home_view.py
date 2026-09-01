from datetime import datetime
from zoneinfo import ZoneInfo

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import DataTable

from schooltools_tui.period import Period, get_period_at
from schooltools_tui.subject import Subject
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

    def __init__(
        self,
        timetable_entries: list[TimetableEntry],
        subjects: list[Subject],
        periods: list[Period],
    ) -> None:
        super().__init__()
        self.timetable_entries = timetable_entries
        self.periods = periods
        self.subjects_by_id = {subject.id: subject for subject in subjects}
        self.timetable_entries_by_slot = {
            (entry.weekday, entry.period): entry
            for entry in timetable_entries
        }
        self.current_time_position: tuple[str | None, int | None] | None = None

    def compose(self) -> ComposeResult:
        yield DataTable(id="schedule", cursor_type="cell")

    def on_mount(self) -> None:
        self.refresh_time_highlight()
        self.set_interval(30, self.refresh_time_highlight)

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
            cells = []

            for weekday, label in WEEKDAYS:
                entry = self.timetable_entries_by_slot.get(
                    (weekday, period.number)
                )
                if entry is None:
                    content = "--"
                else:
                    subject = self.subjects_by_id[entry.subject_id]
                    content = (
                        f"{entry.school_class_id}-{subject.short_name} {entry.room}"
                    )

                cells.append(
                    self.get_highlighted_text(
                        content,
                        is_current_row=period.number == current_period,
                        is_current_column=weekday == current_weekday,
                    )
                )

            row_label = self.get_highlighted_text(
                str(period.number),
                is_current_row=period.number == current_period,
            )
            table.add_row(
                *cells,
                key=str(period.number),
                label=row_label,
            )

    def refresh_time_highlight(self) -> None:
        position = get_current_timetable_position(
            self.periods,
            datetime.now(ZoneInfo("Europe/Berlin")),
        )
        if position == self.current_time_position:
            return

        self.current_time_position = position
        table = self.query_one("#schedule", DataTable)
        cursor = table.cursor_coordinate
        table.clear(columns=True)
        self.populate_timetable(*position)
        table.move_cursor(row=cursor.row, column=cursor.column)

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


def get_current_timetable_position(
    periods: list[Period],
    current_datetime: datetime,
) -> tuple[str | None, int | None]:
    weekday_index = current_datetime.weekday()
    current_weekday = (
        WEEKDAYS[weekday_index][0]
        if weekday_index < len(WEEKDAYS)
        else None
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
