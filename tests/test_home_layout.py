import asyncio
from datetime import datetime, time

import pytest
from test_ui_integration import prepare_root
from textual.widgets import DataTable

from pult.app import PultApp
from pult.school.calendar import load_school_calendar
from pult.school.period import load_periods
from pult.school.timetable import (
    TimetableEntry,
    get_timetable_path,
    save_timetable,
)
from pult.views.home_view import HomeView
from pult.widgets.dashboard.daily_schedule import DailySchedulePanel
from pult.widgets.dashboard.timetable import TimetablePanel
from pult.widgets.navigation import ManagementPicker, TeachingPicker, ViewPicker


def test_dashboard_content_and_keyboard_navigation(tmp_path, monkeypatch):
    config = prepare_root(tmp_path)
    periods = load_periods(tmp_path)
    first_day = load_school_calendar(
        tmp_path, config.active_school_year
    ).first_school_day

    class Clock:
        @classmethod
        def now(cls, tz):
            return datetime.combine(first_day, time(8, 10), tzinfo=tz)

    monkeypatch.setattr("pult.app.load_app_config", lambda: config)
    monkeypatch.setattr("pult.screens.main_screen.datetime", Clock)
    monkeypatch.setattr("pult.views.home_view.datetime", Clock)
    save_timetable(
        get_timetable_path(tmp_path, config.active_school_year),
        [
            TimetableEntry(day, p.number, "5A", "mathematik", "101")
            for day in ("monday", "tuesday", "wednesday", "thursday", "friday")
            for p in periods
        ],
    )

    async def run():
        app = PultApp()
        async with app.run_test(size=(160, 45)) as pilot:
            await pilot.pause()
            await pilot.wait_for_scheduled_animations()
            home = app.screen.query_one(HomeView)
            table = home.query_one(TimetablePanel).query_one(DataTable)
            assert table.row_count == len(periods)
            assert "5A" in str(table.get_cell("1", "monday"))
            assert home.query_one(DailySchedulePanel)
            await pilot.press("tab")
            assert isinstance(app.focused, TeachingPicker)
            await pilot.press("tab")
            assert isinstance(app.focused, ManagementPicker)
            await pilot.press("tab")
            assert isinstance(app.focused, ViewPicker)

    asyncio.run(run())


@pytest.mark.parametrize(
    "hour, minute, expected",
    [(7, 50, None), (8, 0, 1), (8, 45, 2), (8, 50, 2), (9, 0, 2), (9, 45, None)],
)
def test_timetable_highlights_next_period_during_break(hour, minute, expected):
    from pult.school.period import Period
    from pult.widgets.dashboard.timetable import get_current_timetable_position

    periods = [Period(1, time(8), time(8, 45)), Period(2, time(9), time(9, 45))]
    assert get_current_timetable_position(
        periods, datetime(2026, 9, 14, hour, minute)
    ) == ("monday", expected)
    assert get_current_timetable_position(
        periods, datetime(2026, 9, 13, hour, minute)
    ) == (None, None)


def test_home_periods_expand_only_for_scheduled_late_lessons(tmp_path):
    from pult.widgets.dashboard.timetable import displayed_periods

    config = prepare_root(tmp_path)
    periods = load_periods(config.root)
    assert [p.number for p in periods] == list(range(1, 12))
    assert len(displayed_periods(periods, [])) == 6
    for number in (7, 8, 9, 10, 11):
        assert (
            len(
                displayed_periods(
                    periods, [TimetableEntry("monday", number, "5A", "mathematik", "")]
                )
            )
            == number
        )
