from pathlib import Path

from schooltools_tui.config import AppConfig, save_app_config


class SetupError(Exception):
    """An expected error while setting up Schooltools."""


def initialize_schooltools(data_directory: str, editor: str) -> AppConfig:
    data_directory = data_directory.strip()
    editor = editor.strip()

    if not data_directory:
        raise SetupError("Bitte gib ein Datenverzeichnis an.")

    if not editor:
        raise SetupError("Bitte gib einen Editor an.")

    path = Path(data_directory).expanduser()

    if path.exists() and not path.is_dir():
        raise SetupError("Der angegebene Pfad ist kein Verzeichnis.")

    app_config = AppConfig(
        data_directory=path,
        editor=editor,
    )

    try:
        save_app_config(app_config)
    except OSError as error:
        raise SetupError(
            f"Die Konfiguration konnte nicht gespeichert werden: {error}"
        ) from error

    return app_config
