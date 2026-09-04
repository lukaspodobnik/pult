from pathlib import Path

from schooltools_tui.class_progress import (
    ActiveSequence,
    ClassProgress,
    save_class_progress,
    validate_class_progress,
)
from schooltools_tui.school_class import (
    SchoolClass,
    get_school_class_path,
    save_school_class,
)
from schooltools_tui.sequence import load_sequence_library, sequence_sort_key
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
    sequences = load_sequence_library(root)

    for subject_id in school_class.subject_ids:
        subject = subjects_by_id.get(subject_id)

        if subject is None:
            raise SchoolClassSetupError(f"Das Fach '{subject_id}' existiert nicht.")

        if school_class.grade_level not in subject.grade_levels:
            raise SchoolClassSetupError(
                f"Das Fach '{subject.name}' ist für die "
                f"{school_class.grade_level}. Jahrgangsstufe nicht verfügbar."
            )

    active_sequences: list[ActiveSequence] = []
    for subject_id in school_class.subject_ids:
        subject_sequences = [
            sequence
            for sequence in sequences
            if sequence.grade_level == school_class.grade_level
            and sequence.subject_id == subject_id
        ]
        if not subject_sequences:
            raise SchoolClassSetupError(
                f"Für das Fach '{subjects_by_id[subject_id].name}' existieren in "
                f"der {school_class.grade_level}. Jahrgangsstufe keine Sequenzen."
            )

        first_sequence = min(subject_sequences, key=sequence_sort_key)
        active_sequences.append(
            ActiveSequence(
                subject_id=subject_id,
                sequence_id=first_sequence.id,
            )
        )

    class_progress = ClassProgress(
        active_sequences=tuple(active_sequences),
        entries=(),
    )
    validate_class_progress(class_progress, school_class, sequences)

    class_directory.mkdir(parents=True, exist_ok=True)
    save_school_class(root, year, school_class)
    save_class_progress(root, year, school_class.id, class_progress)
