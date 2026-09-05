from datetime import datetime
from zoneinfo import ZoneInfo

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import DataTable, ProgressBar, Static

from schooltools_tui.curriculum.sequence import Sequence
from schooltools_tui.progress.class_progress import TeachingAction, TeachingLogEntry
from schooltools_tui.progress.queries import (
    DailyAdditionalEntry,
    DailyTimetableEntry,
    HomeDashboardSummary,
    PlannedLesson,
    get_time_highlighted_occurrence,
)
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

WEEKDAY_NAMES = (
    "Montag",
    "Dienstag",
    "Mittwoch",
    "Donnerstag",
    "Freitag",
    "Samstag",
    "Sonntag",
)

ACTION_ICONS = {
    TeachingAction.COMPLETED: "✓",
    TeachingAction.CONTINUED: "↻",
    TeachingAction.CANCELLED: "×",
}


class TimetableDataTable(DataTable):
    can_focus = False


class DailyScheduleRow(Horizontal):
    def __init__(
        self,
        daily_entry: DailyTimetableEntry,
        subjects_by_id: dict[str, Subject],
        sequences_by_key: dict[tuple[int, str, str], Sequence],
    ) -> None:
        action = daily_entry.action
        classes = "daily-schedule-row"
        if action is not None:
            classes += f" {action.value}"
        if daily_entry.is_time_highlighted:
            classes += " time-highlighted"
        super().__init__(classes=classes)
        self.daily_entry = daily_entry
        self.subjects_by_id = subjects_by_id
        self.sequences_by_key = sequences_by_key

    @property
    def occurrence(self) -> tuple[str, str, int]:
        entry = self.daily_entry.timetable_entry
        return entry.school_class_id, entry.subject_id, entry.period

    def compose(self) -> ComposeResult:
        entry = self.daily_entry.timetable_entry
        yield Static(
            ACTION_ICONS.get(self.daily_entry.action, " "),
            classes="day-status",
        )
        yield Static(f"{entry.period}.", classes="day-period")
        with Vertical(classes="day-entry-content"):
            yield Static(
                f"{entry.school_class_id} · "
                f"{self.subjects_by_id[entry.subject_id].short_name}",
                classes="day-entry-heading",
            )
            lesson_title = self._get_lesson_title()
            if lesson_title is not None:
                yield Static(lesson_title, classes="day-entry-lesson")

    def _get_lesson_title(self) -> str | None:
        if self.daily_entry.planned_lesson is not None:
            return self.daily_entry.planned_lesson.lesson.title or "Lesson ohne Titel"

        log_entry = self.daily_entry.log_entry
        if log_entry is None or log_entry.lesson_id is None:
            return None

        sequence = self.sequences_by_key[
            (
                self.daily_entry.grade_level,
                log_entry.subject_id,
                log_entry.sequence_id,
            )
        ]
        lesson = next(
            lesson for lesson in sequence.lessons if lesson.id == log_entry.lesson_id
        )
        return lesson.title or "Lesson ohne Titel"


class DailyAdditionalRow(Horizontal):
    def __init__(
        self,
        entry: DailyAdditionalEntry,
        subjects_by_id: dict[str, Subject],
    ) -> None:
        super().__init__(classes="daily-additional-row")
        self.entry = entry
        self.subjects_by_id = subjects_by_id

    def compose(self) -> ComposeResult:
        yield Static("+", classes="day-status")
        with Vertical(classes="day-entry-content"):
            yield Static(
                f"{self.entry.school_class_id} · "
                f"{self.subjects_by_id[self.entry.log_entry.subject_id].short_name} "
                "· Zusatzunterricht",
                classes="day-entry-heading",
            )
            if self.entry.log_entry.comment:
                yield Static(
                    self.entry.log_entry.comment,
                    classes="day-entry-lesson",
                )


