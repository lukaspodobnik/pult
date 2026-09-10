"""CommonMark parsing and cached mathematical rendering for the prototype."""

import hashlib
import os
import subprocess
from pathlib import Path

from markdown_it import MarkdownIt
from mdit_py_plugins.dollarmath import dollarmath_plugin
from PIL import Image

BASE = Path(__file__).resolve().parent
CACHE = BASE / ".cache"
CACHE.mkdir(exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(CACHE / "matplotlib"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

BACKGROUND = "#18252b"
FOREGROUND = "#e7ece7"
ACCENT = "#a9d6bf"

PARSER = MarkdownIt("commonmark").enable("table").use(dollarmath_plugin)


def blocks(source: str):
    """Use CommonMark source maps: fenced code never becomes mathematics."""
    tokens = PARSER.parse(source)
    lines = source.splitlines(keepends=True)
    cursor = 0
    for token in tokens:
        kind = None
        if token.type == "math_block":
            kind, value, caption = "math", token.content, ""
        elif token.type == "inline" and token.children:
            children = token.children
            if len(children) == 1 and children[0].type == "image":
                kind, value, caption = (
                    "image",
                    children[0].attrGet("src"),
                    children[0].content,
                )
            elif any(child.type == "math_inline" for child in children):
                kind, value, caption = "inline", children, ""
        if kind is None or token.map is None:
            continue
        start, end = token.map
        if start > cursor:
            yield "text", "".join(lines[cursor:start]), ""
        yield kind, value, caption
        cursor = end
    if cursor < len(lines):
        yield "text", "".join(lines[cursor:]), ""


def formula_image(formula: str) -> Path:
    key = hashlib.sha256(("mathjax-tex-v1" + formula).encode()).hexdigest()[:20]
    path = CACHE / f"math-{key}.png"
    if not path.exists():
        svg = subprocess.run(
            ["node", str(BASE / "math.cjs")],
            input=formula,
            text=True,
            capture_output=True,
            check=True,
        ).stdout
        png = subprocess.run(
            ["rsvg-convert"], input=svg.encode(), capture_output=True, check=True
        ).stdout
        import io

        with Image.open(io.BytesIO(png)) as image:
            canvas = Image.new("RGBA", image.size, BACKGROUND)
            canvas.alpha_composite(image.convert("RGBA"))
            canvas.convert("RGB").save(path)
    return path


def figure_image(name: str) -> Path:
    if name not in {"bruchteile", "parabel"}:
        raise ValueError(f"Unbekannte Beispielabbildung: {name}")
    path = CACHE / f"{name}-cm-v2.png"
    if path.exists():
        return path
    fig, ax = plt.subplots(figsize=(8, 3.3), dpi=160, facecolor=BACKGROUND)
    ax.set_facecolor(BACKGROUND)
    if name == "bruchteile":
        for y, count, filled in [(1.2, 4, 3), (0.2, 8, 6)]:
            for i in range(count):
                ax.add_patch(
                    Rectangle(
                        (i * 6 / count, y),
                        6 / count,
                        0.65,
                        facecolor=ACCENT if i < filled else BACKGROUND,
                        edgecolor=FOREGROUND,
                        linewidth=1.6,
                    )
                )
            ax.text(
                6.3,
                y + 0.32,
                rf"$\frac{{{filled}}}{{{count}}}$",
                color=FOREGROUND,
                fontsize=22,
                math_fontfamily="cm",
                va="center",
            )
        ax.set(xlim=(-0.2, 7.3), ylim=(-0.1, 2.15))
        ax.axis("off")
    else:
        x = np.linspace(-2, 2, 401)
        y = x**2 - 1
        ax.plot(x, y, color=ACCENT, linewidth=2.5)
        ax.fill_between(x, 0, y, where=y >= 0, color=ACCENT, alpha=0.3)
        ax.fill_between(x, 0, y, where=y < 0, color="#e9b98a", alpha=0.4)
        ax.axhline(0, color=FOREGROUND, linewidth=0.8)
        ax.axvline(0, color=FOREGROUND, linewidth=0.8)
        ax.set(xlim=(-2.3, 2.3), ylim=(-1.5, 3.5), xticks=[-2, -1, 0, 1, 2])
        ax.tick_params(colors=FOREGROUND)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.grid(alpha=0.12, color=FOREGROUND)
        ax.text(
            0.12,
            2.7,
            r"$f(x) = x^2 - 1$",
            color=FOREGROUND,
            fontsize=16,
            math_fontfamily="cm",
        )
    fig.savefig(path, bbox_inches="tight", pad_inches=0.15, facecolor=BACKGROUND)
    plt.close(fig)
    return path


def prepare_assets(lessons: list[dict]) -> None:
    for lesson in lessons:
        files = [lesson["note"]]
        for task in lesson["tasks"]:
            files.extend([task["text"], task["solution"]])
        for file in files:
            for kind, value, _ in blocks((BASE / "materials" / file).read_text()):
                if kind == "math":
                    formula_image(value)
                elif kind == "inline":
                    for token in value:
                        if token.type == "math_inline":
                            formula_image(token.content)
                elif kind == "image":
                    figure_image(value)
