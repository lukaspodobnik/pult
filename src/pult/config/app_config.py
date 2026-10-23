from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pult.services.documents.document_fonts import validate_document_font
from pult.storage import load_toml, save_toml

APP_CONFIG_PATH = Path.home() / ".config" / "pult" / "config.toml"


@dataclass
class AppConfig:
    root: Path
    editor: str
    active_school_year: str
    document_font: str = "auto"
    export_author: str = ""


def validate_export_author(value: str) -> str:
    if not isinstance(value, str) or len(value) > 80 or "\n" in value or "\r" in value:
        raise ValueError(
            "Der Name auf Arbeitsblättern muss ein kurzer einzeiliger Text sein (maximal 80 Zeichen)."
        )
    return value.strip()


def load_app_config() -> AppConfig | None:
    """Lade die globale App-Konfiguration oder gib bei fehlender Datei None zurück."""
    try:
        data = load_toml(APP_CONFIG_PATH)
    except FileNotFoundError:
        return None

    root = data.get("root")
    if root is None:
        return None

    return AppConfig(
        root=Path(root),
        editor=data["editor"],
        active_school_year=data["active_school_year"],
        document_font=validate_document_font(data.get("document_font", "auto")),
        export_author=validate_export_author(data.get("export_author", "")),
    )


def save_app_config(app_config: AppConfig) -> None:
    """Speichere die vollständige globale App-Konfiguration."""
    data: dict[str, Any] = {
        "root": str(app_config.root),
        "editor": app_config.editor,
        "active_school_year": app_config.active_school_year,
        "document_font": validate_document_font(app_config.document_font),
        "export_author": validate_export_author(app_config.export_author),
    }

    APP_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    save_toml(APP_CONFIG_PATH, data)
