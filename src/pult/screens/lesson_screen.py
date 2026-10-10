"""Unterrichtsansicht mit freier Vorbereitung, Planung und separatem Material."""

import shlex
import shutil
import subprocess
from pathlib import Path
from typing import ClassVar

from rich.text import Text
from textual import on
from textual.binding import Binding
from textual.widgets import Static
from textual.widgets.option_list import Option

from pult.curriculum.material import Lesson, initialize_lesson_files, material_path
from pult.curriculum.sequence import Sequence, get_sequence_path, load_sequence
from pult.screens.base_screen import PultScreen
from pult.screens.select_lesson_file_screen import SelectLessonFileScreen
from pult.widgets.document_viewer import DocumentPane, DocumentViewer
from pult.widgets.footer import PultFooter
from pult.widgets.materials import MaterialsPane
from pult.widgets.scrolling import Horizontal, OptionList, Vertical


class LessonScreen(PultScreen[Sequence]):
    BINDINGS: ClassVar = [
        ("escape", "close", "Zurück"),
        Binding("space", "toggle_material", "Vorbereitung / Planung", priority=True),
        ("a", "open_tasks", "Aufgaben öffnen"),
        ("e", "edit_preparation", "Bearbeiten"),
        ("r", "edit_material", "Material bearbeiten"),
        ("m", "edit_metadata", "Stundentitel"),
    ]

    def __init__(self, sequence: Sequence, lesson_id: str):
        super().__init__()
        if not any(lesson.id == lesson_id for lesson in sequence.lessons):
            raise ValueError("Die ausgewählte Stunde ist nicht mehr vorhanden.")
        self.sequence, self.lesson_id = sequence, lesson_id
        self.show_planning = False

    @property
    def lesson(self) -> Lesson | None:
        return next(
            (item for item in self.sequence.lessons if item.id == self.lesson_id), None
        )

    @property
    def directory(self) -> Path:
        return get_sequence_path(
            self.app_config.root,
            self.sequence.grade_level,
            self.sequence.subject_id,
            self.sequence.id,
        ).parent

    def options(self):
        for item in self.sequence.lessons:
            yield Option(
                Text(" ".join(item.title.split()), no_wrap=True, overflow="crop"),
                id=item.id,
            )

    def document(self, planning: bool = False):
        lesson = self.lesson
        if lesson is None:
            return Static("Noch keine Stunden vorhanden.", classes="lesson-empty")
        return DocumentViewer(
            lesson.preparation_markdown(),
            material_path(
                self.directory,
                "stunden",
                lesson.id,
                "verlauf.md" if planning else "vorbereitung.md",
            ),
            self.directory,
            planning=lesson if planning else None,
        )

    def materials(self):
        return MaterialsPane(
            self.lesson.material_markdown() if self.lesson else "",
            material_path(self.directory, "stunden", self.lesson_id, "material.md"),
            self.directory,
            id="lesson-materials",
        )

    def compose(self):
        with Horizontal(id="lesson-workspace"):
            with Vertical(id="lesson-navigation", classes="teaching-navigation"):
                with Vertical(id="lesson-list-frame"):
                    yield OptionList(*self.options(), id="lesson-list")
                with Vertical(id="lesson-material-frame"):
                    yield self.materials()
            with Vertical(id="lesson-primary"):
                with DocumentPane(id="lesson-preparation"):
                    yield self.document()
                with DocumentPane(id="lesson-planning"):
                    yield self.document(planning=True)
        yield PultFooter()

    def on_mount(self):
        self.query_one("#lesson-list-frame").border_title = "STUNDEN"
        self.update_view()
        self.query_one("#lesson-list").focus()

    def update_view(self):
        self.query_one("#lesson-preparation").display = not self.show_planning
        self.query_one("#lesson-planning").display = self.show_planning
        for selector, label in (
            ("lesson-preparation", "Vorbereitung"),
            ("lesson-planning", "Planung"),
        ):
            pane = self.query_one("#" + selector)
            pane.border_title = self.sequence.title
            pane.border_subtitle = label
        listing = self.query_one("#lesson-list", OptionList)
        if self.lesson:
            with self.prevent(OptionList.OptionHighlighted):
                listing.highlighted = listing.get_option_index(self.lesson.id)

    @on(OptionList.OptionHighlighted, "#lesson-list")
    async def select_lesson(self, event: OptionList.OptionHighlighted):
        event.stop()
        if (
            event.option_index != self.query_one("#lesson-list", OptionList).highlighted
            or event.option.id == self.lesson_id
        ):
            return
        self.lesson_id = str(event.option.id)
        self.show_planning = False
        await self.refresh_contents()

    async def refresh_contents(self):
        for selector, planning in (
            ("lesson-preparation", False),
            ("lesson-planning", True),
        ):
            pane = self.query_one("#" + selector, DocumentPane)
            await pane.remove_children()
            await pane.mount(self.document(planning))
            pane.scroll_home(animate=False)
        frame = self.query_one("#lesson-material-frame", Vertical)
        await frame.remove_children()
        await frame.mount(self.materials())
        self.update_view()

    def action_close(self):
        self.dismiss(self.sequence)

    def action_toggle_material(self):
        self.show_planning = not self.show_planning
        self.update_view()

    def action_open_tasks(self):
        from pult.screens.task_screen import TaskScreen

        try:
            self.app.push_screen(
                TaskScreen(self.sequence, self.directory, lesson_id=self.lesson_id),
                self.tasks_closed,
            )
        except (OSError, ValueError) as error:
            self.notify(str(error), severity="error")

    def tasks_closed(self, sequence: Sequence | None):
        if sequence is not None:
            self.sequence = sequence
        # The existing document widgets, mode and scroll position remain mounted.

    async def action_edit_preparation(self):
        if self.show_planning:
            self.app.push_screen(SelectLessonFileScreen(), self.file_selected)
        else:
            await self.edit("vorbereitung.md")

    async def file_selected(self, filename: str | None):
        if filename is not None:
            await self.edit(filename)

    async def action_edit_material(self):
        await self.edit("material.md")

    async def action_edit_metadata(self):
        await self.edit("stunde.toml")

    async def edit(self, filename: str):
        if self.lesson is None:
            return
        try:
            command = shlex.split(self.app_config.editor)
            if not command or shutil.which(command[0]) is None:
                raise ValueError("Der konfigurierte Editor wurde nicht gefunden.")
            initialize_lesson_files(self.directory, self.lesson_id)
            path = material_path(self.directory, "stunden", self.lesson_id, filename)
            with self.app.suspend():
                result = subprocess.run([*command, str(path)], check=False)
            if result.returncode:
                self.notify(
                    f"Der Editor wurde mit Status {result.returncode} beendet.",
                    severity="warning",
                )
        except (OSError, ValueError) as error:
            self.notify(
                f"Der Editor konnte nicht geöffnet werden: {error}", severity="error"
            )
            return
        self.pult_app.require_sequence_library().invalidate()
        try:
            updated = load_sequence(
                self.app_config.root,
                self.sequence.grade_level,
                self.sequence.subject_id,
                self.sequence.id,
            )
        except (OSError, ValueError) as error:
            self.notify(
                f"{error}\nDie letzte gültige Ansicht bleibt geöffnet.",
                severity="error",
                timeout=12,
            )
            return
        self.sequence = updated
        if self.lesson is None:
            self.lesson_id = updated.lessons[0].id if updated.lessons else ""
        listing = self.query_one("#lesson-list", OptionList)
        with self.prevent(OptionList.OptionHighlighted):
            listing.clear_options()
            listing.add_options(self.options())
        await self.refresh_contents()
