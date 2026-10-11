import asyncio
import colorsys
import os

import pytest
from PIL import Image
from textual.color import Color

from pult.services.document_callouts import resolve_callout_colors, text_document_parser
from pult.services.document_rendering import (
    DocumentRenderer,
    document_html,
    markdown_html,
)
from pult.services.themes import PULT_PALETTE, theme_from_palette


def render(source, tmp_path):
    return markdown_html(source, tmp_path / "text.md", tmp_path)


def test_callouts_keep_inline_math_and_block_content(tmp_path):
    source = (
        "> [!definition] Gerade Zahl\n> Eine Zahl heißt **gerade**, wenn $2$ sie teilt.\n>\n"
        "> - Beispiel: $4$\n> - Noch ein Beispiel: $6$\n\n"
        "> [!merksatz] Distributivgesetz\n>\n> Für $a$, $b$, $c$ gilt:\n>\n> $$a(b+c)=ab+ac$$\n"
    )
    html = render(source, tmp_path)
    assert 'class="callout callout-definition"' in html
    assert 'class="callout callout-merksatz"' in html
    assert '<p class="callout-title">Definition · Gerade Zahl</p>' in html
    assert '<p class="callout-title">Merksatz · Distributivgesetz</p>' in html
    assert "<strong>gerade</strong>" in html
    assert "<ul>" in html
    assert "\\(2\\)" in html and "\\[a(b+c)=ab+ac\\]" in html
    assert "[!" not in html


def test_callouts_without_title_nested_or_with_only_title(tmp_path):
    html = render(
        "> [!DEFINITION]\n> Text.\n>\n> > [!merksatz] Nur ein Titel\n", tmp_path
    )
    assert '<p class="callout-title">Definition</p>' in html
    assert '<p class="callout-title">Merksatz · Nur ein Titel</p>' in html
    assert html.count("<blockquote") == html.count("</blockquote>") == 2
    assert "<p></p>" not in html


@pytest.mark.parametrize(
    "source",
    [
        "> Ein normales Zitat.\n",
        "> [!unbekannt] Titel\n> Inhalt\n",
        "```md\n> [!definition] Beispielcode\n```\n",
        "    > [!definition] Eingerückter Code\n",
        "> Ein Zitat.\n> [!definition] Spätere Zeile\n",
        "[!definition] Ohne Zitatblock\n",
    ],
)
def test_other_markdown_remains_ordinary_markdown(tmp_path, source):
    assert 'class="callout' not in render(source, tmp_path)


def test_html_and_image_rules_also_apply_inside_callouts(tmp_path):
    html = render(
        "> [!definition] <script>alert(1)</script>\n> `<b>` und $x$.", tmp_path
    )
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert "<code>&lt;b&gt;</code>" in html
    with pytest.raises(ValueError, match="relative Dateien"):
        render("> [!merksatz]\n> ![Bild](https://example.org/bild.png)", tmp_path)
    Image.new("RGB", (10, 10), "blue").save(tmp_path / "bild.png")
    assert "data:image/png;base64," in render(
        "> [!merksatz]\n> ![Bild](bild.png)", tmp_path
    )


def test_text_parser_labels_callouts_and_keeps_latex_literal():
    tokens = text_document_parser().parse(
        "> [!definition] $x$\n> Eine **Variable** $x$."
    )
    text = [t.content for t in tokens if t.type == "inline"]
    assert text == ["Definition · $x$", "Eine **Variable** $x$."]
    assert not any(
        t.type.startswith("math") for token in tokens for t in token.children or []
    )


@pytest.mark.parametrize("background", ["#202428", "#eff1f5", "#000000", "#ffffff"])
def test_colors_keep_families_and_readable_contrast(background):
    def luminance(color):
        channels = [component / 255 for component in (color.r, color.g, color.b)]
        linear = [
            c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
            for c in channels
        ]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    for palette in (
        {},
        PULT_PALETTE,
        {"blue": "#89b4fa", "orange": "#fab387"},
        {"blue": "#00ff00", "accent": "#ff00ff"},
    ):
        blue, orange = resolve_callout_colors(background, palette)
        for color, interval in [(blue, (190, 250)), (orange, (15, 43))]:
            rgb = Color.parse(color)
            hue = colorsys.rgb_to_hls(rgb.r / 255, rgb.g / 255, rgb.b / 255)[0] * 360
            assert interval[0] <= hue <= interval[1]
            bg = Color.parse(background).blend(rgb, 0.07)
            light, dark = sorted([luminance(rgb), luminance(bg)], reverse=True)
            assert (light + 0.05) / (dark + 0.05) >= 4.5


