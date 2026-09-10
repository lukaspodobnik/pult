"""Lokales Markdown-/Formelrendering ohne Abhängigkeit vom Prototyp."""

import hashlib
import io
import os
import shutil
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from markdown_it import MarkdownIt
from mdit_py_plugins.dollarmath import dollarmath_plugin
from PIL import Image as PILImage

PARSER = MarkdownIt("commonmark").enable("table").use(dollarmath_plugin)
_image_widget = None


def initialize_graphics() -> None:
    """Terminalerkennung vor Textuals Übernahme des Terminals durchführen."""
    global _image_widget
    if not sys.stdout.isatty() or not sys.stdin.isatty():
        return
    from textual_image.widget import Image, SixelImage

    if Image is SixelImage:
        from pult.widgets.sixel_image import StableSixelImage

        _image_widget = StableSixelImage
    else:
        _image_widget = Image


def image_widget():
    return _image_widget


def blocks(source: str) -> Iterator[tuple[str, Any, str]]:
    lines = source.splitlines(keepends=True)
    cursor = 0
    for token in PARSER.parse(source):
        kind, value, caption = None, None, ""
        if token.type == "math_block":
            kind, value = "math", token.content
        elif token.type == "inline" and token.children:
            if len(token.children) == 1 and token.children[0].type == "image":
                child = token.children[0]
                kind, value, caption = "image", child.attrGet("src"), child.content
            elif any(child.type == "math_inline" for child in token.children):
                kind, value = "inline", token.children
        if kind is None or token.map is None:
            continue
        start, end = token.map
        if start > cursor:
            yield "text", "".join(lines[cursor:start]), ""
        yield kind, value, caption
        cursor = end
    if cursor < len(lines):
        yield "text", "".join(lines[cursor:]), ""


class MaterialRenderer:
    def __init__(self, background: str, foreground: str, cache: Path | None = None):
        self.background, self.foreground = background, foreground
        self.cache = (
            cache
            or Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache")))
            / "pult/materials"
        )

    def render(
        self, kind: str, value: str, source_path: Path, sequence_directory: Path
    ) -> Path:
        path: Path | None = None
        if kind == "math":
            if not shutil.which("node") or not shutil.which("rsvg-convert"):
                raise ValueError(
                    "Für Formeln werden Node.js und rsvg-convert benötigt."
                )
            payload = value.encode()
        else:
            path = (source_path.parent / value).resolve()
            if not path.is_relative_to(sequence_directory.resolve()):
                raise ValueError(
                    "Abbildungen müssen innerhalb des Sequenzordners liegen."
                )
            payload = path.read_bytes()
        key = hashlib.sha256(
            b"v1"
            + kind.encode()
            + self.background.encode()
            + self.foreground.encode()
            + payload
        ).hexdigest()
        target = self.cache / (key + ".png")
        if target.exists():
            return target
        if kind == "math":
            renderer = Path(__file__).parents[1] / "assets/math-renderer.cjs"
            svg = subprocess.run(
                ["node", str(renderer)],
                input=payload,
                capture_output=True,
                check=True,
                timeout=10,
            ).stdout
            svg = svg.replace(b"currentColor", self.foreground.encode())
            payload = subprocess.run(
                ["rsvg-convert"], input=svg, capture_output=True, check=True, timeout=10
            ).stdout
        elif path is not None and path.suffix.lower() == ".svg":
            if not shutil.which("rsvg-convert"):
                raise ValueError("Für SVG-Abbildungen wird rsvg-convert benötigt.")
            payload = subprocess.run(
                ["rsvg-convert", str(path)], capture_output=True, check=True, timeout=10
            ).stdout
        with PILImage.open(io.BytesIO(payload)) as image:
            canvas = PILImage.new("RGBA", image.size, self.background)
            canvas.alpha_composite(image.convert("RGBA"))
            self.cache.mkdir(parents=True, exist_ok=True)
            # Ein kompletter PNG-Bytestrom statt einer teilweise lesbaren Cache-Datei.
            output = io.BytesIO()
            canvas.convert("RGB").save(output, format="PNG")
            with NamedTemporaryFile(
                dir=self.cache, suffix=".png", delete=False
            ) as temporary:
                temporary.write(output.getvalue())
                temporary_path = Path(temporary.name)
            temporary_path.replace(target)
        return target
