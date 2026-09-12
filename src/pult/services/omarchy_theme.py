"""Lies Omarchys aktive Palette; ändere weder Theme-Dateien noch Systemeinstellungen."""

import tomllib
from pathlib import Path

from textual.theme import Theme

from pult.services.themes import theme_from_palette as theme_from_palette


def get_omarchy_palette_path() -> Path:
    """Pfad der aktiven Palette in der installierten Omarchy-Version."""
    return Path.home() / ".local/state/omarchy/current/theme/colors.toml"


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
