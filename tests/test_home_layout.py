import asyncio
from datetime import datetime, time

import pytest
from test_ui_integration import prepare_root
from textual.events import MouseScrollDown
from textual.widgets import DataTable, Header

from schooltools_tui.app import SchooltoolsApp
from schooltools_tui.school.calendar import load_school_calendar
from schooltools_tui.school.period import load_periods
from schooltools_tui.school.timetable import (
    TimetableEntry,
    get_timetable_path,
    save_timetable,
)
from schooltools_tui.views.home_view import HomeView
from schooltools_tui.widgets.capped_text import CappedText
from schooltools_tui.widgets.dashboard.daily_schedule import DailySchedulePanel
from schooltools_tui.widgets.dashboard.next_lesson import NextLessonPanel
from schooltools_tui.widgets.dashboard.timetable import TimetablePanel
from schooltools_tui.widgets.navigation import ManagementPicker, ViewPicker


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

    monkeypatch.setattr("schooltools_tui.app.load_app_config", lambda: config)
    monkeypatch.setattr("schooltools_tui.screens.main_screen.datetime", Clock)
    monkeypatch.setattr("schooltools_tui.views.home_view.datetime", Clock)
    save_timetable(
        get_timetable_path(tmp_path, config.active_school_year),
        [
            TimetableEntry(day, p.number, "5A", "mathematik", "101")
            for day in ("monday", "tuesday", "wednesday", "thursday", "friday")
            for p in periods
        ],
    )

    async def run():
        app = SchooltoolsApp()
        async with app.run_test(size=size) as pilot:
            await pilot.pause(0.4)
            for _ in range(40):
                if app.screen._pending_view_id is None:
                    break
                await pilot.pause(0.05)
            home = app.screen.query_one(HomeView)
            footer = app.screen.query_one("SchooltoolsFooter")
            for _ in range(40):
                if footer.query(".quit-key"):
                    break
                await pilot.pause(0.05)
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
            assert (
                logo.region.bottom + 1 == app.screen.query_one(ViewPicker).region.y
            )
            timetable = home.query_one(TimetablePanel)
            next_lesson = home.query_one(NextLessonPanel)
            daily = home.query_one(DailySchedulePanel)
            views = app.screen.query_one(ViewPicker)
            management = app.screen.query_one(ManagementPicker)
            assert (views.region.y, views.region.height) == (
                timetable.region.y,
                timetable.region.height,
            )
            assert (management.region.y, management.region.height) == (
                next_lesson.region.y,
                next_lesson.region.height,
            )
            table = timetable.query_one(DataTable)
            assert [row.height for row in table.rows.values()] == [3] * (
                len(periods) - 2
            ) + [2, 2]
            assert (
                str(table.get_cell(str(periods[0].number), "separator-1")) == "│\n│\n│"
            )
            assert timetable.region.height == len(periods) * 3 + 2
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
                timetable.query_one(DataTable),
                daily.query_one("#daily-schedule-entries"),
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
            }
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
            title = next_lesson.query_one(".next-lesson-name", CappedText)
            long_title = "Ein sehr langer Stundentitel mit vielen Wörtern " * 20
            title.update(long_title)
            await pilot.pause()
            assert title.render().plain.endswith("…")
            assert title.render().plain.count("\n") <= 1
            assert title.content == long_title
            app.save_screenshot("home.svg", path=str(tmp_path))
            next_lesson.query_one(".next-lesson-notes").update("Notizen\n" * 100)
            next_lesson.query_one(".next-lesson-notes").display = True
            await pilot.pause()
            assert next_lesson.max_scroll_y > 0
            assert next_lesson not in app.screen.focus_chain
            next_lesson.post_message(
                MouseScrollDown(next_lesson, 1, 1, 0, 0, 0, False, False, False)
            )
            await pilot.pause(0.2)
            assert next_lesson.scroll_y > 0
            assert isinstance(app.focused, ManagementPicker)
            await pilot.resize_terminal(100, 30)
            await pilot.pause()
            assert home.max_scroll_y > 0
            assert home.max_scroll_x > 0
            # Das Layout bleibt auch im kleinen Fenster nebeneinander angeordnet.
            assert daily.region.x >= timetable.region.right

    asyncio.run(run())
