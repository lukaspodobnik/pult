from datetime import datetime
from zoneinfo import ZoneInfo

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message

from schooltools_tui.curriculum.sequence import Sequence
from schooltools_tui.progress.queries import (
    HomeDashboardSummary,
)
from schooltools_tui.school.period import Period
from schooltools_tui.school.subject import Subject
from schooltools_tui.school.timetable import TimetableEntry
from schooltools_tui.widgets.dashboard.daily_schedule import DailySchedulePanel
from schooltools_tui.widgets.dashboard.next_lesson import NextLessonPanel
from schooltools_tui.widgets.dashboard.school_year_progress import SchoolYearProgress
from schooltools_tui.widgets.dashboard.timetable import TimetablePanel


class HomeView(VerticalScroll, can_focus=False):
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
        self.timetable_entries = timetable_entries
        self._refresh_requested = False
        self._updating = False

    async def update_data(
        self,
        timetable_entries: list[TimetableEntry],
        subjects: list[Subject],
        periods: list[Period],
        sequences: list[Sequence],
        dashboard: HomeDashboardSummary,
    ) -> None:
        """Reiche neue Daten an die bestehenden Dashboard-Widgets weiter."""
        subjects_by_id = {subject.id: subject for subject in subjects}
        sequences_by_key = {
            (sequence.grade_level, sequence.subject_id, sequence.id): sequence
            for sequence in sequences
        }
        if (
            self.timetable_entries == timetable_entries
            and self.subjects_by_id == subjects_by_id
            and self.periods == periods
            and self.sequences_by_key == sequences_by_key
            and self.dashboard == dashboard
        ):
            return
        self.timetable_entries = timetable_entries
        self.subjects_by_id = subjects_by_id
        self.periods = periods
        self.sequences_by_key = sequences_by_key
        self.dashboard = dashboard
        self._refresh_requested = False
        self._updating = True
        try:
            self.query_one(SchoolYearProgress).update_data(
                dashboard.school_year_progress
            )
            self.query_one(TimetablePanel).update_data(
                timetable_entries, subjects_by_id, periods
            )
            self.query_one(NextLessonPanel).update_data(
                dashboard.next_planned_lesson,
                dashboard.daily_schedule.date,
                subjects_by_id,
                sequences_by_key,
            )
            await self.query_one(DailySchedulePanel).update_data(
                dashboard.daily_schedule, subjects_by_id, sequences_by_key
            )
        finally:
            self._updating = False
        self.refresh_time_highlight()

    def compose(self) -> ComposeResult:
        yield SchoolYearProgress(self.dashboard.school_year_progress)
        with Horizontal(id="home-dashboard-content"):
            with Vertical(id="home-dashboard-left"):
                yield TimetablePanel(
                    self.timetable_entries, self.subjects_by_id, self.periods
                )
                yield NextLessonPanel(
                    self.dashboard.next_planned_lesson,
                    self.dashboard.daily_schedule.date,
                    self.subjects_by_id,
                    self.sequences_by_key,
                )
            yield DailySchedulePanel(
                self.dashboard.daily_schedule,
                self.subjects_by_id,
                self.sequences_by_key,
            )

    def on_mount(self) -> None:
        self.refresh_time_highlight()
        self.set_interval(30, self.refresh_time_highlight)

    def refresh_time_highlight(self) -> None:
        if self._updating or not self.display or self.app.screen is not self.screen:
            return
        current_datetime = datetime.now(ZoneInfo("Europe/Berlin"))
        if current_datetime.date() != self.dashboard.daily_schedule.date:
            if not self._refresh_requested:
                self._refresh_requested = True
                self.post_message(self.DashboardRefreshRequested())
            return

        self.query_one(TimetablePanel).refresh_time_highlight(current_datetime)
        self.query_one(DailySchedulePanel).refresh_time_highlight(
            self.periods, current_datetime
        )
