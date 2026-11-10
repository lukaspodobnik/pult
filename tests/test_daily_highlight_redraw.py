import asyncio
from datetime import datetime, time

import pytest
from test_lesson_cache import until
from test_ui_integration import prepare_root
from textual.widget import Widget

from pult.app import PultApp
from pult.school.calendar import load_school_calendar
from pult.school.period import load_periods
from pult.school.timetable import TimetableEntry, get_timetable_path, save_timetable
from pult.screens.base_screen import PultScreen
from pult.widgets.dashboard.daily_schedule import DailySchedulePanel, DailyScheduleRow
from pult.widgets.navigation import ViewPicker


@pytest.fixture
def dashboard(tmp_path, monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    root = tmp_path / "unterricht"
    root.mkdir()
    config = prepare_root(root)
    first_day = load_school_calendar(root, config.active_school_year).first_school_day

    class Clock:
        current = time(8, 10)

        @classmethod
        def now(cls, tz):
            return datetime.combine(first_day, cls.current, tzinfo=tz)

    monkeypatch.setattr("pult.app.load_app_config", lambda: config)
    monkeypatch.setattr("pult.services.dashboard.datetime", Clock)
    monkeypatch.setattr("pult.views.home_view.datetime", Clock)
    save_timetable(
        get_timetable_path(root, config.active_school_year),
        [
            TimetableEntry(day, period, "5A", "mathematik", "101")
            for day in ("monday", "tuesday", "wednesday", "thursday", "friday")
            for period in (1, 2)
        ],
    )
    return config, Clock


def data_files(root):
    return {
        str(path.relative_to(root)): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in root.rglob("*")
        if path.is_file()
    }


def assert_background(row):
    expected = row.background_colors[1].rich_color
    checked = 0
    for widget in row.walk_children(Widget):
        if not widget.display or not widget.size:
            continue
        # render_lines liest die vorhandenen Zeichen-Caches; kein refresh().
        for strip in widget.render_lines(widget.size.region):
            for segment in strip:
                if segment.text and not segment.control:
                    assert segment.style is not None
                    assert segment.style.bgcolor == expected, widget
                    checked += 1
    assert checked


def test_startup_and_highlight_change_keep_backgrounds_consistent(
    dashboard, logging_session
):
    config, clock = dashboard
    before = data_files(config.root)

    async def run():
        # Korrektur muss auch ohne --debug aktiv sein.
        async with PultApp().run_test(size=(179, 45)) as pilot:
            await pilot.pause()
            await pilot.wait_for_scheduled_animations()
            await pilot.pause()
            panel = pilot.app.screen.query_one(DailySchedulePanel)
            rows = list(panel.query(DailyScheduleRow))
            assert [row.has_class("time-highlighted") for row in rows] == [True, False]
            for row in rows:
                assert_background(row)
            text = logging_session.path.read_text()
            assert (
                sum(
                    "daily_row_redraw_requested" in line
                    and "reason=startup_finished" in line
                    for line in text.splitlines()
                )
                == 2
            )
            redraws = text.count("daily_row_redraw_requested")
            for _ in range(3):
                panel.refresh_time_highlight(load_periods(config.root), clock.now(None))
                await pilot.pause()
            assert (
                logging_session.path.read_text().count("daily_row_redraw_requested")
                == redraws
            )

            clock.current = load_periods(config.root)[1].start
            panel.refresh_time_highlight(load_periods(config.root), clock.now(None))
            await pilot.pause()
            assert [row.has_class("time-highlighted") for row in rows] == [False, True]
            for row in rows:
                assert_background(row)
            assert logging_session.path.read_text().count("reason=highlight_clock") == 2
            assert list(panel.query(DailyScheduleRow)) == rows

    asyncio.run(run())
    assert data_files(config.root) == before


@pytest.mark.parametrize("destination", ["class", "screen"])
def test_return_keeps_backgrounds_consistent_without_replacing_rows(
    dashboard, destination
):
    config, _ = dashboard
    before = data_files(config.root)

    async def run():
        app = PultApp()
        async with app.run_test(size=(179, 45)) as pilot:
            await pilot.pause()
            await pilot.wait_for_scheduled_animations()
            await pilot.pause()
            main = app.screen
            panel = main.query_one(DailySchedulePanel)
            rows = list(panel.query(DailyScheduleRow))
            picker = main.query_one(ViewPicker)
            if destination == "class":
                picker.highlighted = 1
                await until(
                    lambda: (
                        main.active_school_class_id == "5A"
                        and main._pending_view_id is None
                    )
                )
                await pilot.pause()
                assert main.active_school_class_id == "5A"
            else:
                await app.push_screen(PultScreen())
                await pilot.pause()

            if destination == "class":
                picker.highlighted = picker.get_option_index("home")
                await until(
                    lambda: (
                        main.active_school_class_id is None
                        and main._pending_view_id is None
                    )
                )
            else:
                app.pop_screen()
            await pilot.pause()
            assert app.screen is main
            assert main.active_school_class_id is None
            assert list(panel.query(DailyScheduleRow)) == rows
            for row in rows:
                assert_background(row)

    asyncio.run(run())
    assert data_files(config.root) == before
