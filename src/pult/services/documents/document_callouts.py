"""Beschriftete Markdown-Blöcke und zum Theme passende Blau-/Orangetöne."""

import colorsys
import re
from collections.abc import Mapping

from markdown_it import MarkdownIt
from markdown_it.rules_core import StateCore
from markdown_it.token import Token
from mdit_py_plugins.dollarmath import dollarmath_plugin

from pult.services.documents.document_figures import figures_plugin
from pult.services.documents.document_replacements import (
    literal_math_plugin,
    replacements_plugin,
)
from pult.services.documents.document_subtasks import subtasks_plugin

CALLOUT_LABELS = {"definition": "Definition", "merksatz": "Merke"}
CALLOUT_MARKER = re.compile(r"^\[!(definition|merksatz)\](?:[ \t]+(.*))?$", re.I)
HEX_COLOR = re.compile(r"#[0-9a-fA-F]{6}")


def callouts_plugin(md: MarkdownIt) -> None:
    def callouts(state: StateCore) -> None:
        result: list[Token] = []
        tokens = state.tokens
        index = 0
        while index < len(tokens):
            quote = tokens[index]
            result.append(quote)
            index += 1
            if (
                quote.type != "blockquote_open"
                or index + 2 >= len(tokens)
                or [token.type for token in tokens[index : index + 3]]
                != ["paragraph_open", "inline", "paragraph_close"]
            ):
                continue
            paragraph, inline, closing = tokens[index : index + 3]
            first_line, _, body = inline.content.partition("\n")
            match = CALLOUT_MARKER.fullmatch(first_line.rstrip())
            if match is None:
                continue
            kind = match[1].lower()
            title = (match[2] or "").strip()
            quote.attrJoin("class", f"callout callout-{kind}")
            quote.attrSet("data-callout", kind)
            result.extend(
                [
                    Token(
                        "paragraph_open",
                        "p",
                        1,
                        level=paragraph.level,
                        attrs={"class": "callout-title"},
                    ),
                    Token(
                        "inline",
                        "",
                        0,
                        level=inline.level,
                        content=CALLOUT_LABELS[kind] + (f" · {title}" if title else ""),
                    ),
                    Token("paragraph_close", "p", -1, level=closing.level),
                ]
            )
            if body:
                inline.content = body
                result.extend([paragraph, inline, closing])
            index += 3
        state.tokens = result

    # Transform parsed blockquotes, never literal examples inside code fences.
    # Running before inline parsing preserves math, emphasis, links and images.
    md.core.ruler.before("inline", "pult_callouts", callouts)


def text_document_parser(replacements: Mapping[str, str] | None = None) -> MarkdownIt:
    """Dieselben Beschriftungen im Terminal; TeX bleibt lesbarer Quelltext."""
    return (
        MarkdownIt("gfm-like", {"html": False})
        .use(dollarmath_plugin)
        .use(callouts_plugin)
        .use(subtasks_plugin, text_only=True)
        .use(figures_plugin, text_only=True)
        .use(replacements_plugin, replacements)
        .use(literal_math_plugin)
    )


def _rgb(color: str) -> tuple[float, float, float]:
    return (
        int(color[1:3], 16) / 255,
        int(color[3:5], 16) / 255,
        int(color[5:7], 16) / 255,
    )


def _luminance(rgb: tuple[float, float, float]) -> float:
    channels = [
        v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in rgb
    ]
    return sum(v * weight for v, weight in zip(channels, (0.2126, 0.7152, 0.0722)))


def _contrast(
    first: tuple[float, float, float], second: tuple[float, float, float]
) -> float:
    light, dark = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def _readable_color(color: str, background: str) -> str:
    rgb, bg = _rgb(color), _rgb(background)
    hue, lightness, saturation = colorsys.rgb_to_hls(*rgb)
    direction = 1 if _luminance(bg) < 0.18 else -1
    for _ in range(101):
        # Match the 7% tint of the callout surface, not just the page background.
        surface = (
            rgb[0] * 0.07 + bg[0] * 0.93,
            rgb[1] * 0.07 + bg[1] * 0.93,
            rgb[2] * 0.07 + bg[2] * 0.93,
        )
        if _contrast(rgb, surface) >= 4.6:
            break
        # Retain the hue even on unusual mid-gray themes instead of becoming white/black.
        adjusted = max(0.08, min(0.92, lightness + direction * 0.01))
        if adjusted == lightness:
            break
        lightness = adjusted
        rgb = colorsys.hls_to_rgb(hue, lightness, saturation)
    return "#" + "".join(f"{round(channel * 255):02x}" for channel in rgb)


def resolve_callout_colors(
    background: str, palette: Mapping[str, str]
) -> tuple[str, str]:
    """Farbfamilien stabil halten; passende Palettenfarben bevorzugen."""
    dark = _luminance(_rgb(background)) < 0.18
    colors = []
    for keys, hue_range, fallback in (
        (
            ("document-definition", "blue", "secondary", "primary", "accent"),
            (190, 250),
            "#91adbf" if dark else "#38698e",
        ),
        (
            ("document-merksatz", "orange", "peach", "accent", "primary", "warning"),
            (15, 43),
            "#d6a06d" if dark else "#99561f",
        ),
    ):
        selected = fallback
        for key in keys:
            candidate = palette.get(key, "")
            if not HEX_COLOR.fullmatch(candidate):
                continue
            hue, _, saturation = colorsys.rgb_to_hls(*_rgb(candidate))
            if hue_range[0] <= hue * 360 <= hue_range[1] and saturation >= 0.15:
                selected = candidate
                break
        colors.append(_readable_color(selected, background))
    return colors[0], colors[1]
