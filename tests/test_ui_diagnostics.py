import asyncio
from datetime import datetime, time

import pytest
from test_document_cache import mock_browser, render
from test_lesson_cache import RecordingRenderer, ready, setup_lessons, until
from textual import work
from textual.worker import WorkerFailed

from pult.app import PultApp
from pult.screens.base_screen import PultScreen
from pult.screens.teaching.lesson_screen import LessonScreen
from pult.services.diagnostics import operation
from pult.services.documents.document_rendering import DocumentRenderer


def test_textual_ui_failure_is_logged_once(logging_session):
    class BrokenApp(PultApp):
        CSS_PATH = []

        def on_mount(self, event):
            event.prevent_default()
            raise RuntimeError("PRIVATE_UI_TEXT")

    async def run():
        async with BrokenApp().run_test() as pilot:
            await pilot.pause()

    with pytest.raises(RuntimeError):
        asyncio.run(run())
    text = logging_session.path.read_text()
    assert text.count("ui_failed") == 1
    assert "RuntimeError" in text
    assert "on_mount" in text
    assert "PRIVATE_UI_TEXT" not in text


def test_fatal_worker_preserves_original_stack(logging_session):
    class BrokenApp(PultApp):
        CSS_PATH = []

        def on_mount(self, event):
            event.prevent_default()
            self.broken_work()

        @work
        async def broken_work(self):
            raise ValueError("PRIVATE_WORKER_TEXT")

    async def run():
        async with BrokenApp().run_test() as pilot:
            await pilot.pause()

    with pytest.raises(WorkerFailed):
        asyncio.run(run())
    text = logging_session.path.read_text()
    assert text.count("ui_failed") == 1
    assert "ValueError" in text
    assert "broken_work" in text
    assert "PRIVATE_WORKER_TEXT" not in text


def test_nonfatal_screen_worker_and_cancellation(logging_session):
    class WorkerScreen(PultScreen):
        @work(exit_on_error=False)
        async def broken_work(self):
            raise RuntimeError("PRIVATE_BACKGROUND_TEXT")

        @work(group="waiting")
        async def waiting_work(self):
            await asyncio.Event().wait()

    class WorkerApp(PultApp):
        CSS_PATH = []

        def on_mount(self, event):
            event.prevent_default()
            self.push_screen(WorkerScreen())

    async def run():
        app = WorkerApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            screen.broken_work()
            await until(
                lambda: "background_worker_failed" in logging_session.path.read_text()
            )
            worker = screen.waiting_work()
            await pilot.pause()
            worker.cancel()
            await until(lambda: "worker_cancelled" in logging_session.path.read_text())
            assert app.is_running

    asyncio.run(run())
    text = logging_session.path.read_text()
    assert text.count("background_worker_failed") == 1
    assert "PRIVATE_BACKGROUND_TEXT" not in text
    assert len([line for line in text.splitlines() if " ERROR " in line]) == 1


def test_lesson_roundtrip_and_cancel_have_traceable_events(
    tmp_path, monkeypatch, logging_session
):
    _, sequence = setup_lessons(tmp_path, monkeypatch)

    async def run():
        app = PultApp()
        renderer = RecordingRenderer(tmp_path)
        app.document_renderer = renderer
        async with app.run_test(size=(160, 46)) as pilot:
            await pilot.pause()
            screen = LessonScreen(sequence, "lesson-3")
            await app.push_screen(screen)
            await until(lambda: ready(screen, "lesson-3"))
            screen.action_open_tasks()
            await pilot.pause()
            await pilot.press("escape")
            await until(lambda: app.screen is screen)
            renderer.block = ("lesson-6", False)
            renderer.started.clear()
            screen.query_one("#lesson-list").highlighted = 6
            await asyncio.wait_for(renderer.started.wait(), 5)
            screen.query_one("#lesson-list").highlighted = 3
            await until(lambda: ready(screen, "lesson-3"))
            await until(lambda: "render_cancelled" in logging_session.path.read_text())

    asyncio.run(run())
    text = logging_session.path.read_text()
    for event in (
        "task_library_opened",
        "task_library_closed",
        "lesson_screen_resumed",
        "lesson_selected",
        "viewer_updated",
    ):
        assert event in text
    starts = [line for line in text.splitlines() if " render_started " in line]
    for line in starts:
        assert "request=render-" in line and "viewer=viewer-" in line
    assert "Vorbereitung 3" not in text
    assert " ERROR " not in text


def test_renderer_cache_events_share_operation(tmp_path, monkeypatch, logging_session):
    async def run():
        renderer = DocumentRenderer(tmp_path / "cache")
        mock_browser(renderer, monkeypatch)
        with operation("render") as request:
            await render(renderer, "PRIVATE_DOCUMENT", tmp_path)
            await render(renderer, "PRIVATE_DOCUMENT", tmp_path)
            return request

    request = asyncio.run(run())
    text = logging_session.path.read_text()
    for event in (
        "document_cache_miss",
        "document_cache_written",
        "document_cache_hit",
    ):
        lines = [line for line in text.splitlines() if event in line]
        assert len(lines) == 1 and f"request={request} " in lines[0]
    assert "PRIVATE_DOCUMENT" not in text


