"""Markdown, Terminaltext und lokale Formelbilder für die Unterrichtsansicht."""

import asyncio
import math
import re
import subprocess
from pathlib import Path

from PIL import Image as PILImage
from rich.cells import cell_len
from rich.text import Text
from textual import work
from textual.containers import Horizontal, Vertical
from textual.widgets import Markdown, Static

from pult.services.material_rendering import MaterialRenderer, blocks, image_widget


class LessonMaterial(Vertical):
    def __init__(self, source: str, path: Path, directory: Path):
        super().__init__(classes="lesson-material")
        self.source, self.path, self.directory = source, path, directory

    def on_mount(self) -> None:
        self.load_material()

    @work(exclusive=True)
    async def load_material(self) -> None:
        variables = self.app.get_css_variables()
        renderer = MaterialRenderer(variables["surface"], variables["foreground"])
        for kind, value, caption in blocks(self.source):
            if not self.is_mounted:
                return
            if kind == "text":
                await self.mount(Markdown(value))
            elif kind == "inline":
                pieces = []
                style = []
                for token in value:
                    if token.type in {"strong_open", "em_open"}:
                        style.append(
                            "bold" if token.type == "strong_open" else "italic"
                        )
                    elif token.type in {"strong_close", "em_close"}:
                        if style:
                            style.pop()
                    elif token.type == "math_inline":
                        widget = await self.graphic(renderer, "math", token.content)
                        assert widget.styles.width is not None
                        pieces.append((widget, int(widget.styles.width.value) + 2))
                    elif token.type in {
                        "text",
                        "code_inline",
                        "softbreak",
                        "hardbreak",
                    }:
                        for word in re.findall(r"\s+|\S+", token.content or " "):
                            widget = Static(
                                Text(word, style=" ".join(style)),
                                classes="lesson-inline-text",
                            )
                            widget.styles.width = max(1, cell_len(word))
                            pieces.append((widget, max(1, cell_len(word))))
                await self.mount(InlineMaterial(pieces))
            else:
                await self.mount(await self.graphic(renderer, kind, value))
                if caption:
                    await self.mount(
                        Static(caption, markup=False, classes="lesson-caption")
                    )

    async def graphic(self, renderer, kind, value):
        factory = image_widget()
        reason = None
        if factory is not None:
            try:
                path = await asyncio.to_thread(
                    renderer.render, kind, value, self.path, self.directory
                )
                kwargs = {}
                if factory.__name__ == "StableSixelImage":
                    kwargs = {
                        "paper_color": renderer.background,
                        "ink_color": renderer.foreground,
                    }
                widget = factory(
                    path, classes="formula" if kind == "math" else "figure", **kwargs
                )
                with PILImage.open(path) as image:
                    widget.styles.width = (
                        max(2, math.ceil(image.width / 12))
                        if kind == "math"
                        else min(60, max(12, math.ceil(image.width / 12)))
                    )
                widget.styles.max_width = "100%"
                widget.styles.height = "auto"
                return widget
            except (OSError, ValueError, subprocess.SubprocessError) as error:
                reason = (
                    str(error)
                    if not isinstance(error, subprocess.SubprocessError)
                    else "Formel oder Abbildung konnte nicht gerendert werden."
                )
        fallback = Static(
            value if kind == "math" else f"Abbildung: {value}",
            markup=False,
            classes="lesson-fallback",
        )
        fallback.styles.width = min(80, max(4, cell_len(value)))
        fallback.tooltip = (
            reason or "Grafikdarstellung ist in diesem Terminal nicht verfügbar."
        )
        if reason:
            self.notify(reason, severity="warning", timeout=8)
        return fallback


class InlineMaterial(Vertical):
    def __init__(self, pieces):
        super().__init__(classes="lesson-inline-flow")
        self.pieces = pieces
        self.built = False

    def on_mount(self):
        self.call_after_refresh(self.build_lines)

    def on_resize(self):
        self.call_after_refresh(self.build_lines)

    async def build_lines(self):
        width = self.content_size.width
        if width <= 1 or self.built:
            return
        self.built = True
        rows, row, used = [], [], 0
        for widget, size in self.pieces:
            if row and used + size > width:
                rows.append(Horizontal(*row, classes="lesson-inline-row"))
                row, used = [], 0
            row.append(widget)
            used += size
        if row:
            rows.append(Horizontal(*row, classes="lesson-inline-row"))
        await self.mount(*rows)
        self.refresh(layout=True)
