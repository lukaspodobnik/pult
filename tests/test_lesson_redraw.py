import asyncio

import pytest
from test_lesson_cache import (
    RecordingRenderer,
    ready,
    setup_lessons,
    until,
    visible_document,
)

from pult.app import PultApp
from pult.curriculum.material import Task, TaskMetadata, save_task
from pult.screens.teaching.lesson_screen import LessonScreen
from pult.screens.teaching.task_screen import TaskScreen
from pult.widgets.document_viewer import DocumentViewer
from pult.widgets.scrolling import Vertical


def prepare_lesson(tmp_path, monkeypatch):
    root = tmp_path / "unterricht"
    root.mkdir()
    _, sequence = setup_lessons(root, monkeypatch)
    directory = root / "sequences/5/mathematik/cache-example"
    save_task(
        directory,
        Task("exercise", "Aufgabe", metadata=TaskMetadata("Aufgabe", ["K1"], "I")),
    )
    return root, sequence


@pytest.mark.parametrize("planning", [False, True])
def test_return_resends_existing_images_and_preserves_document(
    tmp_path, monkeypatch, logging_session, planning
):
    from textual_image._terminal import CellSize, get_cell_size
    from textual_image.renderable import tgp
    from textual_image.widget import TGPImage

    root, sequence = prepare_lesson(tmp_path, monkeypatch)
    monkeypatch.setattr("pult.services.documents.material_rendering.GRAPHICS", TGPImage)
    monkeypatch.setattr(get_cell_size, "_result", CellSize(10, 20), raising=False)
    # Exercise the real image widget and protocol encoder, without terminal I/O.
    # Only image availability is modeled; no lesson content leaves the process.
    live_images = set()

    def terminal_message(**message):
        if message.get("payload") and message.get("m") == 0:
            live_images.add(message["i"])

    monkeypatch.setattr(tgp, "_send_tgp_message", terminal_message)

    def data_files():
        return {
            path.relative_to(root): (path.read_bytes(), path.stat().st_mtime_ns)
            for path in root.rglob("*")
            if path.is_file()
        }

    async def run():
        app = PultApp()
        renderer = RecordingRenderer(tmp_path)
        app.document_renderer = renderer
        async with app.run_test(size=(179, 45)) as pilot:
            await pilot.pause()
            screen = LessonScreen(sequence, "lesson-3")
            await app.push_screen(screen)
            await until(lambda: ready(screen, "lesson-3"))
            if planning:
                screen.action_toggle_material()
                await until(lambda: ready(screen, "lesson-3"))
            # Load the task screen's styles before taking the snapshot.
            screen.action_open_tasks()
            await pilot.pause()
            await pilot.press("escape")
            await until(lambda: app.screen is screen)
            await pilot.pause()
            viewer = visible_document(screen)
            pane = viewer.parent
            pane.scroll_to(y=7, animate=False, immediate=True)
            await pilot.pause()
            assert pane.scroll_y == 7
            tiles = [tile for tile, _ in viewer.image_tiles]
            assert tiles and all(tile._renderable is not None for tile in tiles)
            signature = viewer.rendered_signature
            cache_path = viewer._cache_path
            data_before = data_files()
            current_key = ("lesson-3", planning)
            renders_before = sum(call[0] == current_key for call in renderer.calls)

            screen.action_open_tasks()
            await pilot.pause()
            assert isinstance(app.screen, TaskScreen)
            # The terminal no longer has the lesson's images, while PULT still
            # has the cached widgets and considers the document fully rendered.
            live_images.clear()
            await pilot.press("escape")
            await until(lambda: app.screen is screen)
            await pilot.pause()

            assert visible_document(screen) is viewer
            assert [tile for tile, _ in viewer.image_tiles] == tiles
            assert viewer.rendered_signature == viewer.signature == signature
            assert viewer._cache_path == cache_path
            assert pane.scroll_y == 7
            assert screen.lesson_id == "lesson-3"
            assert screen.show_planning is planning
            assert (
                sum(call[0] == current_key for call in renderer.calls) == renders_before
            )
            assert data_files() == data_before
            assert all(
                tile._renderable.terminal_image_id in live_images for tile in tiles
            )
            # Unchanged clock checks must not keep retransmitting the images.
            ids = [tile._renderable.terminal_image_id for tile in tiles]
            for _ in range(3):
                viewer.schedule_render()
                await pilot.pause()
            assert [tile._renderable.terminal_image_id for tile in tiles] == ids

    asyncio.run(run())


@pytest.mark.parametrize("stage", ["render", "mount"])
def test_closing_tasks_cancels_render_before_resuming_lesson(
    tmp_path, monkeypatch, logging_session, stage
):
    _, sequence = prepare_lesson(tmp_path, monkeypatch)

    async def run():
        app = PultApp()
        renderer = RecordingRenderer(tmp_path)
        app.document_renderer = renderer
        started, cancelled = asyncio.Event(), asyncio.Event()
        if stage == "render":
            renderer.block = ("exercise", False)
            started, cancelled = renderer.started, renderer.cancelled
        else:
            mount = Vertical.mount

            def mount_until_closed(body, *children, **kwargs):
                result = mount(body, *children, **kwargs)
                if (
                    body.id != "document-body"
                    or not isinstance(body.parent, DocumentViewer)
                    or body.parent.path.parent.name != "exercise"
                    or not children
                    or not all(child.has_class("document-tile") for child in children)
                ):
                    return result

                async def wait_for_close():
                    await result
                    started.set()
                    try:
                        await asyncio.Event().wait()
                    finally:
                        cancelled.set()

                return wait_for_close()

            monkeypatch.setattr(Vertical, "mount", mount_until_closed)
        async with app.run_test(size=(179, 45)) as pilot:
            await pilot.pause()
            screen = LessonScreen(sequence, "lesson-3")
            await app.push_screen(screen)
            await until(lambda: ready(screen, "lesson-3"))
            screen.action_open_tasks()
            await asyncio.wait_for(started.wait(), 5)
            tasks = app.screen
            assert isinstance(tasks, TaskScreen)
            viewer = tasks.query_one(DocumentViewer)
            workers = [worker for worker in app.workers if worker.node is viewer]
            assert workers and any(worker.is_running for worker in workers)
            dismiss = tasks.dismiss

            def dismiss_after_cancellation(result):
                # Textual also cancels on unmount, but that is too late: the
                # lesson resumes before the old screen finishes being removed.
                assert not viewer.display
                assert all(worker.is_cancelled for worker in workers)
                return dismiss(result)

            monkeypatch.setattr(tasks, "dismiss", dismiss_after_cancellation)
            await pilot.press("escape")
            await until(lambda: app.screen is screen)
            await asyncio.wait_for(cancelled.wait(), 5)
            await pilot.pause()
            text = logging_session.path.read_text()
            assert f"render_cancelled viewer={viewer.diagnostic_id}" in text
            assert f"viewer_updated viewer={viewer.diagnostic_id}" not in text
            assert ready(screen, "lesson-3")
            assert " ERROR " not in text

    asyncio.run(run())
