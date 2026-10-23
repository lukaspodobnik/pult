import asyncio
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from PIL import Image
from PIL.PngImagePlugin import PngInfo
from test_ui_integration import prepare_root
from textual.widgets import Static

from pult.app import PultApp
from pult.curriculum.material import Lesson, Phase
from pult.curriculum.sequence import Sequence, save_sequence
from pult.screens.teaching.lesson_screen import LessonScreen
from pult.services.documents.document_rendering import SEPARATOR_Y, DocumentRenderer
from pult.widgets.document_viewer import DocumentViewer


async def until(predicate):
    async def wait():
        while not predicate():
            await asyncio.sleep(0.01)

    await asyncio.wait_for(wait(), 5)


class Tile(Static):
    def __init__(self, image, **kwargs):
        super().__init__("", **kwargs)
        self.image = image


class RecordingRenderer:
    generation = 0

    def __init__(self, directory):
        self.directory = directory
        self.calls = []
        self.block = None
        self.started = asyncio.Event()
        self.cancelled = asyncio.Event()

    async def render(
        self, source, path, directory, width, font_size, *colors, **kwargs
    ):
        key = (path.parent.name, kwargs.get("planning") is not None)
        self.calls.append((key, width, colors, kwargs["font"]))
        if key == self.block:
            self.started.set()
            try:
                await asyncio.Event().wait()
            finally:
                self.cancelled.set()
        target = self.directory / f"render-{len(self.calls)}.png"
        metadata = PngInfo()
        metadata.add_text(SEPARATOR_Y, "800")
        Image.new("RGB", (width, 1600), colors[0]).save(target, pnginfo=metadata)
        return target

    async def close(self):
        pass


def setup_lessons(tmp_path, monkeypatch):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)
    monkeypatch.setattr("pult.services.documents.material_rendering.GRAPHICS", Tile)
    sequence = Sequence(
        "cache-example",
        "M5 1",
        "mathematik",
        5,
        "Cache",
        7,
        [
            Lesson(
                f"lesson-{i}",
                f"Stunde {i}",
                preparation=f"Vorbereitung {i}",
                goals=[f"Ziel {i}"],
                phases=[Phase("Einstieg", f"Inhalt {i}")],
                material=[f"Material {i}"],
            )
            for i in range(7)
        ],
    )
    save_sequence(tmp_path, sequence)
    return config, sequence


def visible_document(screen):
    pane = screen.query_one(
        "#lesson-planning" if screen.show_planning else "#lesson-preparation"
    )
    return next(viewer for viewer in pane.query(DocumentViewer) if viewer.display)


def ready(screen, lesson_id):
    try:
        viewer = visible_document(screen)
    except StopIteration:
        return False
    return (
        screen.lesson_id == lesson_id
        and viewer.path.parent.name == lesson_id
        and bool(viewer.image_tiles)
        and viewer.rendered_signature == viewer.signature
    )


def test_neighbours_reuse_and_bounded_views(tmp_path, monkeypatch):
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
            expected = {
                (f"lesson-{i}", planning)
                for i in range(1, 6)
                for planning in (False, True)
            }
            await until(lambda: {call[0] for call in renderer.calls} == expected)
            initial = visible_document(screen)
            tile = initial.image_tiles[0][0]
            picker = screen.query_one("#lesson-list")
            picker.highlighted = 4
            await until(lambda: ready(screen, "lesson-4"))
            await pilot.pause()
            pane = screen.query_one("#lesson-preparation")
            pane.scroll_home(animate=False)
            await pilot.pause()
            initial._initial_scroll_pending = True
            initial.position_continuation()
            await pilot.pause()
            assert pane.scroll_y == 0
            picker.highlighted = 3
            await until(lambda: ready(screen, "lesson-3"))
            await pilot.pause()
            assert visible_document(screen) is initial
            assert initial.image_tiles[0][0] is tile
            assert pane.scroll_y > 0
            assert app.focused is picker
            screen.action_toggle_material()
            await until(lambda: ready(screen, "lesson-3"))
            assert visible_document(screen).planning.goals == ["Ziel 3"]
            for index in (4, 5, 6):
                picker.highlighted = index
                await until(lambda: ready(screen, f"lesson-{index}"))
            await pilot.pause()
            assert {key[0] for key in screen._documents} <= {
                "lesson-4",
                "lesson-5",
                "lesson-6",
            }
            assert len(screen.query(DocumentViewer)) <= 6
            assert initial not in screen.query(DocumentViewer)

    asyncio.run(run())


