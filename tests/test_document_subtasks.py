import asyncio
import os
from pathlib import Path

import pytest
from PIL import Image

from pult.services.document_callouts import text_document_parser
from pult.services.document_rendering import (
    DocumentRenderer,
    document_html,
    markdown_html,
)


def render(source, tmp_path):
    return markdown_html(source, tmp_path / "aufgabe.md", tmp_path)


def test_grid_keeps_order_labels_math_and_markdown(tmp_path):
    source = (
        "Vereinfache.\n\n:::teilaufgaben spalten=3\n"
        + "\n\n".join(
            f"{letter}) **Term** ${number}x$"
            for number, letter in enumerate("abcdef", 1)
        )
        + "\n:::\n\nDanach."
    )
    html = render(source, tmp_path)
    assert 'class="subtasks" data-columns="3"' in html
    assert html.count('class="subtask"') == 6
    assert html.count('class="subtask-label"') == 6
    positions = [html.index(f'class="subtask-label">{letter})') for letter in "abcdef"]
    assert positions == sorted(positions)
    assert html.count("<strong>Term</strong>") == 6
    assert "\\(1x\\)" in html and "\\(6x\\)" in html
    assert html.startswith("<p>Vereinfache.</p>")
    assert html.endswith("<p>Danach.</p>\n")
    assert ":::" not in html


def test_one_column_keeps_continuations_lists_callouts_and_code(tmp_path):
    html = render(
        ":::teilaufgaben\na) Entscheide **begründet**.\nFortsetzung.\n\n"
        "Ein weiterer Absatz.\n\n- Erster Punkt\n- Zweiter Punkt\n\n"
        "> [!merksatz] Regel\n> Nicht als Teilaufgabe: b)\n\n"
        "```text\nb) Ein Beispiel im Code\n```\n\nb) Berechne.\n\n"
        "$$x^2$$\n:::",
        tmp_path,
    )
    assert 'data-columns="1"' in html
    assert html.count('class="subtask"') == 2
    assert "<ul>" in html
    assert 'class="callout callout-merksatz"' in html
    assert "Ein weiterer Absatz." in html and "Fortsetzung." in html
    assert "b) Ein Beispiel im Code" in html and "\\[x^2\\]" in html


@pytest.mark.parametrize(
    "source",
    [
        "a) $x$\n\nb) $y$",
        "```md\n:::teilaufgaben spalten=3\na) $x$\n:::\n```",
        "    :::teilaufgaben\n    a) $x$\n    :::",
        ":::teilaufgaben spalten=4\na) $x$\n:::",
        ':::teilaufgaben spalten=3 onclick="alert(1)"\na) $x$\n:::',
        ":::teilaufgaben\nKeine Beschriftung.\n:::",
    ],
)
def test_other_markdown_never_becomes_a_grid(tmp_path, source):
    assert 'class="subtasks"' not in render(source, tmp_path)


def test_multiple_blocks_keep_independent_columns_and_labels(tmp_path):
    html = render(
        ":::teilaufgaben spalten=2\na) Eins.\n:::\n\n:::teilaufgaben\nb) Zwei.\n:::",
        tmp_path,
    )
    assert 'data-columns="2"' in html and 'data-columns="1"' in html
    assert html.count('class="subtask"') == 2
    assert 'class="subtask-label">b)' in html


def test_image_safety_and_escaping_also_apply_inside_grid(tmp_path):
    with pytest.raises(ValueError, match="relative Dateien"):
        render(":::teilaufgaben\na) ![Bild](https://example.org/x.png)\n:::", tmp_path)
    Image.new("RGB", (10, 10), "red").save(tmp_path / "bild.png")
    html = render(
        ":::teilaufgaben\na) ![Bild](bild.png) <script>alert(1)</script>\n:::", tmp_path
    )
    assert "data:image/png;base64," in html
    assert "&lt;script&gt;" in html and "<script>" not in html


def test_text_parser_preserves_labels_and_all_content_without_directives():
    tokens = text_document_parser().parse(
        ":::teilaufgaben spalten=3\na) $x$\n\nWeiter.\n\nb) **Begründe.**\n:::"
    )
    assert [t.content for t in tokens if t.type == "inline"] == [
        "a) $x$",
        "Weiter.",
        "b) **Begründe.**",
    ]
    assert all(not t.type.startswith(("container_", "subtask")) for t in tokens)
    assert sum(t.nesting for t in tokens) == 0


