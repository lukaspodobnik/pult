from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from schooltools_tui.storage import load_toml, save_toml

APP_CONFIG_PATH = Path.home() / ".config" / "schooltools-tui" / "config.toml"

@dataclass
class AppConfig:
    data_directory: Path
    editor: str


def load_app_config() -> AppConfig | None:
    data = load_toml(APP_CONFIG_PATH)

    if data is None:
        return None

    return AppConfig(
        data_directory=Path(data["data_directory"]),
        editor=data["editor"],
    )

def save_app_config(app_config: AppConfig) -> None:
    data: dict[str, Any] = {
        "data_directory": str(app_config.data_directory),
        "editor": app_config.editor,
    }
    
    save_toml(APP_CONFIG_PATH, data)
