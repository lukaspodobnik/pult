from datetime import datetime
from zoneinfo import ZoneInfo

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import DataTable

from schooltools_tui.school.period import Period, get_period_at
from schooltools_tui.school.subject import Subject
from schooltools_tui.school.timetable import TimetableEntry

WEEKDAYS = (
    ("monday", "Montag"),
    ("tuesday", "Dienstag"),
    ("wednesday", "Mittwoch"),
    ("thursday", "Donnerstag"),
    ("friday", "Freitag"),
)


class TimetableDataTable(DataTable):
    can_focus = False


class HomeView(Vertical):
    def __init__(
        self,
        timetable_entries: list[TimetableEntry],
        subjects: list[Subject],
        periods: list[Period],
    ) -> None:
        super().__init__()
        self.periods = periods
        self.subjects_by_id = {subject.id: subject for subject in subjects}
        self.timetable_entries_by_slot = {
            (entry.weekday, entry.period): entry
            for entry in timetable_entries
        }
        self.current_time_position: tuple[str | None, int | None] | None = None

    def compose(self) -> ComposeResult:
        yield TimetableDataTable(
            id="schedule",
            cursor_type="none",
        )

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

            for weekday, _ in WEEKDAYS:
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
        table.clear(columns=True)
        self.populate_timetable(*position)

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