def test_text_viewer_displays_subtasks_and_following_document(tmp_path):
    from textual.app import App

    from pult.widgets.document_viewer import DocumentViewer

    class ViewerApp(App):
        def compose(self):
            viewer = DocumentViewer(
                "# Aufgabe\n\n:::teilaufgaben spalten=3\na) $x$\n\nb) **Begründe.**\n:::\n\nDanach.",
                tmp_path / "aufgabe.md",
                tmp_path,
            )
            viewer.text_mode = True
            yield viewer

    async def run():
        app = ViewerApp()
        async with app.run_test() as pilot:
            await pilot.pause(0.6)
            await app.workers.wait_for_complete()
            paragraphs = [w._content.plain for w in app.query("MarkdownParagraph")]
            assert paragraphs == ["a) $x$", "b) Begründe.", "Danach."]

    asyncio.run(run())


@pytest.mark.skipif(
    not os.environ.get("PULT_TEST_BROWSER"), reason="Expliziter lokaler Browser-Test"
)
def test_browser_grid_aligns_labels_and_adapts_for_screen_and_print(tmp_path):
    async def run():
        renderer = DocumentRenderer(tmp_path / "cache")
        source = (
            ":::teilaufgaben spalten=3\n"
            + "\n\n".join(
                f"{letter}) ${term}$"
                for letter, term in zip(
                    "abcdef",
                    [
                        r"\frac{2}{3}x \cdot 9y",
                        "4x",
                        r"x^2",
                        "7ab",
                        r"\frac{1}{4}a",
                        "5y",
                    ],
                )
            )
            + "\n:::"
        )
        try:
            await renderer.ensure_browser()
            page = await renderer.browser.new_page()
            await page.route("**/*", lambda route: route.abort())
            script = (
                Path(__file__).parents[1] / "src/pult/assets/mathjax/tex-svg-full.js"
            )
            for width, font_size, columns, media in (
                (1050, 22, 3, "screen"),
                (740, 22, 2, "screen"),
                (400, 22, 1, "screen"),
                (720, 15, 3, "print"),
            ):
                await page.set_viewport_size({"width": width, "height": 900})
                await page.emulate_media(media=media)
                await page.set_content(
                    document_html(
                        source,
                        tmp_path / "aufgabe.md",
                        tmp_path,
                        width,
                        font_size,
                        "#ffffff",
                        "#222222",
                        "#41628a",
                    )
                )
                await page.evaluate(
                    "window.MathJax = {startup:{typeset:false}, svg:{fontCache:'local'}}"
                )
                await page.add_script_tag(content=script.read_text())
                await page.evaluate(
                    "async () => {await MathJax.startup.promise; await MathJax.typesetPromise(); await document.fonts.ready;}"
                )
                layout = await page.evaluate("""() => {
                    const cells = Array.from(document.querySelectorAll('.subtask'));
                    const rect = e => {const r = e.getBoundingClientRect(); return {x:r.x, y:r.y, width:r.width};};
                    return {
                        cells:cells.map(rect),
                        bodies:cells.map(e => rect(e.querySelector('.subtask-content'))),
                        labelRects:cells.map(e => rect(e.querySelector('.subtask-label'))),
                        labels:cells.map(e => e.querySelector('.subtask-label').textContent),
                        overflow:document.documentElement.scrollWidth > innerWidth,
                        breaks:cells.map(e => getComputedStyle(e).breakInside),
                    };
                }""")
                assert layout["labels"] == [f"{letter})" for letter in "abcdef"]
                assert not layout["overflow"]
                for i, cell in enumerate(layout["cells"]):
                    assert layout["labelRects"][i]["y"] == pytest.approx(
                        layout["labelRects"][i // columns * columns]["y"]
                    )
                    assert layout["bodies"][i]["x"] == pytest.approx(
                        layout["bodies"][i % columns]["x"]
                    )
                    if i >= columns:
                        assert cell["y"] > layout["cells"][i - columns]["y"]
                assert set(layout["breaks"]) == {"avoid"}
            await page.close()
        finally:
            await renderer.close()

    asyncio.run(run())
