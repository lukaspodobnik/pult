import re
from dataclasses import dataclass

ID_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def validate_id(value: str, field_name: str) -> str:
    value = value.strip().lower()

    if not ID_PATTERN.fullmatch(value):
        raise ValueError(
            f"{field_name} darf nur Kleinbuchstaben, Zahlen "
            "und einzelne Bindestriche enthalten."
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
    subject_id: str
    grade_level: int
    title: str
    recommended_lesson_count: int
    lessons: list[Lesson]

    def __post_init__(self) -> None:
        self.id = validate_id(self.id, "Die Sequenz-ID")
        self.subject_id = validate_id(self.subject_id, "Die Fach-ID")
        self.title = self.title.strip()

        if self.grade_level < 5:
            raise ValueError("Die Jahrgangsstufe muss mindestsns 5 sein.")

        if self.grade_level > 13:
            raise ValueError("Die Jahrgangsstufe darf höchstens 13 sein.")

        if not self.title:
            raise ValueError("Die Sequenz benötigt einen Titel.")

        if self.recommended_lesson_count < 1:
            raise ValueError("Die empfohlene Stundenzahl muss größer als 0 sein.")

        if not self.lessons:
            raise ValueError("Eine Sequenz muss mindestens eine Stunde enthalten.")

        lesson_ids = [lesson.id for lesson in self.lessons]
        if len(lesson_ids) != len(set(lesson_ids)):
            raise ValueError(
                "Jede Stunden-ID darf innerhalb einer Sequenz nur einmal vorkommen."
            )