def test_highlight_only_logs_changes(logging_session):
    from textual.app import App

    from pult.progress.queries import DailyTimetableEntry
    from pult.school.subject import Subject
    from pult.school.timetable import TimetableEntry
    from pult.widgets.dashboard.daily_schedule import DailyScheduleRow

    subject = Subject("mathematik", "Mathematik", "Ma", [5])
    entry = DailyTimetableEntry(
        timetable_entry=TimetableEntry("monday", 1, "5A", subject.id, "101"),
        grade_level=5,
        log_entry=None,
        planned_lesson=None,
        is_time_highlighted=False,
    )

    class RowApp(App):
        def compose(self):
            yield DailyScheduleRow(entry, {subject.id: subject}, {})

    async def run():
        async with RowApp().run_test() as pilot:
            row = pilot.app.query_one(DailyScheduleRow)
            for _ in range(5):
                row.set_time_highlight(True, reason="clock")
                await pilot.pause()
            assert row.has_class("time-highlighted")
            row.set_time_highlight(False, reason="clock")
            await pilot.pause()
            assert not row.has_class("time-highlighted")

    asyncio.run(run())
    text = logging_session.path.read_text()
    assert text.count("daily_highlight_changed") == 2
    assert text.count("daily_highlight_layout") == 2


@pytest.mark.parametrize("debug", [False, True])
def test_daily_redraw_key_repaints_without_data_changes(
    tmp_path, monkeypatch, logging_session, debug
):
    from test_ui_integration import prepare_root
    from textual.widgets import Static

    from pult.school.calendar import load_school_calendar
    from pult.school.timetable import TimetableEntry, get_timetable_path, save_timetable
    from pult.screens.common.binding_help_screen import binding_help_rows
    from pult.widgets.dashboard.daily_schedule import (
        DailySchedulePanel,
        DailyScheduleRow,
    )
    from pult.widgets.navigation import ViewPicker

    root = tmp_path / "unterricht"
    root.mkdir()
    config = prepare_root(root)
    first_day = load_school_calendar(root, config.active_school_year).first_school_day

    class Clock:
        @classmethod
        def now(cls, tz):
            return datetime.combine(first_day, time(8, 10), tzinfo=tz)

    monkeypatch.setattr("pult.app.load_app_config", lambda: config)
    monkeypatch.setattr("pult.services.dashboard.datetime", Clock)
    monkeypatch.setattr("pult.views.home_view.datetime", Clock)
    save_timetable(
        get_timetable_path(root, config.active_school_year),
        [
            TimetableEntry(day, 1, "5A", "mathematik", "101")
            for day in ("monday", "tuesday", "wednesday", "thursday", "friday")
        ],
    )

    def data_files():
        return {
            str(path.relative_to(root)): (path.read_bytes(), path.stat().st_mtime_ns)
            for path in root.rglob("*")
            if path.is_file()
        }

    async def run():
        app = PultApp(diagnostic_mode=debug)
        async with app.run_test(size=(179, 45)) as pilot:
            await pilot.pause()
            await pilot.wait_for_scheduled_animations()
            screen = app.screen
            panel = screen.query_one(DailySchedulePanel)
            row = panel.query_one(DailyScheduleRow)
            assert row.has_class("time-highlighted")
            assert ("ctrl+r" in screen.active_bindings) is debug
            assert (
                any(
                    "Diagnose: Neuzeichnen" == description
                    for _, description, _ in binding_help_rows(screen)
                )
                is debug
            )
            widgets = list(row.walk_children(with_self=True))
            rendered = set()
            expected = []
            for widget in widgets:
                if not isinstance(widget, Static) or not widget.display:
                    continue
                expected.append(widget)

                def render(widget=widget, original=widget.render):
                    rendered.add(widget)
                    return original()

                monkeypatch.setattr(widget, "render", render)

            def forbidden(*args, **kwargs):
                pytest.fail("Redraw must not reload dashboard data or save progress")

            before = data_files()
            focus = app.focused
            entry = row.daily_entry
            with monkeypatch.context() as guard:
                guard.setattr("pult.screens.main_screen.load_home_view_data", forbidden)
                guard.setattr(
                    "pult.screens.main_screen.save_class_progress_data", forbidden
                )
                await pilot.press("ctrl+r")
                await pilot.pause()

            assert data_files() == before
            assert app.focused is focus
            assert row.daily_entry is entry
            assert list(row.walk_children(with_self=True)) == widgets
            assert row.has_class("time-highlighted")
            text = logging_session.path.read_text()
            if debug:
                assert expected and set(expected) <= rendered
                assert text.count("daily_redraw_requested") == 1
                request_line = next(
                    line
                    for line in text.splitlines()
                    if "daily_redraw_requested" in line
                )
                redraw = request_line.split("redraw=")[1].split()[0]
                states = [
                    line
                    for line in text.splitlines()
                    if f"daily_redraw_state redraw={redraw}" in line
                ]
                assert any("phase=before" in line for line in states)
                assert any("phase=after" in line for line in states)
                assert all("highlighted=True" in line for line in states)
                assert all(
                    "background=" in line and "region=" in line for line in states
                )
                for widget in expected:
                    content = str(widget.content)
                    if len(content) > 10:
                        assert content not in "\n".join(states)
            else:
                assert "daily_redraw_" not in text

            # Die Taste darf auch keinen verdeckten HomeView aktualisieren.
            screen.query_one(ViewPicker).highlighted = 1
            await until(lambda: screen.active_school_class_id == "5A")
            await pilot.pause()
            assert "ctrl+r" not in screen.active_bindings
            await pilot.press("ctrl+r")
            await app.push_screen(PultScreen())
            await pilot.pause()
            assert "ctrl+r" not in app.screen.active_bindings
            await pilot.press("ctrl+r")
            await pilot.pause()
            assert logging_session.path.read_text().count(
                "daily_redraw_requested"
            ) == int(debug)
            assert data_files() == before

    asyncio.run(run())
