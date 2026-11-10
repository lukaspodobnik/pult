import asyncio

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
