"""Stunden und Aufgaben gemäß dem Materialvertrag; unabhängig von Klassen."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tomli_w

from pult.storage import load_toml

PHASE_TEMPLATE = """
# Vorschlag: Nur die benötigten Phasen verwenden.
# Zuerst phasen = [] oben entfernen, dann die gewünschten Phasen unten
# aktivieren (führende # entfernen) und jeweils einen nicht leeren Text ergänzen.

# [[phasen]]
# titel = "Einstieg"
# text = ""

# [[phasen]]
# titel = "Erarbeitung"
# text = ""

# [[phasen]]
# titel = "Übung"
# text = ""

# [[phasen]]
# titel = "Auswertung"
# text = ""

# [[phasen]]
# titel = "Schluss"
# text = ""
"""


def lesson_metadata_source(lesson: "Lesson") -> str:
    """Schreibe die erlaubten Felder mit kurzen Ausfüllhinweisen."""
    fields = [
        ("titel", lesson.title, "Titel der Stunde."),
        ("ziele", lesson.goals, "Lernziele als kurze Aussagen."),
        (
            "material",
            lesson.material,
            "Benötigtes Material, z. B. Lineal oder Arbeitsblatt.",
        ),
        (
            "aufgaben",
            [t.id for t in lesson.tasks],
            "Aufgaben-IDs aus aufgaben/, in geplanter Reihenfolge.",
        ),
        (
            "phasen",
            [{"titel": p.title, "text": p.text} for p in lesson.phases],
            "Geordneter Verlauf ohne Zeitangaben.",
        ),
    ]
    source = "\n".join(
        f"# {hint}\n{tomli_w.dumps({key: value})}" for key, value, hint in fields
    )
    return source + (PHASE_TEMPLATE if not lesson.phases else "")


ID_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def validate_id(value: str, field_name: str) -> str:
    value = value.strip().lower()
    if not ID_PATTERN.fullmatch(value):
        raise ValueError(
            f"{field_name} darf nur Kleinbuchstaben, Zahlen und einzelne Bindestriche enthalten."
        )
    return value


def require_text(data: dict[str, Any], key: str) -> str:
    value = data[key]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{key}' muss ein nicht leerer Text sein.")
    return value


def text_list(data: dict[str, Any], key: str) -> list[str]:
    values = data.get(key, [])
    if not isinstance(values, list) or any(
        not isinstance(v, str) or not v.strip() for v in values
    ):
        raise ValueError(f"'{key}' muss eine Liste nicht leerer Texte sein.")
    return values


def reference_ids(data: dict[str, Any], key: str) -> list[str]:
    values = text_list(data, key)
    for value in values:
        if validate_id(value, key) != value:
            raise ValueError(f"'{key}' enthält eine nicht kanonische ID: {value!r}.")
    if len(set(values)) != len(values):
        raise ValueError(f"'{key}' enthält doppelte IDs.")
    return values


def reject_unknown(data: dict[str, Any], allowed: set[str]) -> None:
    unknown = data.keys() - allowed
    if unknown:
        raise ValueError(f"Unbekannte Felder: {', '.join(sorted(unknown))}.")


@dataclass
class Phase:
    title: str
    text: str

    def __post_init__(self) -> None:
        self.title = require_text({"titel": self.title}, "titel").strip()
        self.text = require_text({"text": self.text}, "text").strip()


@dataclass
class Task:
    id: str
    text: str
    solution: str | None = None

    def __post_init__(self) -> None:
        self.id = validate_id(self.id, "Die Aufgaben-ID")
        if not isinstance(self.text, str) or (
            self.solution is not None and not isinstance(self.solution, str)
        ):
            raise ValueError("Aufgabe und Lösung müssen Markdown-Texte sein.")


@dataclass
class Lesson:
    id: str
    title: str
    tasks: list[Task] = field(default_factory=list)
    preparation: str | None = None
    goals: list[str] = field(default_factory=list)
    material: list[str] = field(default_factory=list)
    phases: list[Phase] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.id = validate_id(self.id, "Die Stunden-ID")
        self.title = require_text({"titel": self.title}, "titel").strip()
        self.goals = [v.strip() for v in text_list({"ziele": self.goals}, "ziele")]
        self.material = [
            v.strip() for v in text_list({"material": self.material}, "material")
        ]
        if self.preparation is not None and not isinstance(self.preparation, str):
            raise ValueError("Die Vorbereitung muss Markdown-Text sein.")
        if any(not isinstance(task, Task) for task in self.tasks):
            raise ValueError("Aufgaben müssen aufgelöste Aufgabenobjekte sein.")
        if len({t.id for t in self.tasks}) != len(self.tasks):
            raise ValueError(
                "Eine Aufgabe darf pro Stunde nur einmal referenziert werden."
            )
        if any(not isinstance(phase, Phase) for phase in self.phases):
            raise ValueError("Der Verlauf muss aus Phasen bestehen.")

    @property
    def task_summary(self) -> str:
        return " · ".join(task.id for task in self.tasks)

    @property
    def material_summary(self) -> str:
        return " · ".join(self.material)

    def preparation_markdown(self) -> str:
        """Erzeuge den Anzeigeabschnitt, ohne die Vorbereitungsdatei zu verändern."""
        parts = []
        if self.material:
            # Metadaten sind Klartext, kein eingebettetes Markdown.
            escaped = [
                re.sub(r"([\\`*_{}\[\]()#+.!<>|~-])", r"\\\1", item)
                for item in self.material
            ]
            parts.append(
                "## Benötigtes Material\n\n"
                + "\n".join(f"- {item}" for item in escaped)
            )
        if self.preparation:
            parts.append(self.preparation)
        return "\n\n".join(parts)


def material_path(directory: Path, *parts: str) -> Path:
    path = directory.joinpath(*parts)
    if not path.resolve().is_relative_to(directory.resolve()):
        raise ValueError(f"Materialpfad liegt außerhalb der Sequenz: {path}")
    return path


def optional_markdown(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def load_lesson(directory: Path, lesson_id: str, tasks: dict[str, Task]) -> Lesson:
    path = material_path(directory, "stunden", lesson_id, "stunde.toml")
    try:
        data = load_toml(path)
        reject_unknown(data, {"titel", "ziele", "material", "aufgaben", "phasen"})
        resolved = []
        for task_id in reference_ids(data, "aufgaben"):
            if task_id not in tasks:
                task_path = material_path(directory, "aufgaben", task_id, "aufgabe.md")
                try:
                    tasks[task_id] = Task(
                        task_id,
                        task_path.read_text(encoding="utf-8"),
                        optional_markdown(
                            material_path(directory, "aufgaben", task_id, "loesung.md")
                        ),
                    )
                except (OSError, ValueError) as error:
                    raise ValueError(f"Aufgabe '{task_path}': {error}") from error
            resolved.append(tasks[task_id])
        phases = data.get("phasen", [])
        if not isinstance(phases, list) or any(not isinstance(p, dict) for p in phases):
            raise ValueError("'phasen' muss eine Liste von Tabellen sein.")
        for phase in phases:
            reject_unknown(phase, {"titel", "text"})
        return Lesson(
            lesson_id,
            require_text(data, "titel"),
            resolved,
            optional_markdown(
                material_path(directory, "stunden", lesson_id, "vorbereitung.md")
            ),
            text_list(data, "ziele"),
            text_list(data, "material"),
            [Phase(require_text(p, "titel"), require_text(p, "text")) for p in phases],
        )
    except (OSError, ValueError, TypeError, KeyError) as error:
        raise ValueError(f"Stunde '{path}': {error}") from error


def save_markdown(path: Path, source: str | None) -> None:
    if source is None:
        path.unlink(missing_ok=True)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")


def save_lesson(directory: Path, lesson: Lesson) -> None:
    lesson.__post_init__()
    path = material_path(directory, "stunden", lesson.id, "stunde.toml")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(lesson_metadata_source(lesson), encoding="utf-8")
    save_markdown(
        material_path(directory, "stunden", lesson.id, "vorbereitung.md"),
        lesson.preparation,
    )
    for task in lesson.tasks:
        task.__post_init__()
        save_markdown(
            material_path(directory, "aufgaben", task.id, "aufgabe.md"), task.text
        )
        save_markdown(
            material_path(directory, "aufgaben", task.id, "loesung.md"), task.solution
        )
