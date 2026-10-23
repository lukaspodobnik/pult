import pytest
from PIL import Image

from pult.services.documents.document_callouts import text_document_parser
from pult.services.documents.document_rendering import markdown_html


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
