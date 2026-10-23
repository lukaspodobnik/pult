import asyncio

import pytest
from PIL import Image

from pult.services.documents.document_callouts import text_document_parser
from pult.services.documents.document_rendering import (
    document_html,
    markdown_html,
)


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
    assert '<p class="callout-title">Merke · Distributivgesetz</p>' in html
    assert "<strong>gerade</strong>" in html
    assert "<ul>" in html
    assert "\\(2\\)" in html and "\\[a(b+c)=ab+ac\\]" in html
    assert "[!" not in html


def test_callouts_without_title_nested_or_with_only_title(tmp_path):
    html = render(
        "> [!DEFINITION]\n> Text.\n>\n> > [!merksatz] Nur ein Titel\n", tmp_path
    )
    assert '<p class="callout-title">Definition</p>' in html
    assert '<p class="callout-title">Merke · Nur ein Titel</p>' in html
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


def test_callout_colors_reject_css_injection(tmp_path):
    with pytest.raises(ValueError, match="Callout-Farbe"):
        document_html(
            "> [!definition]\n> Text",
            tmp_path / "test.md",
            tmp_path,
            800,
            19,
            "#202428",
            "#d8dde2",
            "#d6a06d",
            callout_colors=("red;}body{display:none", "#fab387"),
        )


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
                "Merke",
                "Weitere Erklärung.",
            ]

    asyncio.run(run())
