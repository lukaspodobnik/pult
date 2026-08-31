from dataclasses import dataclass
from pathlib import Path

from schooltools_tui.storage import load_toml


class SubjectFileError(ValueError):
    """Die Fächerdatei hat ein ungültiges Format"""


SUBJECTS_FILE_NAME = Path("subjects.toml")


@dataclass
class Subject:
    id: str
    name: str
    short_name: str


def load_subjects(root: Path) -> list[Subject]:
    path = root / SUBJECTS_FILE_NAME
    data = load_toml(path)

    if data is None:
        raise FileNotFoundError(f"Die Fächerdatei wurde nicht gefunden: {path}")

    subjects = data.get("subjects")

    if not isinstance(subjects, list):
        raise SubjectFileError("Die Fächerdatei muss eine Liste 'subjects' enthalten.")

    if len(subjects) == 0:
        raise SubjectFileError("Die Liste 'subjects' in der Fächerdatei darf nicht leer sein.")

    return [
        Subject(
            id=subject["id"], name=subject["name"], short_name=subject["short_name"]
        )
        for subject in subjects
    ]
