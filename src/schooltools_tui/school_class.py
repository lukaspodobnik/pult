from dataclasses import dataclass
from pathlib import Path


@dataclass
class SchoolClass:
    id: str
    subject_ids: list[str]


def load_school_classes() -> list[SchoolClass]:
    return []


def save_school_class(root: Path, year: str, school_class: SchoolClass) -> None:
    pass
