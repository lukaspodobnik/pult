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
    split_phase_time,
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


def test_named_code_is_highlighted_without_interpreting_html_or_math():
    source = '```python\n# Kommentar\nprint("<script>$$x$$</script>")\n```'
    rendered = document_html(
        source,
        Path("test.md"),
        Path.cwd(),
        900,
        19,
        "#18252b",
        "#e7ece7",
        "#afbbac",
    )
    assert '<pre class="syntax-highlight">' in rendered
    assert '<span class="c1"># Kommentar</span>' in rendered
    assert "&lt;script&gt;" in rendered
    assert "<script>" not in rendered
    assert 'class="math"' not in rendered


def test_unknown_and_unlabelled_code_stay_readable():
    for language in ("", "pult-unknown-language"):
        rendered = document_html(
            f"```{language}\n<tag> & value\n```",
            Path("test.md"),
            Path.cwd(),
            900,
            19,
            "#ffffff",
            "#222222",
            "#777777",
        )
        assert "&lt;tag&gt; &amp; value" in rendered
        assert '<pre class="syntax-highlight">' not in rendered


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
            Phase("Einstieg", "**5**\n\n- **Beispiel** mit $x$\n- Zweites Beispiel"),
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
    assert "<th>Zeit</th><th>Phase</th><th>Inhalt</th>" in output
    assert "<tr><td>5</td><td>Einstieg</td><td><ul>" in output
    assert "<tr><td></td><td>Übung</td><td></td></tr>" in output
    assert output.count("<td>5</td>") == 1
    assert "Min." not in output
    assert "<strong>Beispiel</strong>" in output
    assert "<li>" in output
    assert "\\(x\\)" in output


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("**4** Besprechen.", ("4", "Besprechen.")),
        ("**2,5**", ("2,5", "")),
        ("**4**\n\n    code", ("4", "    code")),
        ("3 Aufgaben bearbeiten.", ("", "3 Aufgaben bearbeiten.")),
        ("**3 Aufgaben** bearbeiten.", ("", "**3 Aufgaben** bearbeiten.")),
        ("```md\n**4**\n```", ("", "```md\n**4**\n```")),
        ("**4 Min.** Besprechen.", ("4", "Besprechen.")),
        ("10 Min.\n\n- Beispiel", ("10", "- Beispiel")),
        ("**2,5 Min.**", ("2,5", "")),
        ("**4 Min.**\n\n    code", ("4", "    code")),
        ("Text mit **4 Min.**", ("", "Text mit **4 Min.**")),
        ("```md\n**4 Min.**\n```", ("", "```md\n**4 Min.**\n```")),
        ("**4 Min. Inhalt**", ("", "**4 Min. Inhalt**")),
        ("5 Minuten zählen.", ("", "5 Minuten zählen.")),
        ("", ("", "")),
    ],
)
def test_phase_time_only_extracts_a_separate_leading_duration(source, expected):
    assert split_phase_time(source) == expected


