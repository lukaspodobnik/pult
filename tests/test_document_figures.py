import os

import pytest
from PIL import Image

from pult.services.document_callouts import text_document_parser
from pult.services.document_rendering import markdown_html


def render(source, tmp_path):
    Image.new("RGB", (10, 10), "white").save(tmp_path / "bild.png")
    return markdown_html(source, tmp_path / "aufgabe.md", tmp_path)


def test_picture_beside_text_preserves_markdown_and_math(tmp_path):
    html = render(
        ":::abbildung\n**Berechne** $a b$.\n\n![Rechteck](bild.png)\n:::\n\nDanach.",
        tmp_path,
    )
    assert '<div class="illustrated">' in html
    assert '<div class="illustrated-text">' in html
    assert '<figure class="illustrated-image">' in html
    assert "<strong>Berechne</strong>" in html and r"\(a b\)" in html
    assert "data:image/png;base64," in html and 'alt="Rechteck"' in html
    assert ":::" not in html
    assert html.endswith("<p>Danach.</p>\n")


def test_picture_inside_subtask_keeps_labels_and_sibling_items(tmp_path):
    source = "::::teilaufgaben\na)\n\n:::abbildung\nBerechne.\n\n![Bild](bild.png)\n:::\n\nb) Begründe.\n::::"
    html = render(source, tmp_path)
    assert html.count('class="subtask"') == 2
    assert html.count('class="illustrated"') == 1
    assert 'class="subtask-label">a)' in html and 'class="subtask-label">b)' in html
    assert html.index("Berechne.") < html.index('class="subtask-label">b)')
    tokens = text_document_parser().parse(source)
    assert all(
        not t.type.startswith(("container_", "figure_layout", "subtask"))
        for t in tokens
    )
    assert [t.content for t in tokens if t.type == "inline"] == [
        "a)",
        "Berechne.",
        "![Bild](bild.png)",
        "b) Begründe.",
    ]
    assert sum(t.nesting for t in tokens) == 0


def test_subtasks_inside_figure_block(tmp_path):
    html = render(
        "::::abbildung\n:::teilaufgaben\na) Eins.\n\nb) Zwei.\n:::\n\n![Bild](bild.png)\n::::",
        tmp_path,
    )
    assert html.count('class="illustrated"') == 1
    assert html.count('class="subtask"') == 2


@pytest.mark.parametrize(
    "body",
    [
        "Kein Bild.",
        "![Bild](bild.png)",
        "![A](bild.png)\n\n![B](bild.png)\n\nText.",
        "Text ![Bild](bild.png) im Absatz.",
    ],
)
def test_ambiguous_content_stays_in_reading_order(tmp_path, body):
    html = render(":::abbildung\n" + body + "\n:::", tmp_path)
    assert 'class="illustrated"' not in html
    assert ":::" not in html


def test_code_and_unknown_options_are_not_layouts(tmp_path):
    for source in [
        "```md\n:::abbildung\nText.\n\n![Bild](bild.png)\n:::\n```",
        ":::abbildung onclick=x\nText.\n\n![Bild](bild.png)\n:::",
    ]:
        assert 'class="illustrated"' not in render(source, tmp_path)


def test_existing_image_security_applies(tmp_path):
    with pytest.raises(ValueError, match="relative Dateien"):
        render(
            ":::abbildung\nText.\n\n![Bild](https://example.org/bild.png)\n:::",
            tmp_path,
        )
    with pytest.raises(ValueError, match="außerhalb"):
        render(":::abbildung\nText.\n\n![Bild](../bild.png)\n:::", tmp_path)
    html = render(
        ":::abbildung\n<script>alert(1)</script>\n\n![Bild](bild.png)\n:::", tmp_path
    )
    assert "<script>" not in html and "&lt;script&gt;" in html


@pytest.mark.skipif(
    not os.environ.get("PULT_TEST_BROWSER"),
    reason="Expliziter lokaler Browser-Test",
)
def test_browser_figure_layout_adapts_to_screen_and_print(tmp_path):
    import asyncio

    from pult.services.document_rendering import DocumentRenderer, document_html

    async def run():
        renderer = DocumentRenderer(tmp_path / "cache")
        Image.new("RGB", (800, 600), "white").save(tmp_path / "bild.png")
        source = (
            ":::abbildung\nBestimme den Flächeninhalt.\n\n![Rechteck](bild.png)\n:::"
        )
        try:
            await renderer.ensure_browser()
            page = await renderer.browser.new_page()
            for width, size, media, beside in [
                (1000, 22, "screen", True),
                (700, 22, "screen", True),
                (400, 22, "screen", False),
                (640, 15, "print", True),
            ]:
                await page.set_viewport_size({"width": width, "height": 900})
                await page.emulate_media(media=media)
                await page.set_content(
                    document_html(
                        source,
                        tmp_path / "aufgabe.md",
                        tmp_path,
                        width,
                        size,
                        "#ffffff",
                        "#222222",
                        "#41628a",
                    )
                )
                result = await page.evaluate("""() => {
                  const t=document.querySelector('.illustrated-text').getBoundingClientRect();
                  const i=document.querySelector('.illustrated-image img').getBoundingClientRect();
                  return {beside:i.left>=t.right,below:i.top>=t.bottom,width:i.width,overflow:document.documentElement.scrollWidth>innerWidth};
                }""")
                assert result["beside"] == beside
                assert result["below"] != beside
                assert 0 < result["width"] <= size * 11 + 1
                assert not result["overflow"]
            await page.close()
        finally:
            await renderer.close()

    asyncio.run(run())
