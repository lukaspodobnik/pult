import shutil
from pathlib import Path

import pytest
from PIL import Image

from pult.services.material_rendering import MaterialRenderer, blocks


def test_markdown_code_is_not_parsed_as_math():
    parsed = list(blocks('```python\nprint("$$test$$")\n```\n\nEin $x$ und mehr.\n'))
    assert [item[0] for item in parsed] == ["text", "inline"]
    assert "$$test$$" in parsed[0][1]


@pytest.mark.skipif(
    not shutil.which("node") or not shutil.which("rsvg-convert"),
    reason="Lokaler Grafikrenderer nicht installiert",
)
def test_real_aligned_and_relative_svg(tmp_path):
    renderer = MaterialRenderer("#18252b", "#e7ece7", tmp_path / "cache")
    root = (
        Path(__file__).parents[1]
        / "examples/unterricht/sequences/6/mathematik/formatbeispiel"
    )
    source = root / "stunden/anteile/vorbereitung.md"
    formula = r"\begin{aligned}2x+4&=10\\2x&=6\\x&=3\end{aligned}"
    path = renderer.render("math", formula, source, root)
    with Image.open(path) as image:
        assert image.height > 70
    assert renderer.render("math", formula, source, root) == path
    figure = renderer.render("image", "../../dateien/anteile.svg", source, root)
    with Image.open(figure) as image:
        assert image.size == (480, 160)


def test_external_image_rejected(tmp_path):
    renderer = MaterialRenderer("#000000", "#ffffff", tmp_path / "cache")
    with pytest.raises(ValueError, match="Sequenzordner"):
        renderer.render(
            "image", "../../../outside.png", tmp_path / "vorbereitung.md", tmp_path
        )


def test_sixel_palette_precedes_drawing():
    from pult.widgets.sixel_image import terminal_safe_sixel

    encoded = '\x1bP0;0;0q"1;1;4;6#0;2;0;0;0??#1;2;100;100;100@@\x1b\\'
    converted = terminal_safe_sixel(encoded)
    assert converted.startswith('\x1bP0;1;0q"1;1;4;6#0;2;0;0;0#1;2;100;100;100')
    assert converted.endswith("#0??#1@@\x1b\\")
