import asyncio
from datetime import datetime

from textual.app import App, ComposeResult
from textual.widgets import DataTable

from pult.progress.queries import get_home_dashboard_summary
from pult.views.home_view import HomeView
from pult.widgets.dashboard.daily_schedule import (
    DailySchedulePanel,
    DailyScheduleRow,
)
from pult.widgets.dashboard.next_lesson import NextLessonPanel
from pult.widgets.dashboard.school_year_progress import SchoolYearProgress
from pult.widgets.dashboard.timetable import TimetablePanel
from pult.widgets.lesson_progress_bar import LessonProgressBar


def test_dashboard_widgets_and_time_updates(
    monkeypatch,
    school_class,
    subject,
    sequences,
    empty_progress,
    school_calendar,
    timetable_entries,
    periods,
):
    class Clock:
        current = datetime(2026, 9, 7, 8, 10)

        @classmethod
        def now(cls, tz):
            return cls.current.replace(tzinfo=tz)

    monkeypatch.setattr("pult.views.home_view.datetime", Clock)
    dashboard = get_home_dashboard_summary(
        Clock.current,
        {school_class.id: empty_progress},
        sequences,
        timetable_entries,
        periods,
        [school_class],
        school_calendar,
        [],
        {school_class.id: []},
    )

    class DashboardApp(App):
        refresh_requests = 0

        def compose(self) -> ComposeResult:
            yield HomeView(timetable_entries, [subject], periods, sequences, dashboard)

        def on_home_view_dashboard_refresh_requested(self):
            self.refresh_requests += 1

    async def run():
        app = DashboardApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            view = app.query_one(HomeView)
            assert app.query_one(SchoolYearProgress).parent is view
            bar = app.query_one("#school-year-progress-bar", LessonProgressBar)
            assert bar.completed == dashboard.school_year_progress.elapsed_day_count
            assert (
                app.query_one(NextLessonPanel).planned_lesson
                == dashboard.next_planned_lesson
            )
            table = app.query_one(DataTable)
            assert table.parent is app.query_one(TimetablePanel)
            assert table.row_count == len(periods)
            assert not table.can_focus
            assert table.cursor_type == "none"
            assert [
                line.rstrip()
                for line in str(table.get_cell("1", "monday")).splitlines()
            ][:2] == ["5A · Ma", "101"]
            panel = app.query_one(TimetablePanel)
            current_style = panel.get_component_rich_style("timetable--current")
            row_style = panel.get_component_rich_style("timetable--period")
            assert current_style.bgcolor != row_style.bgcolor
            assert table.get_cell("1", "monday").style == current_style
            assert table.get_cell("1", "tuesday").style == row_style
            assert (
                not current_style.bold
                and not current_style.underline
                and not current_style.reverse
            )
            assert "1. Std." in str(table.ordered_rows[0].label)
            rows = list(app.query_one(DailySchedulePanel).query(DailyScheduleRow))
            assert [row.has_class("time-highlighted") for row in rows] == [True, False]

            Clock.current = datetime(2026, 9, 7, 8, 55)
            view.refresh_time_highlight()
            assert [row.has_class("time-highlighted") for row in rows] == [False, True]
            assert table.get_cell("2", "monday").style == current_style
            assert table.get_cell("1", "monday").style == row_style
            assert table.get_cell("1", "tuesday").style == ""
            view.refresh_time_highlight()
            assert table.row_count == len(periods)

            Clock.current = datetime(2026, 9, 8, 0, 1)
            view.refresh_time_highlight()
            view.refresh_time_highlight()
            await pilot.pause()
            assert app.refresh_requests == 1

    asyncio.run(run())
