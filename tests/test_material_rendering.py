import asyncio
import os
from pathlib import Path

import pytest
from PIL import Image

from pult.curriculum.material import Lesson, Phase
from pult.services.documents.document_rendering import (
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
def test_browser_renders_math_and_local_images(tmp_path):
    async def run():
        renderer = DocumentRenderer(tmp_path / "cache")
        try:
            (tmp_path / "figure.svg").write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="60"><rect width="200" height="60" fill="red"/></svg>'
            )
            source = r"Ein $\frac{1}{2}$ im Text." + "\n\n![Bild](figure.svg)"
            path = await renderer.render(
                source,
                tmp_path / "text.md",
                tmp_path,
                800,
                19,
                "#18252b",
                "#e7ece7",
                "#afbbac",
            )
            with Image.open(path) as image:
                assert image.format == "PNG"
                image.verify()
        finally:
            await renderer.close()

    asyncio.run(run())


def test_sixel_palette_precedes_drawing():
    from pult.widgets.sixel_image import terminal_safe_sixel

    encoded = '\x1bP0;0;0q"1;1;4;6#0;2;0;0;0??#1;2;100;100;100@@\x1b\\'
    converted = terminal_safe_sixel(encoded)
    assert converted.startswith('\x1bP0;1;0q"1;1;4;6#0;2;0;0;0#1;2;100;100;100')
    assert converted.endswith("#0??#1@@\x1b\\")
