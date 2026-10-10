"""Lehrpläne nach Fach und Jahrgang, ohne Gliederungs- oder Sprungbaum."""

from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import ClassVar

from textual import on
from textual.widgets import Static

from pult.school.subject import load_subjects
from pult.screens.base_screen import PultScreen
from pult.widgets.document_viewer import DocumentPane, DocumentViewer
from pult.widgets.footer import PultFooter
from pult.widgets.scrolling import Horizontal, Tree, Vertical


@dataclass(frozen=True)
class CurriculumEntry:
    title: str
    source: str
    path: Path
    directory: Path


class CurriculumTree(Tree[CurriculumEntry | None]):
    def __init__(self, *, id: str | None = None):
        super().__init__("Lehrplan", id=id)
        self.show_root = False
        self.guide_depth = 2
        self.border_title = "LEHRPLAN"


def curriculum_documents(root: Path, subject_id: str) -> dict[str, str]:
    """Nur Jahrgangsdokumente; persönliche Dateien haben Vorrang."""
    documents: dict[str, str] = {}
    bundled = files("pult.defaults").joinpath("curriculum", subject_id)
    if bundled.is_dir():
        for path in bundled.iterdir():
            if (
                path.is_file()
                and path.name.startswith("jahrgang-")
                and path.name.endswith(".md")
            ):
                documents[path.name] = path.read_text(encoding="utf-8")
    personal = root / "curriculum" / subject_id
    for path in personal.glob("jahrgang-*.md"):
        documents[path.name] = path.read_text(encoding="utf-8")
    return documents


class CurriculumScreen(PultScreen[None]):
    BINDINGS: ClassVar = [("escape", "close", "Zurück")]

    def __init__(self):
        super().__init__()
        self.current_entry: CurriculumEntry | None = None

    def compose(self):
        with Horizontal(id="curriculum-workspace"):
            with Vertical(id="curriculum-navigation"):
                yield CurriculumTree(id="curriculum-tree")
            with Vertical(id="curriculum-content"):
                with DocumentPane(id="curriculum-reader"):
                    yield Static("Fach und Jahrgang links auswählen.")
        yield PultFooter()

    def on_mount(self):
        tree = self.query_one(CurriculumTree)
        for subject in sorted(
            load_subjects(self.app_config.root), key=lambda s: s.name.casefold()
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
                self.add_subject(
                    tree.root.add(subject.name, expand=True), documents, subject.id
                )
        tree.root.expand()
        if tree.root.children:
            tree.move_cursor(tree.root.children[0])
        tree.focus()

    def add_subject(self, subject_node, documents: dict[str, str], subject_id: str):
        for grade in range(5, 14):
            name = f"jahrgang-{grade:02}.md"
            if name not in documents:
                continue
            personal = self.app_config.root / "curriculum" / subject_id / name
            bundled = Path(
                str(files("pult.defaults").joinpath("curriculum", subject_id, name))
            )
            path = personal if personal.exists() else bundled
            title = f"{grade}. Jahrgangsstufe"
            subject_node.add_leaf(
                title, CurriculumEntry(title, documents[name], path, path.parent)
            )

    @on(Tree.NodeHighlighted, "#curriculum-tree")
    async def entry_highlighted(self, event: Tree.NodeHighlighted):
        entry = event.node.data
        if not isinstance(entry, CurriculumEntry) or entry == self.current_entry:
            return
        self.current_entry = entry
        reader = self.query_one("#curriculum-reader", DocumentPane)
        await reader.remove_children()
        await reader.mount(DocumentViewer(entry.source, entry.path, entry.directory))
        reader.border_title = entry.title
        reader.scroll_home(animate=False)

    def action_close(self):
        self.dismiss()
