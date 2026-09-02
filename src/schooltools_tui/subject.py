import re
from dataclasses import dataclass
from pathlib import Path

from schooltools_tui.storage import load_toml


class SubjectFileError(ValueError):
    """Die Fächerdatei hat ein ungültiges Format"""


SUBJECTS_FILE_NAME = Path("subjects.toml")
SUBJECT_ID_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


@dataclass
class Subject:
    id: str
    name: str
    short_name: str
    grade_levels: list[int]

    def __post_init__(self) -> None:
        self.id = self.id.strip().lower()
        self.name = self.name.strip()
        self.short_name = self.short_name.strip()

        if not SUBJECT_ID_PATTERN.fullmatch(self.id):
            raise ValueError(
                "Die Fach-ID darf nur Kleinbuchstaben, Zahlen "
                "und einzelne Bindestriche enthalten."
            )

        if not self.name:
            raise ValueError("Das Fach benötigt einen Namen.")

        if not self.short_name:
            raise ValueError("Das Fach benötigt einen Kurznamen.")

        if not self.grade_levels:
            raise ValueError("Das Fach benötigt mindestens eine Jahrgangsstufe.")

        if any(
            isinstance(grade_level, bool)
            or not isinstance(grade_level, int)
            or not 5 <= grade_level <= 13
            for grade_level in self.grade_levels
        ):
            raise ValueError(
                "Die Jahrgangsstufen eines Fachs müssen zwischen 5 und 13 liegen."
            )

        if len(self.grade_levels) != len(set(self.grade_levels)):
            raise ValueError("Jede Jahrgangsstufe darf nur einmal vorkommen.")

        self.grade_levels.sort()


def load_subjects(root: Path) -> list[Subject]:
    path = root / SUBJECTS_FILE_NAME
    data = load_toml(path)

    subjects = data.get("subjects")

    if not isinstance(subjects, list):
        raise SubjectFileError("Die Fächerdatei muss eine Liste 'subjects' enthalten.")

    if len(subjects) == 0:
        raise SubjectFileError("Die Liste 'subjects' in der Fächerdatei darf nicht leer sein.")

    try:
        loaded_subjects = [
            Subject(
                id=subject["id"],
                name=subject["name"],
                short_name=subject["short_name"],
                grade_levels=subject["grade_levels"],
            )
            for subject in subjects
        ]
    except (KeyError, TypeError, ValueError) as error:
        raise SubjectFileError(f"Ungültige Fächerdatei: {error}") from error

    subject_ids = [subject.id for subject in loaded_subjects]
    if len(subject_ids) != len(set(subject_ids)):
        raise SubjectFileError("Jede Fach-ID darf nur einmal vorkommen.")

    return loaded_subjects
