import asyncio
import os
from pathlib import Path

import pytest
from PIL import Image

from pult.curriculum.material import Lesson, Phase
from pult.services.document_rendering import (
    DocumentRenderer,
    document_html,
    parser,
    safe_local,
)


def test_code_is_not_math_and_html_is_escaped():
    source = '```python\nprint("$$test$$")\n```\n\nEin $x$ und mehr.\n<script>alert(1)</script>'
    tokens = parser().parse(source)
    assert tokens[0].type == "fence"
    assert any(c.type == "math_inline" for t in tokens for c in t.children or [])
    rendered = document_html(
        source, Path("test.md"), Path.cwd(), 900, 19, "#18252b", "#e7ece7", "#afbbac"
    )
    assert "<script>" not in rendered
    assert "max-width:980px" not in rendered
    assert "width:900px" in rendered


def test_local_images_participate_in_cache_content(tmp_path):
    image = tmp_path / "image.png"
    Image.new("RGB", (20, 20), "red").save(image)
    args = (
        "![Bild](image.png)",
        tmp_path / "text.md",
        tmp_path,
        500,
        19,
        "#000000",
        "#ffffff",
        "#aaaaaa",
    )
    first = document_html(*args)
    Image.new("RGB", (20, 20), "blue").save(image)
    assert document_html(*args) != first
    assert "data:image/png;base64" in first


def test_external_image_rejected(tmp_path):
    with pytest.raises(ValueError):
        safe_local("../outside.png", tmp_path / "text.md", tmp_path)
    with pytest.raises(ValueError):
        safe_local("https://example.org/x.png", tmp_path / "text.md", tmp_path)


def test_planning_table_renders_markdown_inside_cells(tmp_path):
    lesson = Lesson(
        "test",
        "Test",
        goals=["Erkennen"],
        phases=[
            Phase("Einstieg", "- **Beispiel** mit $x$\n- Zweites Beispiel"),
            Phase("Übung", ""),
        ],
    )
    output = document_html(
        "",
        tmp_path / "verlauf.md",
        tmp_path,
        900,
        19,
        "#000000",
        "#ffffff",
        "#aaaaaa",
        lesson,
    )
    assert '<table class="phases">' in output
    assert "<strong>Beispiel</strong>" in output
    assert "<li>" in output
    assert "\\(x\\)" in output


@pytest.mark.skipif(
    not os.environ.get("PULT_TEST_BROWSER"), reason="Expliziter lokaler Browser-Test"
)
def test_browser_renders_math_assets_width_theme_and_cache(tmp_path):
    async def run():
        renderer = DocumentRenderer(tmp_path / "cache")
        try:
            image = tmp_path / "figure.svg"
            image.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="60"><rect width="200" height="60" fill="red"/></svg>'
            )
            source = (
                "# Brüche\n\nEin $\\frac{1}{2}$ im Text.\n\n$$\\begin{aligned}2x+4&=10\\\\x&=3\\end{aligned}$$\n\n![Bild](figure.svg)\n\n"
                + "Ein Absatz.\n\n" * 80
            )
            args = (
                source,
                tmp_path / "text.md",
                tmp_path,
                800,
                19,
                "#18252b",
                "#e7ece7",
                "#afbbac",
            )
            path = await renderer.render(*args)
            with Image.open(path) as rendered:
                assert rendered.width == 800 and rendered.height > 3000
                assert rendered.getpixel((0, 0))[:3] == (24, 37, 43)
            browser = renderer.browser
            assert await renderer.render(*args) == path
            narrow = await renderer.render(
                source, args[1], tmp_path, 500, 19, "#ffffff", "#18252b", "#afbbac"
            )
            assert narrow != path and renderer.browser is browser
            with Image.open(narrow) as rendered:
                assert rendered.width == 500
        finally:
            await renderer.close()

    asyncio.run(run())


def test_sixel_palette_precedes_drawing():
    from pult.widgets.sixel_image import terminal_safe_sixel

    encoded = '\x1bP0;0;0q"1;1;4;6#0;2;0;0;0??#1;2;100;100;100@@\x1b\\'
    converted = terminal_safe_sixel(encoded)
    assert converted.startswith('\x1bP0;1;0q"1;1;4;6#0;2;0;0;0#1;2;100;100;100')
    assert converted.endswith("#0??#1@@\x1b\\")


def test_document_tiles_keep_native_scale_and_resize(tmp_path, monkeypatch):
    from textual.app import App
    from textual.widgets import Static

    from pult.services import material_rendering as graphics
    from pult.widgets.document_viewer import DocumentPane, DocumentViewer

    class Tile(Static):
        def __init__(self, image, **kwargs):
            self.image = image
            super().__init__("", **kwargs)

    class Renderer:
        def __init__(self):
            self.calls = []

        async def render(
            self, source, path, directory, width, font_size, *colors, planning=None
        ):
            self.calls.append((width, colors))
            image = tmp_path / f"render-{len(self.calls)}.png"
            Image.new("RGB", (width, 1703), colors[0]).save(image)
            return image

    class ViewerApp(App):
        def compose(self):
            with DocumentPane():
                yield DocumentViewer("# Test", tmp_path / "test.md", tmp_path)

    monkeypatch.setattr(graphics, "GRAPHICS", Tile)
    monkeypatch.setattr(graphics, "CELL", (10, 20))

    async def run():
        app = ViewerApp()
        app.document_renderer = Renderer()
        async with app.run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            await app.workers.wait_for_complete()
            tiles = list(app.query(Tile))
            assert len(tiles) == 3
            assert [t.styles.height.value for t in tiles] == [40, 40, 6]
            assert all(
                t.image.width == app.document_renderer.calls[-1][0] for t in tiles
            )
            await pilot.resize_terminal(120, 30)
            await pilot.pause(0.5)
            await app.workers.wait_for_complete()
            assert (
                app.document_renderer.calls[-1][0] > app.document_renderer.calls[0][0]
            )
            app.theme = "textual-light"
            await pilot.pause(0.8)
            await app.workers.wait_for_complete()
            assert (
                app.document_renderer.calls[-1][1] != app.document_renderer.calls[0][1]
            )

    asyncio.run(run())
