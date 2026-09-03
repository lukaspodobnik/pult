import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from schooltools_tui.storage import load_toml, save_toml

ID_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
CURRICULUM_SECTION_ID_PATTERN = re.compile(
    r"[A-ZÄÖÜ]+[0-9]+ [0-9]+(?:\.[0-9]+)*"
)
SEQUENCES_DIRECTORY_NAME = Path("sequences")
SEQUENCE_FILE_SUFFIX = ".toml"


class SequenceFileError(ValueError):
    """Raised when a sequence file has invalid or inconsistent contents."""


def validate_id(value: str, field_name: str) -> str:
    value = value.strip().lower()

    if not ID_PATTERN.fullmatch(value):
        raise ValueError(
            f"{field_name} darf nur Kleinbuchstaben, Zahlen "
            "und einzelne Bindestriche enthalten."
        )

    return value


def validate_curriculum_section_id(value: str, field_name: str) -> str:
    value = " ".join(value.strip().upper().split())

    if not CURRICULUM_SECTION_ID_PATTERN.fullmatch(value):
        raise ValueError(
            f"{field_name} muss dem Format einer Lehrplangliederung entsprechen, "
            "z. B. 'M5 1' oder 'M5 1.1'."
        )

    return value


@dataclass
class Lesson:
    id: str
    title: str
    tasks: list[str]
    notes: str

    def __post_init__(self) -> None:
        self.id = validate_id(self.id, "Die Stunden-ID")
        self.title = self.title.strip()
        self.notes = self.notes.strip()

        if any(not task.strip() for task in self.tasks):
            raise ValueError("Aufgaben dürfen keine leeren Einträge enthalten.")

        self.tasks = [task.strip() for task in self.tasks]


@dataclass
class Sequence:
    id: str
    curriculum_section_id: str
    subject_id: str
    grade_level: int
    title: str
    recommended_lesson_count: int | None
    lessons: list[Lesson]
    chapter_id: str | None = None
    chapter_title: str | None = None

    def __post_init__(self) -> None:
        self.id = validate_id(self.id, "Die Sequenz-ID")
        self.curriculum_section_id = validate_curriculum_section_id(
            self.curriculum_section_id, "Die Lehrplanabschnitts-ID"
        )
        self.subject_id = validate_id(self.subject_id, "Die Fach-ID")
        self.title = self.title.strip()

        if self.grade_level < 5:
            raise ValueError("Die Jahrgangsstufe muss mindestens 5 sein.")

        if self.grade_level > 13:
            raise ValueError("Die Jahrgangsstufe darf höchstens 13 sein.")

        if not self.title:
            raise ValueError("Die Sequenz benötigt einen Titel.")

        if (self.chapter_id is None) != (self.chapter_title is None):
            raise ValueError(
                "Kapitel-ID und Kapiteltitel müssen gemeinsam angegeben werden."
            )

        if self.chapter_id is not None and self.chapter_title is not None:
            self.chapter_id = validate_curriculum_section_id(
                self.chapter_id, "Die Kapitel-ID"
            )
            self.chapter_title = self.chapter_title.strip()

            if not self.chapter_title:
                raise ValueError("Der Kapiteltitel darf nicht leer sein.")

        if self.recommended_lesson_count is not None:
            if (
                isinstance(self.recommended_lesson_count, bool)
                or not isinstance(self.recommended_lesson_count, int)
                or self.recommended_lesson_count < 1
            ):
                raise ValueError("Die empfohlene Stundenzahl muss größer als 0 sein.")

            if not self.lessons:
                raise ValueError(
                    "Eine Sequenz mit empfohlener Stundenzahl muss mindestens "
                    "eine Stunde enthalten."
                )

        lesson_ids = [lesson.id for lesson in self.lessons]
        if len(lesson_ids) != len(set(lesson_ids)):
            raise ValueError(
                "Jede Stunden-ID darf innerhalb einer Sequenz nur einmal vorkommen."
            )


def get_sequence_directory(
    root: Path,
    grade_level: int,
    subject_id: str,
) -> Path:
    if not 5 <= grade_level <= 13:
        raise ValueError("Die Jahrgangsstufe muss zwischen 5 und 13 liegen.")

    subject_id = validate_id(subject_id, "Die Fach-ID")
    return root / SEQUENCES_DIRECTORY_NAME / str(grade_level) / subject_id


def get_sequence_path(
    root: Path,
    grade_level: int,
    subject_id: str,
    sequence_id: str,
) -> Path:
    sequence_id = validate_id(sequence_id, "Die Sequenz-ID")
    return get_sequence_directory(root, grade_level, subject_id) / (
        sequence_id + SEQUENCE_FILE_SUFFIX
    )


