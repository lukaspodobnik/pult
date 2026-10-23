"""Stunden und Aufgaben gemäß dem Materialvertrag; unabhängig von Klassen."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import tomli_w
from markdown_it import MarkdownIt

from pult.storage import load_toml, save_text, save_toml


def lesson_metadata(lesson: "Lesson") -> dict[str, Any]:
    data: dict[str, Any] = {
        "titel": lesson.title,
        "aufgaben": [t.id for t in lesson.tasks],
    }
    if lesson.notes:
        data["hinweise"] = lesson.notes
    return data


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


@dataclass(frozen=True)
class TaskPartExport:
    """Optionale Druckangaben für eine mit a), b), … bezeichnete Teilaufgabe."""

    rows: int | None = None
    image_width_mm: int | None = None

    def __post_init__(self) -> None:
        if self.rows is not None and (
            type(self.rows) is not int or not 0 <= self.rows <= 40
        ):
            raise ValueError(
                "export.teilaufgaben.*.zeilen muss zwischen 0 und 40 liegen."
            )
        if self.image_width_mm is not None and (
            type(self.image_width_mm) is not int or not 10 <= self.image_width_mm <= 65
        ):
            raise ValueError("bildbreite_mm muss eine ganze Zahl von 10 bis 65 sein.")

    @classmethod
    def from_dict(cls, data: Any) -> "TaskPartExport":
        if not isinstance(data, dict):
            raise ValueError("Jede Export-Teilaufgabe muss eine TOML-Tabelle sein.")
        reject_unknown(data, {"zeilen", "bildbreite_mm"})
        return cls(data.get("zeilen"), data.get("bildbreite_mm"))

    def to_dict(self) -> dict[str, int]:
        return {
            key: value
            for key, value in (
                ("zeilen", self.rows),
                ("bildbreite_mm", self.image_width_mm),
            )
            if value is not None
        }


@dataclass(frozen=True)
class TaskExport:
    """Antwortflächen im Arbeitsheft; fehlende Angaben ergeben ein gemeinsames Raster."""

    answer_area: str = "kariert"
    rows: int = 8
    per_subtask: bool = False
    columns: int | None = None
    append_equals: bool = False
    image_width_mm: int | None = None
    parts: dict[str, TaskPartExport] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.answer_area not in ("linien", "kariert", "keiner"):
            raise ValueError(
                "export.antwortbereich muss 'linien', 'kariert' oder 'keiner' sein."
            )
        if type(self.rows) is not int or not 0 <= self.rows <= 40:
            raise ValueError("export.zeilen muss eine ganze Zahl von 0 bis 40 sein.")
        if self.answer_area != "keiner" and self.rows == 0:
            raise ValueError("Ein Antwortbereich benötigt mindestens eine Zeile.")
        if self.answer_area == "keiner" and self.rows != 0:
            raise ValueError("Ohne Antwortbereich muss export.zeilen 0 sein.")
        if type(self.per_subtask) is not bool:
            raise ValueError("export.pro_teilaufgabe muss true oder false sein.")
        if self.columns is not None and (
            type(self.columns) is not int or not 1 <= self.columns <= 3
        ):
            raise ValueError("export.spalten muss 1, 2 oder 3 sein.")
        if self.answer_area == "linien" and self.columns == 3:
            raise ValueError("Schreiblinien erlauben höchstens zwei Exportspalten.")
        if (
            self.answer_area == "kariert"
            and self.per_subtask
            and self.columns not in (None, 1)
        ):
            raise ValueError("Karofelder je Teilaufgabe benötigen eine Exportspalte.")
        if type(self.append_equals) is not bool:
            raise ValueError("export.gleichheitszeichen muss true oder false sein.")
        if self.append_equals and (
            self.answer_area != "linien" or not self.per_subtask
        ):
            raise ValueError(
                "Zusätzliche Gleichheitszeichen benötigen Schreiblinien je Teilaufgabe."
            )
        TaskPartExport(image_width_mm=self.image_width_mm)
        if not isinstance(self.parts, dict):
            raise ValueError("export.teilaufgaben muss eine TOML-Tabelle sein.")
        for label, part in self.parts.items():
            if not isinstance(label, str) or not re.fullmatch(r"[a-z]", label):
                raise ValueError("Export-Teilaufgaben werden mit a, b, … bezeichnet.")
            if not isinstance(part, TaskPartExport):
                raise ValueError("Ungültige Exportangaben für eine Teilaufgabe.")
            part.__post_init__()
            if part.rows is not None:
                if not self.per_subtask:
                    raise ValueError(
                        "Zeilen je Teilaufgabe benötigen pro_teilaufgabe = true."
                    )
                if (part.rows == 0) != (self.answer_area == "keiner"):
                    raise ValueError(
                        "Ein Antwortbereich benötigt mindestens eine Zeile; ohne Bereich gilt 0."
                    )

    @classmethod
    def from_dict(cls, data: Any) -> "TaskExport":
        if not isinstance(data, dict):
            raise ValueError("'export' muss eine TOML-Tabelle sein.")
        reject_unknown(
            data,
            {
                "antwortbereich",
                "zeilen",
                "pro_teilaufgabe",
                "spalten",
                "gleichheitszeichen",
                "bildbreite_mm",
                "teilaufgaben",
            },
        )
        area = data.get("antwortbereich", "kariert")
        default_rows = 0 if area == "keiner" else 1 if area == "linien" else 8
        parts = data.get("teilaufgaben", {})
        if not isinstance(parts, dict):
            raise ValueError("export.teilaufgaben muss eine TOML-Tabelle sein.")
        return cls(
            area,
            data.get("zeilen", default_rows),
            data.get("pro_teilaufgabe", False),
            data.get("spalten"),
            data.get("gleichheitszeichen", False),
            data.get("bildbreite_mm"),
            {label: TaskPartExport.from_dict(part) for label, part in parts.items()},
        )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "antwortbereich": self.answer_area,
            "zeilen": self.rows,
            "pro_teilaufgabe": self.per_subtask,
        }
        if self.columns is not None:
            data["spalten"] = self.columns
        if self.append_equals:
            data["gleichheitszeichen"] = True
        if self.image_width_mm is not None:
            data["bildbreite_mm"] = self.image_width_mm
        if self.parts:
            data["teilaufgaben"] = {
                key: value.to_dict() for key, value in self.parts.items()
            }
        return data


@dataclass
class TaskMetadata:
    title: str
    competencies: list[str]
    requirement_level: str
    export: TaskExport | None = None

    def __post_init__(self) -> None:
        self.title = " ".join(require_text({"titel": self.title}, "titel").split())
        self.competencies = [
            value.strip()
            for value in text_list({"kompetenzen": self.competencies}, "kompetenzen")
        ]
        if not 1 <= len(self.competencies) <= 3:
            raise ValueError(
                "'kompetenzen' muss eine bis drei Hauptkompetenzen enthalten."
            )
        if len(set(self.competencies)) != len(self.competencies):
            raise ValueError("'kompetenzen' darf keine doppelten Einträge enthalten.")
        if self.export is not None:
            if not isinstance(self.export, TaskExport):
                raise ValueError("Ungültige Exportangaben für die Aufgabe.")
            self.export.__post_init__()
        if self.requirement_level not in ("I", "II", "III"):
            raise ValueError("'anforderungsbereich' muss 'I', 'II' oder 'III' sein.")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskMetadata":
        reject_unknown(data, {"titel", "kompetenzen", "anforderungsbereich", "export"})
        return cls(
            data["titel"],
            data["kompetenzen"],
            data["anforderungsbereich"],
            TaskExport.from_dict(data["export"]) if "export" in data else None,
        )

    def to_dict(self) -> dict[str, Any]:
        self.__post_init__()
        data: dict[str, Any] = {
            "titel": self.title,
            "kompetenzen": self.competencies,
            "anforderungsbereich": self.requirement_level,
        }
        if self.export is not None:
            data["export"] = self.export.to_dict()
        return data


@dataclass
class Task:
    id: str
    text: str
    solution: str | None = None
    metadata: TaskMetadata = field(kw_only=True)

    def __post_init__(self) -> None:
        self.id = validate_id(self.id, "Die Aufgaben-ID")
        if not isinstance(self.metadata, TaskMetadata):
            raise ValueError(
                "Die Aufgabe benötigt Titel, Kompetenzen und Anforderungsbereich."
            )
        self.metadata.__post_init__()
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

    notes: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.notes, str):
            raise ValueError("Die Hinweise müssen ein Text sein.")
        self.notes = " ".join(self.notes.split())
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
    source_lines = source.splitlines()
    for token in tokens:
        if token.type == "list_item_open":
            if token.map is None:
                raise ValueError(f"{filename}: Ungültiger Listeneintrag.")
            lines = source_lines[token.map[0] : token.map[1]]
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


def load_task(directory: Path, task_id: str) -> Task:
    if validate_id(task_id, "Die Aufgaben-ID") != task_id:
        raise ValueError(f"Ungültige Aufgaben-ID: {task_id}")
    path = material_path(directory, "aufgaben", task_id, "aufgabe.toml")
    try:
        metadata = TaskMetadata.from_dict(load_toml(path))
        path = material_path(directory, "aufgaben", task_id, "aufgabe.md")
        text = path.read_text(encoding="utf-8")
        path = material_path(directory, "aufgaben", task_id, "loesung.md")
        return Task(task_id, text, optional_markdown(path), metadata=metadata)
    except (OSError, ValueError, TypeError, KeyError) as error:
        raise ValueError(f"Aufgabe '{path}': {error}") from error


def load_lesson(directory: Path, lesson_id: str, tasks: dict[str, Task]) -> Lesson:
    path = material_path(directory, "stunden", lesson_id, "stunde.toml")
    try:
        data = load_toml(path)
        reject_unknown(data, {"titel", "aufgaben", "hinweise"})
        resolved = []
        for task_id in reference_ids(data, "aufgaben"):
            if task_id not in tasks:
                tasks[task_id] = load_task(directory, task_id)
            resolved.append(tasks[task_id])
        folder = material_path(directory, "stunden", lesson_id)
        sources = {
            name: optional_markdown(material_path(folder, name)) or ""
            for name in ("ziele.md", "material.md", "verlauf.md")
        }
        material_entries(sources["material.md"])
        return Lesson(
            id=lesson_id,
            title=require_text(data, "titel"),
            tasks=resolved,
            preparation=optional_markdown(material_path(folder, "vorbereitung.md")),
            goals=unordered_items(sources["ziele.md"], "ziele.md"),
            material=unordered_items(sources["material.md"], "material.md"),
            phases=parse_phases(sources["verlauf.md"]),
            goals_source=sources["ziele.md"],
            material_source=sources["material.md"],
            phases_source=sources["verlauf.md"],
            notes=data.get("hinweise", ""),
        )
    except (OSError, ValueError, TypeError, KeyError) as error:
        raise ValueError(f"Stunde '{path}': {error}") from error


def save_markdown(path: Path, source: str | None) -> None:
    if source is None:
        path.unlink(missing_ok=True)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        save_text(path, source)


def save_task(directory: Path, task: Task) -> None:
    task.__post_init__()
    metadata = material_path(directory, "aufgaben", task.id, "aufgabe.toml")
    text = material_path(directory, "aufgaben", task.id, "aufgabe.md")
    solution = material_path(directory, "aufgaben", task.id, "loesung.md")
    metadata.parent.mkdir(parents=True, exist_ok=True)
    save_toml(metadata, task.metadata.to_dict())
    save_markdown(text, task.text)
    save_markdown(solution, task.solution)


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
        save_task(directory, task)


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
        lesson_metadata(lesson),
    )


def task_sort_key(task: Task) -> tuple[int, int, str, str]:
    """Titelnummern numerisch sortieren; unnummerierte Titel folgen alphabetisch."""
    title = task.metadata.title.casefold()
    number = re.match(r"^(\d+)\.\s+", title)
    if number:
        return 0, int(number[1]), title[number.end() :], task.id
    return 1, 0, title, task.id


def load_tasks(directory: Path) -> list[Task]:
    folder = material_path(directory, "aufgaben")
    if not folder.exists():
        return []
    return sorted(
        (
            load_task(directory, entry.name)
            for entry in folder.iterdir()
            if entry.is_dir() and not entry.name.startswith(".")
        ),
        key=task_sort_key,
    )
