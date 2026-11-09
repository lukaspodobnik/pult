"""Beschriftung einer Sammlung; Rendering und Antwortflächen bleiben gemeinsam."""

from dataclasses import dataclass
from html import escape

from pult.curriculum.material import Task, TaskSource
from pult.curriculum.sequence import Sequence


@dataclass(frozen=True)
class WorkbookProfile:
    kind: str
    books: tuple[tuple[str, str], ...] = ()

    @classmethod
    def for_tasks(cls, tasks: list[Task], sequence: Sequence) -> "WorkbookProfile":
        books: dict[str, str] = {}
        book_tasks = 0
        for task in tasks:
            source = task.metadata.source
            if source is None or source.kind == "eigen":
                continue
            source.__post_init__()
            if source.book_id not in sequence.books:
                raise ValueError(
                    f"{task.metadata.title}: Unbekanntes Buch '{source.book_id}'."
                )
            assert source.book_id is not None
            books[source.book_id] = sequence.books[source.book_id]
            book_tasks += 1
        kind = (
            "eigen"
            if not book_tasks
            else "buch"
            if book_tasks == len(tasks)
            else "gemischt"
        )
        return cls(kind, tuple(books.items()))

    @staticmethod
    def location(source: TaskSource) -> str:
        task = f"Aufgabe {source.number}" if source.number is not None else source.label
        return f"S. {source.page} · {task}"

    def heading(self, task: Task, number: int) -> str:
        source = task.metadata.source
        if self.kind == "buch" and source is not None:
            return self.location(source)
        return f"{number}. Aufgabe"

    def caption(self, task: Task) -> str:
        source = task.metadata.source
        if source is None or source.kind != "buch":
            return ""
        parts = []
        if self.kind == "gemischt" or len(self.books) > 1:
            assert source.book_id is not None
            parts.append(dict(self.books)[source.book_id])
        if self.kind == "gemischt":
            parts.append(self.location(source))
        if source.rubric:
            parts.append(source.rubric)
        return " · ".join(parts)

    def source_html(self, *, solutions: bool) -> str:
        if not self.books:
            return ""
        # This attributes the exercises, not our independently written solutions.
        label = "Lösungen zu Aufgaben aus" if solutions else "Aufgaben aus"
        return (
            '<p class="workbook-sources">'
            + escape(label + ": " + "; ".join(title for _, title in self.books))
            + "</p>"
        )

    def author(self, configured_author: str) -> str:
        return configured_author if self.kind == "eigen" else ""