def load_sequence(
    root: Path,
    grade_level: int,
    subject_id: str,
    sequence_id: str,
) -> Sequence:
    path = get_sequence_path(root, grade_level, subject_id, sequence_id)
    data = load_toml(path)

    try:
        lessons_data = data["lessons"]
        if not isinstance(lessons_data, list):
            raise TypeError("'lessons' muss eine Liste sein.")

        sequence = Sequence(
            id=_require_string(data, "id"),
            curriculum_section_id=_require_string(data, "curriculum_section_id"),
            subject_id=_require_string(data, "subject_id"),
            grade_level=_require_integer(data, "grade_level"),
            title=_require_string(data, "title"),
            recommended_lesson_count=_optional_integer(
                data, "recommended_lesson_count"
            ),
            lessons=[
                _load_lesson(lesson_data, index)
                for index, lesson_data in enumerate(lessons_data, start=1)
            ],
            chapter_id=_optional_string(data, "chapter_id"),
            chapter_title=_optional_string(data, "chapter_title"),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise SequenceFileError(f"Ungültige Sequenzdatei '{path}': {error}") from error

    expected_subject_id = validate_id(subject_id, "Die Fach-ID")
    expected_sequence_id = validate_id(sequence_id, "Die Sequenz-ID")
    if (
        sequence.grade_level != grade_level
        or sequence.subject_id != expected_subject_id
        or sequence.id != expected_sequence_id
    ):
        raise SequenceFileError(
            f"Die Angaben in '{path}' stimmen nicht mit ihrem Ablageort überein."
        )

    return sequence


def load_sequences(
    root: Path,
    grade_level: int,
    subject_id: str,
) -> list[Sequence]:
    directory = get_sequence_directory(root, grade_level, subject_id)
    paths = sorted(directory.glob(f"*{SEQUENCE_FILE_SUFFIX}"))
    return [load_sequence(root, grade_level, subject_id, path.stem) for path in paths]


def load_sequence_library(root: Path) -> list[Sequence]:
    library_directory = root / SEQUENCES_DIRECTORY_NAME
    grade_directories: list[tuple[int, Path]] = []

    for grade_directory in library_directory.iterdir():
        if not grade_directory.is_dir():
            continue

        try:
            grade_level = int(grade_directory.name)
        except ValueError as error:
            raise SequenceFileError(
                f"Ungültiges Jahrgangsstufenverzeichnis '{grade_directory}'."
            ) from error

        if not 5 <= grade_level <= 13:
            raise SequenceFileError(
                f"Ungültiges Jahrgangsstufenverzeichnis '{grade_directory}'."
            )

        grade_directories.append((grade_level, grade_directory))

    sequences: list[Sequence] = []
    for grade_level, grade_directory in sorted(grade_directories):
        subject_directories = sorted(
            path for path in grade_directory.iterdir() if path.is_dir()
        )
        for subject_directory in subject_directories:
            sequences.extend(
                load_sequences(root, grade_level, subject_directory.name)
            )

    return sequences


def save_sequence(root: Path, sequence: Sequence) -> None:
    path = get_sequence_path(
        root,
        sequence.grade_level,
        sequence.subject_id,
        sequence.id,
    )
    data: dict[str, Any] = {
        "id": sequence.id,
        "curriculum_section_id": sequence.curriculum_section_id,
        "subject_id": sequence.subject_id,
        "grade_level": sequence.grade_level,
        "title": sequence.title,
        "lessons": [
            {
                "id": lesson.id,
                "title": lesson.title,
                "tasks": lesson.tasks,
                "notes": lesson.notes,
            }
            for lesson in sequence.lessons
        ],
    }

    if sequence.recommended_lesson_count is not None:
        data["recommended_lesson_count"] = sequence.recommended_lesson_count

    if sequence.chapter_id is not None and sequence.chapter_title is not None:
        data["chapter_id"] = sequence.chapter_id
        data["chapter_title"] = sequence.chapter_title

    save_toml(path, data)


def _load_lesson(data: Any, index: int) -> Lesson:
    if not isinstance(data, dict):
        raise TypeError(f"Stunde {index} muss eine TOML-Tabelle sein.")

    tasks = data.get("tasks")
    if not isinstance(tasks, list) or any(not isinstance(task, str) for task in tasks):
        raise TypeError(f"'tasks' von Stunde {index} muss eine Liste aus Texten sein.")

    return Lesson(
        id=_require_string(data, "id"),
        title=_require_string(data, "title"),
        tasks=tasks,
        notes=_require_string(data, "notes"),
    )


def _require_string(data: dict[str, Any], key: str) -> str:
    value = data[key]
    if not isinstance(value, str):
        raise TypeError(f"'{key}' muss ein Text sein.")
    return value


def _optional_string(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    if value is not None and not isinstance(value, str):
        raise TypeError(f"'{key}' muss ein Text sein.")
    return value


def _require_integer(data: dict[str, Any], key: str) -> int:
    value = data[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"'{key}' muss eine ganze Zahl sein.")
    return value


def _optional_integer(data: dict[str, Any], key: str) -> int | None:
    value = data.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"'{key}' muss eine ganze Zahl sein.")
    return value
