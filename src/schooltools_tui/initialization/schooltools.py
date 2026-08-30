
from pathlib import Path

from schooltools_tui.config import AppConfig, save_app_config


class SetupError(Exception):
    """An expected error while setting up Schooltools."""

INITIAL_DIRECTORIES = (
    Path("sequences"),
    Path("school-years"),
)

def initialize_schooltools(root: str, editor: str) -> AppConfig:
    root = root.strip()
    editor = editor.strip()

    if not root:
        raise SetupError("Bitte gib ein Datenverzeichnis an.")

    if not editor:
        raise SetupError("Bitte gib einen Editor an.")

    root_path = Path(root).expanduser()

    if root_path.exists() and not root_path.is_dir():
        raise SetupError("Der angegebene Pfad ist kein Verzeichnis.")

    try:
        _create_initial_directories(root_path)
    except OSError as error:
        raise SetupError(
            f"Das Datenverzeichnis konnte nicht initialisiert werden: {error}"
        ) from error

    app_config = AppConfig(
        root=root_path,
        editor=editor,
        active_school_year=None,
    )

    try:
        save_app_config(app_config)
    except OSError as error:
        raise SetupError(
            f"Die Konfiguration konnte nicht gespeichert werden: {error}"
        ) from error

    return app_config


def _create_initial_directories(root_path: Path) -> None:
    for relative_path in INITIAL_DIRECTORIES:
        directory = root_path / relative_path
        directory.mkdir(parents=True, exist_ok=True)