def test_foreground_selection_interrupts_prefetch_and_close_stops_work(
    tmp_path, monkeypatch
):
    _, sequence = setup_lessons(tmp_path, monkeypatch)

    async def run():
        app = PultApp()
        renderer = RecordingRenderer(tmp_path)
        renderer.block = ("lesson-3", True)
        app.document_renderer = renderer
        async with app.run_test(size=(160, 46)) as pilot:
            await pilot.pause()
            screen = LessonScreen(sequence, "lesson-3")
            await app.push_screen(screen)
            await asyncio.wait_for(renderer.started.wait(), 5)
            screen.query_one("#lesson-list").highlighted = 4
            await until(lambda: ready(screen, "lesson-4"))
            assert renderer.cancelled.is_set()
            renderer.block = ("lesson-4", True)
            renderer.started.clear()
            renderer.cancelled.clear()
            await asyncio.wait_for(renderer.started.wait(), 5)
            # Coalesced picker events must leave document and materials on the
            # final selection, even while a background document is blocked.
            renderer.block = ("lesson-6", True)
            renderer.started.clear()
            for index in (5, 0, 6):
                screen.query_one("#lesson-list").highlighted = index
                await asyncio.sleep(0)
            await until(lambda: ready(screen, "lesson-6"))
            assert (
                screen.query_one("#lesson-materials").entries[0].label == "Material 6"
            )
            await asyncio.wait_for(renderer.started.wait(), 5)
            renderer.cancelled.clear()
            screen.action_close()
            await pilot.pause()
            assert renderer.cancelled.is_set()
            calls = len(renderer.calls)
            await asyncio.sleep(0.25)
            assert len(renderer.calls) == calls

    asyncio.run(run())


def test_cached_documents_follow_resize_font_theme_and_editor_changes(
    tmp_path, monkeypatch
):
    config, sequence = setup_lessons(tmp_path, monkeypatch)

    async def run():
        app = PultApp()
        app.document_renderer = RecordingRenderer(tmp_path)
        async with app.run_test(size=(160, 46)) as pilot:
            await pilot.pause()
            screen = LessonScreen(sequence, "lesson-3")
            await app.push_screen(screen)
            await until(lambda: ready(screen, "lesson-3"))
            original = visible_document(screen)
            old_signature = original.rendered_signature
            screen.query_one("#lesson-list").highlighted = 4
            await until(lambda: ready(screen, "lesson-4"))
            config.document_font = "source-sans-3"
            app.theme = "textual-light"
            await pilot.resize_terminal(190, 50)
            screen.query_one("#lesson-list").highlighted = 3
            await until(
                lambda: (
                    ready(screen, "lesson-3")
                    and original.rendered_signature != old_signature
                )
            )
            assert original.rendered_signature[0] > old_signature[0]
            assert original.rendered_signature[1] != old_signature[1]
            assert original.rendered_signature[3] == "source-sans-3"

            monkeypatch.setattr(app, "suspend", nullcontext)

            def editor(command, *, check):
                Path(command[-1]).write_text("# Geänderte Vorbereitung")
                return SimpleNamespace(returncode=0)

            monkeypatch.setattr(
                "pult.screens.teaching.lesson_screen.subprocess.run", editor
            )
            await screen.edit("vorbereitung.md")
            await until(lambda: ready(screen, "lesson-3"))
            assert visible_document(screen) is not original
            assert visible_document(screen).source == "# Geänderte Vorbereitung"
            assert original not in screen.query(DocumentViewer)

    asyncio.run(run())


def test_disk_cache_hit_does_not_wait_for_busy_renderer(tmp_path, monkeypatch):
    async def run():
        renderer = DocumentRenderer(tmp_path / "cache")
        page = SimpleNamespace(close=AsyncMock())
        renderer.browser = SimpleNamespace(new_page=AsyncMock(return_value=page))
        monkeypatch.setattr(renderer, "ensure_browser", AsyncMock())

        async def render_png(page, document, target):
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"cached image")
            return target

        monkeypatch.setattr(renderer, "_render_png", render_png)
        args = (
            "Text",
            tmp_path / "text.md",
            tmp_path,
            800,
            19,
            "#000000",
            "#ffffff",
            "#aaaaaa",
        )
        path = await renderer.render(*args, font="source-sans-3")
        async with renderer.lock:
            assert (
                await asyncio.wait_for(
                    renderer.render(*args, font="source-sans-3"), 0.2
                )
                == path
            )
        assert renderer.browser.new_page.await_count == 1

    asyncio.run(run())


def test_cancelled_render_closes_page_and_drains_operation(tmp_path, monkeypatch):
    async def run():
        renderer = DocumentRenderer(tmp_path / "cache")
        started, closed, drained = asyncio.Event(), asyncio.Event(), asyncio.Event()

        async def close():
            closed.set()

        page = SimpleNamespace(close=AsyncMock(side_effect=close))
        renderer.browser = SimpleNamespace(new_page=AsyncMock(return_value=page))
        monkeypatch.setattr(renderer, "ensure_browser", AsyncMock())

        async def render_png(page, document, target):
            started.set()
            await closed.wait()
            drained.set()
            raise RuntimeError("Page closed")

        monkeypatch.setattr(renderer, "_render_png", render_png)
        rendering = asyncio.create_task(
            renderer.render(
                "Text",
                tmp_path / "text.md",
                tmp_path,
                800,
                19,
                "#000000",
                "#ffffff",
                "#aaaaaa",
                font="source-sans-3",
            )
        )
        await started.wait()
        rendering.cancel()
        with pytest.raises(asyncio.CancelledError):
            await rendering
        assert closed.is_set() and drained.is_set()
        assert not renderer.lock.locked()
        assert not renderer.cache.exists()

    asyncio.run(run())
