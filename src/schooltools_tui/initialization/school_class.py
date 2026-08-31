from pathlib import Path

from schooltools_tui.school_class import (
    SchoolClass,
    get_school_class_path,
    save_school_class,
)


class SchoolClassSetupError(ValueError):
    """Fehler beim anlegen einer Klasse."""


def initialize_school_class(root: Path, year: str, school_class: SchoolClass) -> None:
    class_directory = get_school_class_path(root, year, school_class.id).parent

    if class_directory.exists():
        raise SchoolClassSetupError(
            f"Die Klasse '{school_class.id}' existiert schon."
        )

    class_directory.mkdir(parents=True, exist_ok=True)
    save_school_class(root, year, school_class)
