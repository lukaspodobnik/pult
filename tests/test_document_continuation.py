import asyncio
import math
import os

import pytest
from PIL import Image
from PIL.PngImagePlugin import PngInfo
from textual.app import App
from textual.widgets import Static

from pult.curriculum.material import Lesson
from pult.services import material_rendering as graphics
from pult.services.document_rendering import SEPARATOR_Y, DocumentRenderer
from pult.widgets.document_viewer import DocumentPane, DocumentViewer

SOURCE = (
    "> Zitat\n>\n> ---\n\n```\n---\n```\n\n"
    + "Bisheriger Hefteintrag.\n\n" * 24
    + "---\n\n> [!merksatz] Fortsetzung\n> Neue Regel mit $a^2$.\n"
)


class Tile(Static):
    def __init__(self, image, **kwargs):
        self.image = image
        super().__init__("", **kwargs)


@pytest.mark.parametrize("mode", ["image", "text", "failed-image"])
@pytest.mark.parametrize(
    ("placement", "image_height", "separator_y", "source"),
    [
        ("middle", 1600, 900.5, SOURCE + "\nWeiterer Inhalt.\n\n" * 12),
        ("fits", 200, 100, "# Eintrag\n\nBisheriger Text.\n\n---\n\nNeuer Text.\n"),
        ("near-end", 1050, 900.5, SOURCE),
        ("near-start", 1600, 100, "# Eintrag\n\n---\n\n" + "Inhalt.\n\n" * 30),
    ],
)
def test_continuation_centers_only_with_natural_overflow(
    tmp_path, monkeypatch, mode, placement, image_height, separator_y, source
):
    class Renderer:
        async def render(self, source, path, directory, width, *args, **kwargs):
            if mode == "failed-image":
                raise RuntimeError("Browser unavailable")
            metadata = PngInfo()
            metadata.add_text(SEPARATOR_Y, str(separator_y))
            image_path = tmp_path / "render.png"
            Image.new("RGB", (width, image_height), "white").save(
                image_path, pnginfo=metadata
            )
            return image_path

    class ViewerApp(App):
        def compose(self):
            with DocumentPane():
                yield DocumentViewer(
                    source,
                    tmp_path / "vorbereitung.md",
                    tmp_path,
                    start_at_separator=True,
                )

    monkeypatch.setattr(graphics, "GRAPHICS", None if mode == "text" else Tile)
    monkeypatch.setattr(graphics, "CELL", (10, 20))

    async def run():
        app = ViewerApp()
        app.document_renderer = Renderer()
        async with app.run_test(size=(80, 22)) as pilot:
            await pilot.pause(0.7)
            await app.workers.wait_for_complete()
            await pilot.pause()
            pane = app.query_one(DocumentPane)
            viewer = app.query_one(DocumentViewer)
            viewport = pane.scrollable_content_region
            if placement in ("fits", "near-start"):
                assert pane.scroll_y == 0
            else:
                assert pane.scroll_y > 0
            if placement == "fits":
                assert pane.max_scroll_y == 0
            if mode == "image":
                # The image may fill the viewport, but must not acquire a scrollable tail.
                assert pane.max_scroll_y == max(
                    0, math.ceil(image_height / 20) - viewport.height
                )
                if placement == "middle":
                    assert (
                        pane.scroll_y
                        == math.floor(separator_y / 20) - viewport.height // 2
                    )
            else:
                rule = viewer.query("MarkdownHorizontalRule.level-0").first()
                if placement == "middle":
                    assert rule.region.y == viewport.y + viewport.height // 2
                elif placement == "near-end":
                    assert rule.region.y > viewport.y + viewport.height // 2
            if placement == "near-end":
                assert pane.scroll_y == pane.max_scroll_y
            if placement != "middle":
                return
            pane.scroll_to(y=3, animate=False)
            await pilot.pause()
            # Showing planning and returning, as well as a fresh layout, must
            # leave the reader's chosen position alone.
            pane.display = False
            await pilot.pause()
            pane.display = True
            await pilot.resize_terminal(90, 26)
            await pilot.pause(0.7)
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert pane.scroll_y == 3

    asyncio.run(run())


@pytest.mark.parametrize(
    ("source", "enabled", "planning"),
    [
        (SOURCE, False, None),
        (SOURCE, True, Lesson("test", "Planung")),
        ("Bisheriger Text.\n\n" * 24 + "> Zitat\n>\n> ---\n", True, None),
        ("Bisheriger Text.\n\n" * 24 + "```\n---\n```\n", True, None),
        ("Bisheriger Text.\n\n" * 24, True, None),
    ],
)
def test_only_preparation_with_a_real_top_level_rule_scrolls(
    tmp_path, monkeypatch, source, enabled, planning
):
    class ViewerApp(App):
        def compose(self):
            with DocumentPane():
                yield DocumentViewer(
                    source,
                    tmp_path / "text.md",
                    tmp_path,
                    planning=planning,
                    start_at_separator=enabled,
                )

    monkeypatch.setattr(graphics, "GRAPHICS", None)

    async def run():
        async with ViewerApp().run_test() as pilot:
            await pilot.pause(0.7)
            assert pilot.app.query_one(DocumentPane).scroll_y == 0

    asyncio.run(run())


@pytest.mark.skipif(
    not os.environ.get("PULT_TEST_BROWSER"), reason="Expliziter lokaler Browser-Test"
)
def test_browser_caches_the_actual_separator_position(tmp_path, monkeypatch):
    async def run():
        renderer = DocumentRenderer(tmp_path / "cache")
        args = (
            SOURCE,
            tmp_path / "text.md",
            tmp_path,
            700,
            20,
            "#ffffff",
            "#222222",
            "#556677",
        )
        try:
            path = await renderer.render(*args, font="source-sans-3")
            with Image.open(path) as image:
                y = float(image.info[SEPARATOR_Y])
                # Ignore the earlier rule in the quote and the literal in code.
                assert 400 < y < image.height
            for source in ("> Zitat\n>\n> ---", "```\n---\n```", "# Ohne Linie"):
                other = await renderer.render(source, *args[1:], font="source-sans-3")
                with Image.open(other) as image:
                    assert SEPARATOR_Y not in image.info
        finally:
            await renderer.close()

        cached = DocumentRenderer(tmp_path / "cache")

        async def no_browser():
            raise AssertionError("Cache hit should not start a browser")

        monkeypatch.setattr(cached, "ensure_browser", no_browser)
        assert await cached.render(*args, font="source-sans-3") == path
        with Image.open(path) as image:
            assert float(image.info[SEPARATOR_Y]) == y

    asyncio.run(run())
