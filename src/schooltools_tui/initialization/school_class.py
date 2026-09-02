from pathlib import Path

from schooltools_tui.school_class import (
    SchoolClass,
    get_school_class_path,
    save_school_class,
)
from schooltools_tui.subject import load_subjects


class SchoolClassSetupError(ValueError):
    """Fehler beim anlegen einer Klasse."""


def initialize_school_class(root: Path, year: str, school_class: SchoolClass) -> None:
    class_directory = get_school_class_path(root, year, school_class.id).parent

    if class_directory.exists():
        raise SchoolClassSetupError(
            f"Die Klasse '{school_class.id}' existiert schon."
        )

    subjects_by_id = {subject.id: subject for subject in load_subjects(root)}

    for subject_id in school_class.subject_ids:
        subject = subjects_by_id.get(subject_id)

        if subject is None:
            raise SchoolClassSetupError(f"Das Fach '{subject_id}' existiert nicht.")

        if school_class.grade_level not in subject.grade_levels:
            raise SchoolClassSetupError(
                f"Das Fach '{subject.name}' ist für die "
                f"{school_class.grade_level}. Jahrgangsstufe nicht verfügbar."
            )

    class_directory.mkdir(parents=True, exist_ok=True)
    save_school_class(root, year, school_class)