def test_text_planning_keeps_time_columns_and_markdown(tmp_path):
    from rich.console import Console
    from rich.table import Table
    from textual.widgets import Static

    from pult.widgets.document_viewer import DocumentViewer

    lesson = Lesson(
        "test",
        "Test",
        phases=[
            Phase("Einstieg", "**5**\n\n- Beispiel mit $x$\n- Zweiter Punkt"),
            Phase("Übung", "> [!merksatz] Regel\n> Zusammenfassen."),
        ],
    )
    viewer = DocumentViewer("", tmp_path / "verlauf.md", tmp_path, planning=lesson)
    table_widget = viewer.fallback_widgets()[-1]
    assert isinstance(table_widget, Static)
    table = table_widget.content
    assert isinstance(table, Table)
    assert [column.header for column in table.columns] == ["Zeit", "Phase", "Inhalt"]
    console = Console(width=90, force_terminal=False)
    with console.capture() as capture:
        console.print(table)
    text = capture.get()
    assert text.count("5") == 1
    assert "Min." not in text
    assert "Beispiel mit $x$" in text and "Zweiter Punkt" in text
    assert "Merke" in text and "Zusammenfassen." in text
    assert "[!merksatz]" not in text


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
            self,
            source,
            path,
            directory,
            width,
            font_size,
            *colors,
            planning=None,
            font="auto",
            callout_colors=None,
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
            pane = app.query_one(DocumentPane)
            viewer = app.query_one(DocumentViewer)
            background = app.document_renderer.calls[-1][1][0]
            assert background != app.get_css_variables()["surface"]
            assert pane.styles.background.hex == background
            assert viewer.styles.background.hex == background
            assert (
                viewer.query_one("#document-body").styles.background.hex == background
            )
            assert tiles[-1].image.getpixel((0, tiles[-1].image.height - 1)) == (
                pane.styles.background.r,
                pane.styles.background.g,
                pane.styles.background.b,
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
            background = app.document_renderer.calls[-1][1][0]
            assert pane.styles.background.hex == background
            assert viewer.styles.background.hex == background
            assert (
                app.document_renderer.calls[-1][1][1]
                == app.get_css_variables()["foreground"]
            )

    asyncio.run(run())


@pytest.mark.parametrize("available", [True, False])
def test_font_resolution_respects_choice_and_falls_back(monkeypatch, available):
    renderer = DocumentRenderer()

    async def availability():
        return available

    monkeypatch.setattr(renderer, "avenir_available", availability)

    async def run():
        expected = "avenir-next" if available else "source-sans-3"
        assert await renderer.resolve_font("auto") == expected
        assert await renderer.resolve_font("avenir-next") == expected
        assert await renderer.resolve_font("source-sans-3") == "source-sans-3"
        with pytest.raises(ValueError):
            await renderer.resolve_font("unknown")

    asyncio.run(run())


def test_font_changes_document_cache_input():
    args = (
        "# Titel\n\n**Begriff**",
        Path("test.md"),
        Path.cwd(),
        900,
        19,
        "#000000",
        "#ffffff",
        "#aaaaaa",
    )
    source = document_html(*args, font="source-sans-3")
    avenir = document_html(*args, font="avenir-next")
    assert source != avenir
    assert "data:font/ttf;base64," in source
    assert "AvenirNext-DemiBold" in avenir
    assert "strong,b {font-weight:500;}" in source


@pytest.mark.parametrize("theme", ["textual-dark", "textual-light"])
def test_document_border_stays_on_outer_surface_with_short_content(tmp_path, theme):
    from textual.app import App
    from textual.geometry import Region

    from pult.widgets.document_viewer import DocumentPane, DocumentViewer

    class ViewerApp(App):
        def compose(self):
            with DocumentPane():
                viewer = DocumentViewer("# Kurz", tmp_path / "test.md", tmp_path)
                viewer.text_mode = True
                yield viewer

    def background(strip):
        return next(iter(strip)).style.bgcolor.get_truecolor()

    async def run():
        app = ViewerApp()
        app.theme = theme
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause(0.5)
            await app.workers.wait_for_complete()
            pane = app.query_one(DocumentPane)
            pane.border_title = "Dokument"
            pane.border_subtitle = "Vorbereitung"
            pane.focus()
            await pilot.pause()
            outer = pane.background_colors[0]
            expected_outer = (outer.r, outer.g, outer.b)
            inner = pane.styles.background
            expected_inner = (inner.r, inner.g, inner.b)
            assert expected_inner != expected_outer
            lines = pane.render_lines(
                Region(0, 0, pane.outer_size.width, pane.outer_size.height)
            )
            assert lines[0].text.startswith("╭") and lines[0].text.endswith("╮")
            assert lines[-1].text.startswith("╰") and lines[-1].text.endswith("╯")
            for y in (0, pane.outer_size.height - 1):
                assert all(
                    s.style.bgcolor.get_truecolor() == expected_outer for s in lines[y]
                )
            blank_line = lines[-2]
            assert background(blank_line.crop(0, 1)) == expected_outer
            assert (
                background(blank_line.crop(pane.outer_size.width - 1)) == expected_outer
            )
            assert background(blank_line.crop(1, 2)) == expected_inner
            # Partial repaint of the right edge must preserve the same separation.
            cropped = pane.render_lines(
                Region(pane.outer_size.width - 2, pane.outer_size.height - 2, 2, 1)
            )[0]
            assert background(cropped.crop(0, 1)) == expected_inner
            assert background(cropped.crop(1, 2)) == expected_outer
            await pilot.resize_terminal(100, 30)
            await pilot.pause(0.5)
            resized = pane.render_lines(
                Region(0, 0, pane.outer_size.width, pane.outer_size.height)
            )
            assert background(resized[0].crop(0, 1)) == expected_outer
            assert background(resized[-2].crop(1, 2)) == expected_inner

    asyncio.run(run())


def test_pixel_corners_round_viewport_without_rounding_tile_seams():
    from pult.services.document_corners import round_document_tile

    original = Image.new("RGB", (100, 80), "#303030")
    rounded = round_document_tile(original, (0, 0, 100, 80), "#202020", 10)
    assert rounded.getpixel((0, 0)) == (32, 32, 32)
    assert rounded.getpixel((99, 0)) == (32, 32, 32)
    assert rounded.getpixel((0, 79)) == (32, 32, 32)
    assert rounded.getpixel((99, 79)) == (32, 32, 32)
    assert rounded.getpixel((50, 0)) == (48, 48, 48)
    assert original.getpixel((0, 0)) == (48, 48, 48)
    # A middle tile must not acquire corners at its own boundaries.
    assert round_document_tile(original, (0, -80, 100, 160), "#202020", 10) is original


def test_rounding_tracks_scroll_and_fills_short_documents(tmp_path, monkeypatch):
    from textual.app import App
    from textual.widgets import Static

    from pult.services import material_rendering as graphics
    from pult.widgets.document_viewer import DocumentPane, DocumentViewer

    class Tile(Static):
        def __init__(self, image, **kwargs):
            self.image = image
            super().__init__("", **kwargs)

    class Renderer:
        async def render(
            self, source, path, directory, width, font_size, *colors, **kwargs
        ):
            output = tmp_path / "image.png"
            height = 1200 if source == "long" else 80
            Image.new("RGB", (width, height), colors[0]).save(output)
            return output

    class ViewerApp(App):
        def compose(self):
            with DocumentPane():
                yield DocumentViewer("long", tmp_path / "test.md", tmp_path)

    monkeypatch.setattr(graphics, "GRAPHICS", Tile)
    monkeypatch.setattr(graphics, "CELL", (10, 20))

    async def run():
        app = ViewerApp()
        app.document_renderer = Renderer()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause(0.6)
            await app.workers.wait_for_complete()
            pane = app.query_one(DocumentPane)
            viewer = app.query_one(DocumentViewer)
            outer = pane.background_colors[0]
            expected = (outer.r, outer.g, outer.b)
            first_tile = viewer.image_tiles[0][0]
            assert first_tile.image.getpixel((0, 0)) == expected
            pane.scroll_to(y=5, animate=False)
            await pilot.pause()
            viewer.refresh_corners()
            assert first_tile.image.getpixel((0, 100)) == expected
            assert first_tile.image.getpixel((0, 0)) != expected
            pane.scroll_end(animate=False)
            await pilot.pause()
            viewer.refresh_corners()
            last_tile = viewer.image_tiles[-1][0]
            assert last_tile.image.getpixel((0, last_tile.image.height - 1)) == expected
            # Short content fills the viewport without adding a scrollable empty tail.
            pane.scroll_home(animate=False)
            viewer.source = "short"
            viewer.signature = None
            viewer.schedule_render()
            await pilot.pause(0.6)
            await app.workers.wait_for_complete()
            await pilot.pause()
            viewer.refresh_corners()
            assert pane.max_scroll_y == 0
            tile = viewer.image_tiles[0][0]
            assert tile.image.height == pane.scrollable_content_region.height * 20
            assert tile.image.getpixel((0, tile.image.height - 1)) == expected
            assert (
                tile.image.getpixel((tile.image.width - 1, tile.image.height - 1))
                == expected
            )

    asyncio.run(run())
