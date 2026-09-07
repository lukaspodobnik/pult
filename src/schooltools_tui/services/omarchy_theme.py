"""Lies Omarchys aktive Palette; ändere weder Theme-Dateien noch Systemeinstellungen."""

import re
import tomllib
from pathlib import Path
from typing import Any

from textual.color import Color
from textual.theme import Theme


def get_omarchy_palette_path() -> Path:
    """Pfad der aktiven Palette in der installierten Omarchy-Version."""
    return Path.home() / ".local/state/omarchy/current/theme/colors.toml"


def theme_from_palette(data: dict[str, Any]) -> Theme:
    """Validiere Grundfarben und ordne sie den semantischen Textual-Farben zu."""

    def color(key: str, fallback: str | None = None) -> str:
        value = data.get(key, fallback)
        if (
            not isinstance(value, str)
            or re.fullmatch(r"#[0-9a-fA-F]{6}", value) is None
        ):
            raise ValueError(f"Ungültige oder fehlende Omarchy-Farbe: {key}")
        return value.lower()

    background = color("background")
    foreground = color("foreground")
    accent = color("accent")
    mode = data.get("mode")
    if mode is not None and mode not in ("light", "dark"):
        raise ValueError("Omarchy-Modus muss 'light' oder 'dark' sein.")
    dark = (
        mode == "dark" if mode is not None else Color.parse(background).brightness < 0.5
    )
    selection = color("selection", color("lighter_background", background))
    muted = color("muted", color("dark_foreground", foreground))
    return Theme(
        name="omarchy",
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
            "input-selection-background": selection,
            "footer-key-foreground": accent,
        },
    )


class OmarchyThemeWatcher:
    """Prüfe Dateimetadaten; liefere nur eine geänderte, gültige Palette zurück."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path if path is not None else get_omarchy_palette_path()
        self._signature: tuple[int, int, int, int, int] | None = None
        self._theme: Theme | None = None
        self.last_error: str | None = None

    def poll(self) -> Theme | None:
        """Behalte bei fehlender/defekter Datei das letzte gültige Theme bei."""
        try:
            stat = self.path.stat()
            signature = (
                stat.st_dev,
                stat.st_ino,
                stat.st_mtime_ns,
                stat.st_ctime_ns,
                stat.st_size,
            )
            if signature == self._signature:
                self.last_error = None
                return None
            # Omarchy ersetzt beim Wechsel das Verzeichnis: nicht nur mtime prüfen.
            with self.path.open("rb") as file:
                theme = theme_from_palette(tomllib.load(file))
        except (OSError, ValueError) as error:
            self.last_error = str(error)
            return None

        self._signature = signature
        self.last_error = None
        if theme == self._theme:
            return None
        self._theme = theme
        return theme
