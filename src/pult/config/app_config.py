from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pult.storage import load_toml, save_toml

APP_CONFIG_PATH = Path.home() / ".config" / "pult" / "config.toml"
# Nur für den Umstieg: bestehende Daten bleiben am bisherigen Ort.
LEGACY_APP_CONFIG_PATH = Path.home() / ".config" / "schooltools-tui" / "config.toml"


@dataclass
class AppConfig:
    root: Path
    editor: str
    active_school_year: str


def load_app_config() -> AppConfig | None:
    """Lade die globale App-Konfiguration oder gib bei fehlender Datei None zurück."""
    try:
        data = load_toml(APP_CONFIG_PATH)
    except FileNotFoundError:
        try:
            data = load_toml(LEGACY_APP_CONFIG_PATH)
        except FileNotFoundError:
            return None

    root = data.get("root")
    if root is None:
        return None

    return AppConfig(
        root=Path(root),
        editor=data["editor"],
        active_school_year=data["active_school_year"],
    )


def save_app_config(app_config: AppConfig) -> None:
    """Speichere die vollständige globale App-Konfiguration."""
    data: dict[str, Any] = {
        "root": str(app_config.root),
        "editor": app_config.editor,
        "active_school_year": app_config.active_school_year,
    }

    APP_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    save_toml(APP_CONFIG_PATH, data)
