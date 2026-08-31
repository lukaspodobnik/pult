from dataclasses import dataclass
from pathlib import Path

from schooltools_tui.storage import load_toml, save_toml

CLASS_FILE_NAME = Path("class.toml")


@dataclass
class SchoolClass:
    id: str
    subject_ids: list[str]

    def __post_init__(self) -> None:
        self.id = self.id.strip().upper()


def get_school_class_path(root: Path, year: str, school_class_id: str) -> Path:
    return (
        root
        / "school-years"
        / year
        / "classes"
        / school_class_id
        / CLASS_FILE_NAME
    )


def load_school_class(root: Path, year: str, school_class_id: str) -> SchoolClass:
    path = get_school_class_path(root, year, school_class_id)
    data = load_toml(path)

    return SchoolClass(
        id=data["id"],
        subject_ids=data["subject_ids"],
    )


def save_school_class(root: Path, year: str, school_class: SchoolClass) -> None:
    data = {
        "id": school_class.id,
        "subject_ids": school_class.subject_ids,
    }

    path = get_school_class_path(root, year, school_class.id)
    save_toml(path, data)