class HomeView(Vertical):
    class DashboardRefreshRequested(Message):
        pass

    def __init__(
        self,
        timetable_entries: list[TimetableEntry],
        subjects: list[Subject],
        periods: list[Period],
        sequences: list[Sequence],
        dashboard: HomeDashboardSummary,
    ) -> None:
        super().__init__()
        self.periods = periods
        self.dashboard = dashboard
        self.subjects_by_id = {subject.id: subject for subject in subjects}
        self.sequences_by_key = {
            (sequence.grade_level, sequence.subject_id, sequence.id): sequence
            for sequence in sequences
        }
        self.timetable_entries_by_slot = {
            (entry.weekday, entry.period): entry
            for entry in timetable_entries
        }
        self.current_time_position: tuple[str | None, int | None] | None = None
        self._refresh_requested = False

    def compose(self) -> ComposeResult:
        progress = self.dashboard.school_year_progress
        with Horizontal(id="school-year-progress"):
            yield Static(
                f"Schuljahr {self._format_school_year(progress.school_year)}",
                id="school-year-progress-label",
            )
            progress_bar = ProgressBar(
                total=progress.total_day_count,
                show_percentage=False,
                show_eta=False,
                id="school-year-progress-bar",
            )
            progress_bar.progress = progress.elapsed_day_count
            yield progress_bar
            yield Static(
                f"{progress.percentage} %",
                id="school-year-progress-percentage",
            )

        with Horizontal(id="home-dashboard-content"):
            with Vertical(id="timetable-panel", classes="dashboard-panel"):
                yield Static("STUNDENPLAN", classes="dashboard-heading")
                yield TimetableDataTable(id="schedule", cursor_type="none")

            with Vertical(id="home-dashboard-sidebar"):
                yield from self._compose_next_lesson()
                yield from self._compose_daily_schedule()

    def _compose_next_lesson(self) -> ComposeResult:
        with Vertical(id="next-planned-lesson", classes="dashboard-panel"):
            yield Static("NÄCHSTE GEPLANTE LESSON", classes="dashboard-heading")
            planned_lesson = self.dashboard.next_planned_lesson
            if planned_lesson is None:
                yield Static(
                    "Keine offene geplante Lesson",
                    classes="dashboard-empty",
                )
                return

            subject = self.subjects_by_id[planned_lesson.subject_id]
            sequence = self._get_sequence(planned_lesson)
            yield Static(
                f"{planned_lesson.school_class_id} · {subject.name}",
                classes="next-lesson-heading",
            )
            yield Static(
                f"{sequence.curriculum_section_id} · {sequence.title}",
                classes="next-lesson-sequence",
            )
            yield Static(
                planned_lesson.lesson.title or "Lesson ohne Titel",
                classes="next-lesson-name",
            )
            yield Static(
                self._format_planned_occurrence(planned_lesson),
                classes="next-lesson-occurrence",
            )

    def _compose_daily_schedule(self) -> ComposeResult:
        daily_schedule = self.dashboard.daily_schedule
        with Vertical(id="daily-schedule", classes="dashboard-panel"):
            yield Static(
                f"HEUTE · {WEEKDAY_NAMES[daily_schedule.date.weekday()].upper()}",
                classes="dashboard-heading",
            )
            with VerticalScroll(id="daily-schedule-entries"):
                if not daily_schedule.timetable_entries:
                    yield Static(
                        "Heute ist kein Unterricht geplant.",
                        classes="dashboard-empty",
                    )
                for entry in daily_schedule.timetable_entries:
                    yield DailyScheduleRow(
                        entry,
                        self.subjects_by_id,
                        self.sequences_by_key,
                    )

                if daily_schedule.additional_entries:
                    yield Static(
                        "WEITERE EINTRÄGE",
                        classes="daily-additional-heading",
                    )
                    for entry in daily_schedule.additional_entries:
                        yield DailyAdditionalRow(entry, self.subjects_by_id)

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
        current_datetime = datetime.now(ZoneInfo("Europe/Berlin"))
        if current_datetime.date() != self.dashboard.daily_schedule.date:
            if not self._refresh_requested:
                self._refresh_requested = True
                self.post_message(self.DashboardRefreshRequested())
            return

        position = get_current_timetable_position(self.periods, current_datetime)
        if position != self.current_time_position:
            self.current_time_position = position
            table = self.query_one("#schedule", DataTable)
            table.clear(columns=True)
            self.populate_timetable(*position)

        highlighted_occurrence = get_time_highlighted_occurrence(
            [
                entry.timetable_entry
                for entry in self.dashboard.daily_schedule.timetable_entries
            ],
            self.periods,
            current_datetime,
        )
        for row in self.query(DailyScheduleRow):
            row.set_class(
                row.occurrence == highlighted_occurrence,
                "time-highlighted",
            )

    def _get_sequence(self, planned_lesson: PlannedLesson) -> Sequence:
        return self.sequences_by_key[
            (
                planned_lesson.grade_level,
                planned_lesson.subject_id,
                planned_lesson.sequence_id,
            )
        ]

    def _format_planned_occurrence(self, planned_lesson: PlannedLesson) -> str:
        weekday = WEEKDAY_NAMES[planned_lesson.date.weekday()]
        occurrence = (
            f"{weekday}, {planned_lesson.date:%d.%m.%Y} · "
            f"{planned_lesson.period}. Stunde"
        )
        today = self.dashboard.daily_schedule.date
        if planned_lesson.date < today:
            days = (today - planned_lesson.date).days
            occurrence += f" · seit {days} Tag{'en' if days != 1 else ''} ausstehend"
        return occurrence

    @staticmethod
    def _format_school_year(school_year: str) -> str:
        start_year, end_year = school_year.split("-")
        return f"{start_year}/{end_year[-2:]}"

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