def test_palette_preferences_and_theme_variables():
    palette = PULT_PALETTE | {"orange": "#fab387"}
    colors = resolve_callout_colors(palette["background"], palette)
    assert colors == (palette["blue"], palette["orange"])
    theme = theme_from_palette(palette)
    assert theme.variables["document-definition"] == colors[0]
    assert theme.variables["document-merksatz"] == colors[1]
    assert theme.primary == palette["accent"]
    assert (
        resolve_callout_colors(palette["background"], palette | {"blue": "#89b4fa"})
        != colors
    )


def test_midgray_theme_still_has_two_distinct_color_families():
    blue, orange = resolve_callout_colors("#808080", {})
    assert blue != orange
    for color, limits in [(blue, (190, 250)), (orange, (15, 43))]:
        rgb = Color.parse(color)
        hue = colorsys.rgb_to_hls(rgb.r / 255, rgb.g / 255, rgb.b / 255)[0] * 360
        assert limits[0] <= hue <= limits[1]


def test_callout_colors_affect_document_and_reject_css_injection(tmp_path):
    args = (
        "> [!definition]\n> Text",
        tmp_path / "test.md",
        tmp_path,
        800,
        19,
        "#202428",
        "#d8dde2",
        "#d6a06d",
    )
    first = document_html(*args, callout_colors=("#91adbf", "#d6a06d"))
    second = document_html(*args, callout_colors=("#89b4fa", "#fab387"))
    assert first != second
    assert "font-weight:600" in first
    with pytest.raises(ValueError, match="Callout-Farbe"):
        document_html(*args, callout_colors=("red;}body{display:none", "#fab387"))


def test_live_palette_change_rerenders_callouts_without_changing_headings(
    tmp_path, monkeypatch
):
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
            self, source, path, directory, width, font_size, *colors, **kwargs
        ):
            self.calls.append((colors, kwargs["callout_colors"]))
            path = tmp_path / "tile.png"
            Image.new("RGB", (width, 100), colors[0]).save(path)
            return path

    class ViewerApp(App):
        def compose(self):
            with DocumentPane():
                yield DocumentViewer(
                    "> [!definition]\n> Ein $x$.", tmp_path / "test.md", tmp_path
                )

    monkeypatch.setattr(graphics, "GRAPHICS", Tile)

    async def run():
        app = ViewerApp()
        app.register_theme(theme_from_palette(PULT_PALETTE, name="first"))
        app.register_theme(
            theme_from_palette(
                PULT_PALETTE | {"blue": "#89b4fa", "orange": "#fab387"}, name="second"
            )
        )
        app.theme = "first"
        app.document_renderer = Renderer()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause(0.6)
            await app.workers.wait_for_complete()
            first = app.document_renderer.calls[-1]
            app.theme = "second"
            await pilot.pause(0.8)
            await app.workers.wait_for_complete()
            second = app.document_renderer.calls[-1]
            assert first[0] == second[0]
            assert first[1] != second[1]

    asyncio.run(run())


def test_fallback_displays_callout_labels_and_body(tmp_path):
    from textual.app import App

    from pult.widgets.document_viewer import DocumentViewer

    class ViewerApp(App):
        def compose(self):
            viewer = DocumentViewer(
                "> [!definition] Variable\n> Ein $x$.\n\n> [!merksatz]\n> Weitere Erklärung.",
                tmp_path / "test.md",
                tmp_path,
            )
            viewer.text_mode = True
            yield viewer

    async def run():
        app = ViewerApp()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause(0.6)
            await app.workers.wait_for_complete()
            paragraphs = [
                widget._content.plain for widget in app.query("MarkdownParagraph")
            ]
            assert paragraphs == [
                "Definition · Variable",
                "Ein $x$.",
                "Merksatz",
                "Weitere Erklärung.",
            ]

    asyncio.run(run())


@pytest.mark.skipif(
    not os.environ.get("PULT_TEST_BROWSER"), reason="Expliziter lokaler Browser-Test"
)
def test_browser_renders_callouts_math_and_changed_palette(tmp_path):
    async def run():
        renderer = DocumentRenderer(tmp_path / "cache")
        source = (
            "> [!definition] Variable\n> Ein $x$.\n\n> [!merksatz]\n> $$a(b+c)=ab+ac$$"
        )
        args = (
            source,
            tmp_path / "test.md",
            tmp_path,
            650,
            19,
            "#202428",
            "#d8dde2",
            "#d6a06d",
        )
        try:
            first = await renderer.render(
                *args, font="source-sans-3", callout_colors=("#91adbf", "#d6a06d")
            )
            assert (
                await renderer.render(
                    *args, font="source-sans-3", callout_colors=("#91adbf", "#d6a06d")
                )
                == first
            )
            second = await renderer.render(
                *args, font="source-sans-3", callout_colors=("#89b4fa", "#fab387")
            )
            assert first != second
            with Image.open(first) as image:
                assert image.width == 650 and image.height > 150
        finally:
            await renderer.close()

    asyncio.run(run())
