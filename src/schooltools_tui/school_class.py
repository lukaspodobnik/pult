import re
from dataclasses import dataclass
from pathlib import Path

from schooltools_tui.storage import load_toml, save_toml

CLASS_FILE_NAME = Path("class.toml")


@dataclass
class SchoolClass:
    id: str
    grade_level: int
    subject_ids: list[str]

    def __post_init__(self) -> None:
        self.id = self.id.strip().upper()

        if not self.id or self.id[0] not in "0123456789":
            raise ValueError("Die Klassenbezeichnung muss mit einer Zahl beginnen.")

        if any(character.isspace() for character in self.id):
            raise ValueError("Die Klassenbezeichnung darf keine Leerzeichen enthalten.")

        if (
            isinstance(self.grade_level, bool)
            or not isinstance(self.grade_level, int)
            or not 5 <= self.grade_level <= 13
        ):
            raise ValueError("Die Jahrgangsstufe muss zwischen 5 und 13 liegen.")

        if not self.subject_ids:
            raise ValueError("Es muss mindestens ein Fach gewählt werden.")


def school_class_sort_key(school_class: SchoolClass) -> tuple[int, str]:
    match = re.fullmatch(r"([0-9]+)(.*)", school_class.id)
    assert match is not None

    number, suffix = match.groups()
    return int(number), suffix


def get_school_class_path(root: Path, year: str, school_class_id: str) -> Path:
    return root / "school-years" / year / "classes" / school_class_id / CLASS_FILE_NAME


def load_school_class(root: Path, year: str, school_class_id: str) -> SchoolClass:
    path = get_school_class_path(root, year, school_class_id)
    data = load_toml(path)

    return SchoolClass(
        id=data["id"],
        grade_level=data["grade_level"],
        subject_ids=data["subject_ids"],
    )


def load_school_classes(root: Path, year: str) -> list[SchoolClass]:
    classes_directory = root / "school-years" / year / "classes"

    school_classes = []

    for class_directory in classes_directory.iterdir():
        if not class_directory.is_dir():
            continue

        school_class = load_school_class(
            root,
            year,
            class_directory.name,
        )
        school_classes.append(school_class)

    school_classes.sort(key=school_class_sort_key)
    return school_classes


def save_school_class(root: Path, year: str, school_class: SchoolClass) -> None:
    data = {
        "id": school_class.id,
        "grade_level": school_class.grade_level,
        "subject_ids": school_class.subject_ids,
    }

    path = get_school_class_path(root, year, school_class.id)
    save_toml(path, data)
