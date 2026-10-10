"""Stunden und Aufgaben gemäß dem Materialvertrag; unabhängig von Klassen."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import tomli_w
from markdown_it import MarkdownIt

from pult.storage import load_toml, save_toml


def lesson_metadata_source(lesson: "Lesson") -> str:
    """Nur Titel und geordnete Aufgabenverweise gehören in die Metadaten."""
    return tomli_w.dumps(
        {"titel": lesson.title, "aufgaben": [t.id for t in lesson.tasks]}
    )


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
        if not isinstance(self.text, str):
            raise ValueError("Der Phaseninhalt muss Markdown-Text sein.")
        self.text = self.text.strip()


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

    goals_source: str | None = field(default=None, compare=False, repr=False)
    material_source: str | None = field(default=None, compare=False, repr=False)
    phases_source: str | None = field(default=None, compare=False, repr=False)

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
        return self.preparation or ""

    def goals_markdown(self) -> str:
        source = self.goals_source
        if source is not None and unordered_items(source, "ziele.md") == self.goals:
            return source
        return "\n".join(f"- {item}" for item in self.goals)

    def material_markdown(self) -> str:
        source = self.material_source
        if (
            source is not None
            and unordered_items(source, "material.md") == self.material
        ):
            return source
        return "\n".join(f"- {item}" for item in self.material)

    def phases_markdown(self) -> str:
        source = self.phases_source
        if source is not None and parse_phases(source) == self.phases:
            return source
        return "\n\n".join(f"# {p.title}\n\n{p.text}".rstrip() for p in self.phases)


@dataclass(frozen=True)
class MaterialEntry:
    label: str
    target: str | None = None


def unordered_items(source: str, filename: str) -> list[str]:
    """Eine flache ungeordnete Liste, mit normalem Inline-Markdown."""
    tokens = MarkdownIt("commonmark").parse(source)
    if not tokens:
        return []
    if tokens[0].type != "bullet_list_open" or tokens[-1].type != "bullet_list_close":
        raise ValueError(f"{filename}: Nur eine ungeordnete Liste ist erlaubt.")
    allowed = {
        "bullet_list_open",
        "bullet_list_close",
        "list_item_open",
        "list_item_close",
        "paragraph_open",
        "paragraph_close",
        "inline",
    }
    if any(
        t.type not in allowed
        or (t.type == "bullet_list_open" and t.level != 0)
        or (t.type == "paragraph_open" and t.level != 2)
        for t in tokens
    ):
        raise ValueError(f"{filename}: Nur flache Listeneinträge sind erlaubt.")
    if sum(t.type == "inline" for t in tokens) != sum(
        t.type == "list_item_open" for t in tokens
    ):
        raise ValueError(f"{filename}: Jeder Eintrag benötigt genau einen Absatz.")
    items = []
    for token in tokens:
        if token.type == "list_item_open":
            if token.map is None:
                raise ValueError(f"{filename}: Ungültiger Listeneintrag.")
            lines = source.splitlines()[token.map[0] : token.map[1]]
            item = re.sub(r"^ {0,3}[-+*] +", "", lines[0])
            item = "\n".join([item, *(line.strip() for line in lines[1:])]).strip()
            if not item or "\n\n" in item:
                raise ValueError(
                    f"{filename}: Ein Eintrag benötigt genau einen Absatz."
                )
            items.append(item)
    return items


def parse_phases(source: str) -> list[Phase]:
    tokens = MarkdownIt("commonmark").parse(source)
    if not tokens:
        return []
    headings = [token for token in tokens if token.type == "heading_open"]
    if tokens[0].type != "heading_open" or any(
        token.tag != "h1" or token.markup != "#" or token.level != 0
        for token in headings
    ):
        raise ValueError(
            "verlauf.md: Mit '# Phase' beginnen; nur #-Überschriften sind erlaubt."
        )
    lines = source.splitlines()
    phases = []
    for index, token in enumerate(headings):
        assert token.map is not None
        start, end = token.map
        following = headings[index + 1].map if index + 1 < len(headings) else None
        title_token = tokens[tokens.index(token) + 1]
        phases.append(
            Phase(
                title_token.content,
                "\n".join(lines[end : following[0] if following else len(lines)]),
            )
        )
    return phases


def material_entries(source: str) -> list[MaterialEntry]:
    entries = []
    for item in unordered_items(source, "material.md"):
        tokens = MarkdownIt("commonmark").parseInline(item)[0].children or []
        links = [t.attrGet("href") for t in tokens if t.type == "link_open"]
        if len(links) > 1:
            raise ValueError("material.md: Höchstens ein Link pro Eintrag ist erlaubt.")
        target = str(links[0]) if links else None
        if target:
            parsed = urlsplit(target)
            if (
                (parsed.scheme and parsed.scheme not in {"http", "https"})
                or parsed.netloc
                and not parsed.scheme
                or target.startswith("#")
            ):
                raise ValueError(
                    "material.md: Nur relative Dateilinks oder http(s)-Links sind erlaubt."
                )
        label = "".join(
            t.content for t in tokens if t.type in {"text", "code_inline", "softbreak"}
        )
        entries.append(MaterialEntry(label or item, target))
    return entries


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
        reject_unknown(data, {"titel", "aufgaben"})
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
        folder = material_path(directory, "stunden", lesson_id)
        sources = {
            name: optional_markdown(material_path(folder, name)) or ""
            for name in ("ziele.md", "material.md", "verlauf.md")
        }
        material_entries(sources["material.md"])
        return Lesson(
            lesson_id,
            require_text(data, "titel"),
            resolved,
            optional_markdown(material_path(folder, "vorbereitung.md")),
            unordered_items(sources["ziele.md"], "ziele.md"),
            unordered_items(sources["material.md"], "material.md"),
            parse_phases(sources["verlauf.md"]),
            sources["ziele.md"],
            sources["material.md"],
            sources["verlauf.md"],
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
    save_lesson_metadata(directory, lesson)
    for name, source in (
        ("ziele.md", lesson.goals_markdown()),
        ("material.md", lesson.material_markdown()),
        ("verlauf.md", lesson.phases_markdown()),
    ):
        save_markdown(material_path(path.parent, name), source)
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


DEFAULT_TITLE = "Noch nicht vorbereitet"


def lesson_file_sources() -> dict[str, str]:
    return {
        "stunde.toml": tomli_w.dumps({"titel": DEFAULT_TITLE, "aufgaben": []}),
        "vorbereitung.md": f"# {DEFAULT_TITLE}\n",
        "ziele.md": "- Die Schüler können\n- Die Schüler können\n",
        "verlauf.md": "# Einstieg\n",
        "material.md": "",
    }


def default_lesson(lesson_id: str) -> Lesson:
    sources = lesson_file_sources()
    return Lesson(
        lesson_id,
        DEFAULT_TITLE,
        preparation=sources["vorbereitung.md"],
        goals=unordered_items(sources["ziele.md"], "ziele.md"),
        phases=parse_phases(sources["verlauf.md"]),
    )


def initialize_lesson_files(directory: Path, lesson_id: str) -> None:
    """Gemeinsame Muster; vorhandene persönliche Dateien bleiben unangetastet."""
    lesson_id = validate_id(lesson_id, "Die Stunden-ID")
    folder = material_path(directory, "stunden", lesson_id)
    folder.mkdir(parents=True, exist_ok=True)
    for name, source in lesson_file_sources().items():
        try:
            with material_path(folder, name).open("x", encoding="utf-8") as file:
                file.write(source)
        except FileExistsError:
            pass


def save_lesson_metadata(directory: Path, lesson: Lesson) -> None:
    """Aufgabenzuordnung ändern, ohne Dokumente oder Aufgaben neu zu schreiben."""
    lesson.__post_init__()
    save_toml(
        material_path(directory, "stunden", lesson.id, "stunde.toml"),
        {"titel": lesson.title, "aufgaben": [t.id for t in lesson.tasks]},
    )
