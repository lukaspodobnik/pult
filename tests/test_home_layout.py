import asyncio
from datetime import datetime, time

import pytest
from test_ui_integration import prepare_root
from textual.events import MouseScrollDown
from textual.widgets import DataTable, Header, Static

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
from pult.widgets.dashboard.next_lesson import NextLessonPanel
from pult.widgets.dashboard.timetable import TimetablePanel
from pult.widgets.navigation import ManagementPicker, TeachingPicker, ViewPicker


@pytest.mark.parametrize("size", [(206, 46), (180, 42), (241, 70)])
def test_dashboard_geometry_focus_and_overflow(tmp_path, monkeypatch, size):
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
        async with app.run_test(size=size) as pilot:
            await pilot.pause(0.4)
            for _ in range(40):
                if app.screen._pending_view_id is None:
                    break
                await pilot.pause(0.05)
            home = app.screen.query_one(HomeView)
            footer = app.screen.query_one("PultFooter")
            for _ in range(40):
                # Bei einem Footer-Neuaufbau existiert die Taste vor ihrem Layout.
                # Deshalb bei jedem Versuch das aktuelle Widget erneut abfragen.
                if footer.query(".quit-key"):
                    quit_key = footer.query_one(".quit-key")
                    if quit_key.region.width > 0 and quit_key.region.height > 0:
                        break
                await pilot.pause(0.05)
            else:
                pytest.fail("Die Beenden-Taste im Footer erhielt kein Layout.")
            quit_key = footer.query_one(".quit-key")
            assert quit_key.region.right == footer.region.right
            assert quit_key.key == "q"
            logo = app.screen.query_one("#app-logo")
            assert logo.region.height == 5
            assert logo.region.y == 0
            assert not app.screen.query(Header)
            assert not app.ENABLE_COMMAND_PALETTE
            assert home.query_one("#school-year-progress").region.height == 4
            assert home.query_one("#school-year-progress-bar").region.height == 1
            assert not logo.can_focus
            assert logo.region.bottom + 1 == app.screen.query_one(ViewPicker).region.y
            timetable = home.query_one(TimetablePanel)
            next_lesson = home.query_one(NextLessonPanel)
            daily = home.query_one(DailySchedulePanel)
            views = app.screen.query_one(ViewPicker)
            management = app.screen.query_one(ManagementPicker)
            teaching = app.screen.query_one(TeachingPicker)
            assert views.region.y == timetable.region.y
            assert teaching.region.bottom == timetable.region.bottom
            assert management.region.y == next_lesson.region.y
            assert management.region.bottom >= next_lesson.region.bottom
            assert teaching.region.bottom < management.region.y
            table = timetable.query_one(DataTable)
            assert [row.height for row in table.rows.values()] == [3] * (
                len(periods) - 1
            ) + [2]
            assert (
                str(table.get_cell(str(periods[0].number), "separator-1")) == "│\n│\n│"
            )
            assert timetable.region.height == min(27, size[1] - 17)
            assert table.max_scroll_y > 0
            assert table.header_height == 2
            assert "─" in str(
                table.columns[
                    next(k for k in table.columns if k.value == "monday")
                ].label
            )
            assert "│" in str(table.get_cell("1", "separator-0"))
            separator_key = next(k for k in table.columns if k.value == "separator-0")
            assert str(table.columns[separator_key].label) == "│\n┼"
            assert str(table.ordered_columns[0].label) == "\n" + "─" * 12
            assert "08:00–08:45" in str(table.ordered_rows[0].label)
            assert timetable.region.x == next_lesson.region.x
            assert timetable.region.width == next_lesson.region.width
            assert next_lesson.region.y > timetable.region.bottom
            assert daily.region.y == timetable.region.y
            assert daily.region.bottom == next_lesson.region.bottom
            assert daily.region.x >= timetable.region.right
            for widget in (
                home,
                next_lesson,
            ):
                assert widget.max_scroll_y == 0, (
                    type(widget).__name__,
                    widget.region,
                    widget.virtual_size,
                )
                assert widget.max_scroll_x == 0
            assert set(app.screen.focus_chain) == {
                app.screen.query_one(ViewPicker),
                app.screen.query_one(ManagementPicker),
                teaching,
            }
            await pilot.press("tab")
            assert isinstance(app.focused, TeachingPicker)
            await pilot.press("tab")
            assert isinstance(app.focused, ManagementPicker)
            await pilot.pause()
            assert management.styles.border.top[0] == "round"
            assert views.styles.border.top[0] == "round"
            assert management.styles.border.top[1] != views.styles.border.top[1]
            assert management.styles.background_tint.a == 0
            assert views.styles.background_tint.a == 0
            await pilot.press("tab")
            assert isinstance(app.focused, ViewPicker)
            await pilot.press("shift+tab")
            assert isinstance(app.focused, ManagementPicker)
            title = next_lesson.query_one(".next-lesson-name", Static)
            long_title = "Ein sehr langer Stundentitel mit vielen Wörtern " * 20
            title.update(long_title)
            await pilot.pause()
            assert title.region.height > 2
            assert not next_lesson.query(".next-lesson-material")
            assert title.content == long_title
            app.save_screenshot("home.svg", path=str(tmp_path))
            next_lesson.query_one(".next-lesson-tasks").update("Aufgabe\n" * 100)
            next_lesson.query_one(".next-lesson-tasks").display = True
            await pilot.pause()
            assert next_lesson.max_scroll_y > 0
            assert next_lesson not in app.screen.focus_chain
            next_lesson.post_message(
                MouseScrollDown(next_lesson, 1, 1, 0, 0, 0, False, False, False)
            )
            await pilot.pause(0.2)
            assert next_lesson.scroll_y > 0
            assert isinstance(app.focused, ManagementPicker)
            timetable.refresh_time_highlight(datetime(2026, 9, 14, 16, 30))
            await pilot.pause()
            assert table.scroll_y > 0
            table.scroll_home(animate=False)
            timetable.refresh_time_highlight(datetime(2026, 9, 14, 16, 31))
            await pilot.pause()
            assert table.scroll_y == 0
            timetable.update_data([], home.subjects_by_id, periods)
            app.screen.align_dashboard()
            await pilot.pause()
            assert table.row_count == 8
            if size[1] >= 44:
                assert table.max_scroll_y == 0
            await pilot.resize_terminal(100, 30)
            await pilot.pause()
            assert home.max_scroll_y > 0
            assert home.max_scroll_x > 0
            # Das Layout bleibt auch im kleinen Fenster nebeneinander angeordnet.
            assert daily.region.x >= timetable.region.right

    asyncio.run(run())


@pytest.mark.parametrize('hour, minute, expected', [(7, 50, None), (8, 0, 1), (8, 45, 2), (8, 50, 2), (9, 0, 2), (9, 45, None)])
def test_timetable_highlights_next_period_during_break(hour, minute, expected):
    from pult.school.period import Period
    from pult.widgets.dashboard.timetable import get_current_timetable_position

    periods = [Period(1, time(8), time(8, 45)), Period(2, time(9), time(9, 45))]
    assert get_current_timetable_position(periods, datetime(2026, 9, 14, hour, minute)) == ('monday', expected)
    assert get_current_timetable_position(periods, datetime(2026, 9, 13, hour, minute)) == (None, None)


def test_home_periods_expand_only_for_scheduled_late_lessons(tmp_path):
    from pult.widgets.dashboard.timetable import displayed_periods

    config = prepare_root(tmp_path)
    periods = load_periods(config.root)
    assert [p.number for p in periods] == list(range(1, 12))
    assert len(displayed_periods(periods, [])) == 8
    for number in (9, 10, 11):
        assert len(displayed_periods(periods, [TimetableEntry('monday', number, '5A', 'mathematik', '')])) == number
