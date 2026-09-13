"""Fachbezogenes Nachschlagewerk für Lehrpläne und Unterrichtsgrundlagen."""

from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import ClassVar

from markdown_it import MarkdownIt
from textual import on
from textual.app import ComposeResult
from textual.widgets import MarkdownViewer

from pult.school.subject import load_subjects
from pult.screens.base_screen import PultScreen
from pult.widgets.footer import PultFooter
from pult.widgets.scrolling import EdgeScrollbars, Horizontal, Tree, Vertical


@dataclass(frozen=True)
class CurriculumEntry:
    title: str
    source: str
    heading: int | None = None


class CurriculumTree(Tree[CurriculumEntry | None]):
    def __init__(self, *, id: str | None = None):
        super().__init__("Lehrplan", id=id)
        self.show_root = False
        self.guide_depth = 2
        self.border_title = "LEHRPLAN"


class CurriculumReader(
    EdgeScrollbars, MarkdownViewer, can_focus=False, can_focus_children=False
):
    """Lesebereich mit Scrollleisten am Rahmen und ohne eigenen Fokus."""


def curriculum_documents(root: Path, subject_id: str) -> dict[str, str]:
    """Persönliche Dateien haben Vorrang; Defaults bleiben unverändert."""
    documents: dict[str, str] = {}
    bundled = files("pult.defaults").joinpath("curriculum", subject_id)
    if bundled.is_dir():
        for path in sorted(bundled.iterdir(), key=lambda item: item.name):
            if path.is_file() and path.name.endswith(".md"):
                documents[path.name] = path.read_text(encoding="utf-8")
    personal = root / "curriculum" / subject_id
    if personal.is_dir():
        for path in sorted(personal.glob("*.md")):
            documents[path.name] = path.read_text(encoding="utf-8")
    return documents


class CurriculumScreen(PultScreen[None]):
    BINDINGS: ClassVar = [
        ("escape", "close", "Zurück"),
    ]

    def __init__(self):
        super().__init__()
        self.current_source: str | None = None

    def compose(self) -> ComposeResult:
        with Horizontal(id="curriculum-workspace"):
            with Vertical(id="curriculum-navigation"):
                yield CurriculumTree(id="curriculum-tree")
            with Vertical(id="curriculum-content"):
                yield CurriculumReader(
                    "Fach und Inhalt links auswählen.",
                    show_table_of_contents=False,
                    open_links=False,
                    id="curriculum-reader",
                )
        yield PultFooter()

    async def on_mount(self) -> None:
        self.query_one(MarkdownViewer).document.can_focus = False
        tree = self.query_one(CurriculumTree)
        for subject in sorted(
            load_subjects(self.app_config.root),
            key=lambda subject: subject.name.casefold(),
        ):
            try:
                documents = curriculum_documents(self.app_config.root, subject.id)
            except (OSError, UnicodeError) as error:
                self.notify(
                    f"Lehrplan für {subject.name} konnte nicht geladen werden: {error}",
                    severity="error",
                )
                continue
            if documents:
                self.add_subject(tree.root.add(subject.name), documents)
        tree.root.expand()
        if tree.root.children:
            tree.move_cursor(tree.root.children[0])
        else:
            await self.query_one(MarkdownViewer).document.update(
                "Es sind keine Lehrplandokumente vorhanden."
            )
        tree.focus()

    def add_subject(self, subject_node, documents: dict[str, str]) -> None:
        curriculum = subject_node.add("Lehrpläne", expand=True)
        names = {
            "leitideen.md": "Leitideen",
            "kompetenzen.md": "Kompetenzen",
            "anforderungsbereiche.md": "Anforderungsbereiche",
            "operatoren.md": "Operatoren",
        }
        ordered = sorted(name for name in documents if name.startswith("jahrgang-"))
        ordered += [name for name in names if name in documents]
        ordered += sorted(set(documents) - set(ordered))
        for name in ordered:
            source = documents[name]
            is_grade = name.startswith("jahrgang-")
            title = names.get(name, name.removesuffix(".md"))
            if is_grade and name[9:-3].isdigit():
                title = f"{int(name[9:-3])}. Jahrgangsstufe"
            parent = curriculum if is_grade else subject_node
            node = parent.add(title, CurriculumEntry(title, source))
            stack = [(0, node)]
            heading_index = 0
            tokens = MarkdownIt().parse(source)
            for index, token in enumerate(tokens):
                if token.type != "heading_open":
                    continue
                level = int(token.tag[1:])
                heading_title = tokens[index + 1].content
                current_index = heading_index
                heading_index += 1
                if level == 1:
                    continue
                while len(stack) > 1 and stack[-1][0] >= level:
                    stack.pop()
                child = stack[-1][1].add(
                    heading_title,
                    CurriculumEntry(heading_title, source, current_index),
                )
                stack.append((level, child))

            def finish(branch):
                for child in branch.children:
                    finish(child)
                if not branch.children:
                    branch.allow_expand = False

            finish(node)
        if not curriculum.children:
            curriculum.remove()

    @on(Tree.NodeHighlighted, "#curriculum-tree")
    async def entry_highlighted(self, event: Tree.NodeHighlighted) -> None:
        entry = event.node.data
        if not isinstance(entry, CurriculumEntry):
            return
        reader = self.query_one(MarkdownViewer)
        if self.current_source != entry.source:
            self.current_source = entry.source
            await reader.document.update(entry.source)
        reader.border_title = entry.title
        if entry.heading is None:
            reader.scroll_home(animate=False)
        else:
            headings = list(
                reader.document.query(
                    "MarkdownH1, MarkdownH2, MarkdownH3, MarkdownH4, MarkdownH5, MarkdownH6"
                )
            )
            if entry.heading < len(headings):
                self.call_after_refresh(
                    headings[entry.heading].scroll_visible, top=True, animate=False
                )

    def action_close(self) -> None:
        self.dismiss()
