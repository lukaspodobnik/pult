"""Gemeinsame Darstellungsregeln für PULT- und Omarchy-Paletten."""

import re
from typing import Any

from textual.color import Color
from textual.theme import Theme

PULT_PALETTE = {
    "mode": "dark",
    "background": "#202428",
    "dark_background": "#1b1f23",
    "foreground": "#d8dde2",
    "muted": "#9aa5af",
    "accent": "#d6a06d",
    "blue": "#91adbf",
    "selection": "#394650",
    "green": "#a3be8c",
    "yellow": "#d8be86",
    "red": "#cf9295",
}


def theme_from_palette(data: dict[str, Any], *, name: str = "omarchy") -> Theme:
    """Validiere Grundfarben und ordne sie den semantischen Textual-Farben zu."""

    def color(key: str, fallback: str | None = None) -> str:
        value = data.get(key, fallback)
        if (
            not isinstance(value, str)
            or re.fullmatch(r"#[0-9a-fA-F]{6}", value) is None
        ):
            raise ValueError(f"Ungültige oder fehlende Palettenfarbe: {key}")
        return value.lower()

    background = color("background")
    foreground = color("foreground")
    accent = color("accent")
    mode = data.get("mode")
    if mode is not None and mode not in ("light", "dark"):
        raise ValueError("Palettenmodus muss 'light' oder 'dark' sein.")
    dark = (
        mode == "dark" if mode is not None else Color.parse(background).brightness < 0.5
    )
    selection = color("selection", color("lighter_background", background))
    muted = color("muted", color("dark_foreground", foreground))
    return Theme(
        name=name,
        primary=accent,
        accent=accent,
        secondary=color("blue", accent),
        success=color("green"),
        warning=color("yellow"),
        error=color("red"),
        background=background,
        foreground=foreground,
        surface=background,
        panel=color("dark_background", background),
        dark=dark,
        variables={
            "foreground-muted": muted,
            "text-muted": muted,
            "text-accent": accent,
            "border": accent,
            "border-blurred": muted,
            "block-cursor-background": selection,
            "block-cursor-foreground": foreground,
            "block-cursor-text-style": "bold",
            "block-cursor-blurred-background": selection,
            "block-cursor-blurred-foreground": foreground,
            "block-cursor-blurred-text-style": "none",
            "input-selection-background": selection,
            "footer-key-foreground": accent,
            "footer-background": background,
            "footer-key-background": background,
            "footer-description-background": background,
            "footer-item-background": background,
        },
    )


def standard_theme() -> Theme:
    """Dezentes dunkles Standardtheme ohne Abhängigkeit vom Systemtheme."""
    return theme_from_palette(PULT_PALETTE, name="pult")
