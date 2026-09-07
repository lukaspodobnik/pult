from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path

from pult.config import AppConfig, save_app_config
from pult.initialization.school_year import initialize_school_year
from pult.school.calendar import (
    CALENDARS_DIRECTORY_NAME,
    CalendarFileError,
)
from pult.school.period import PERIODS_FILE_NAME as periods_file
from pult.school.subject import SUBJECTS_FILE_NAME as subject_file


class SetupError(Exception):
    """An expected error while setting up Pult."""


INITIAL_DIRECTORIES = (
    Path("sequences"),
    CALENDARS_DIRECTORY_NAME,
    Path("school-years"),
)

DEFAULT_FILES = (
    subject_file,
    periods_file,
)

DEFAULT_DIRECTORIES = (
    Path("sequences"),
    CALENDARS_DIRECTORY_NAME,
)


def initialize_pult(root: str, editor: str, year: str) -> AppConfig:
    """Initialisiere Datenverzeichnis und Schuljahr und speichere danach die Config."""
    root = root.strip()
    editor = editor.strip()
    year = year.strip()

    if not root:
        raise SetupError("Bitte gib ein Datenverzeichnis an.")

    if not editor:
        raise SetupError("Bitte gib einen Editor an.")

    if not year:
        raise SetupError("Bitte wähle ein Schuljahr aus.")

    root_path = Path(root).expanduser()

    if root_path.exists() and not root_path.is_dir():
        raise SetupError("Der angegebene Pfad ist kein Verzeichnis.")

    try:
        _create_initial_directories(root_path)
        _create_default_files(root_path)
        _create_default_directories(root_path)
        initialize_school_year(root_path, year)
    except (OSError, CalendarFileError) as error:
        raise SetupError(
            f"Das Datenverzeichnis konnte nicht initialisiert werden: {error}"
        ) from error

    app_config = AppConfig(
        root=root_path,
        editor=editor,
        active_school_year=year,
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


def _create_default_files(root_path: Path) -> None:
    for default_file_path in DEFAULT_FILES:
        destination = root_path / default_file_path

        if destination.exists():
            continue

        file = files("pult.defaults") / default_file_path
        content = file.read_text(encoding="utf-8")

        destination.write_text(content, encoding="utf-8")


def _create_default_directories(root_path: Path) -> None:
    defaults = files("pult.defaults")

    for relative_path in DEFAULT_DIRECTORIES:
        source = defaults.joinpath(*relative_path.parts)

        if not source.is_dir():
            continue

        destination = root_path / relative_path
        _copy_default_directory(source, destination)


def _copy_default_directory(source: Traversable, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)

    for source_item in source.iterdir():
        destination_item = destination / source_item.name

        if source_item.is_dir():
            _copy_default_directory(source_item, destination_item)
        elif not destination_item.exists():
            destination_item.write_bytes(source_item.read_bytes())
