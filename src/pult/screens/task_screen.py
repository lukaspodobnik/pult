"""Alle Aufgaben einer Sequenz, einschließlich noch nicht zugeordneter Aufgaben."""

import shlex
import shutil
import subprocess
from typing import ClassVar

from rich.text import Text
from textual import on
from textual.widgets import Static
from textual.widgets.option_list import Option

from pult.curriculum.material import (
    Task,
    TaskMetadata,
    load_task,
    material_path,
    save_lesson_metadata,
)
from pult.curriculum.sequence import Sequence, load_sequence
from pult.screens.base_screen import PultScreen
from pult.screens.create_task_screen import CreateTaskScreen
from pult.screens.select_task_file_screen import SelectTaskFileScreen
from pult.services.task_creation import create_task_files
from pult.widgets.document_viewer import DocumentPane, DocumentViewer
from pult.widgets.footer import PultFooter
from pult.widgets.scrolling import Horizontal, OptionList, Vertical


class TaskScreen(PultScreen[Sequence]):
    BINDINGS: ClassVar = [
        ("escape", "close", "Zurück"),
        ("e", "edit_task", "Bearbeiten"),
        ("n", "create_task", "Neue Aufgabe"),
        ("s", "toggle_solution", "Aufgabe / Lösung"),
        ("v", "assign_task", "Vormerken / entfernen"),
    ]
    DEFAULT_CSS = """
    TaskScreen { padding: 1 0 0 0; }
    TaskScreen #task-workspace { height: 1fr; padding: 0 1; margin-bottom: 1; }
    TaskScreen #task-list { height: 1fr; border: round $primary; }
    TaskScreen #task-list:focus {
        border: round $primary;
        border-title-color: $text;
        border-title-style: none;
        background-tint: transparent;
        outline: none;
    }
    TaskScreen #task-content { width: 1fr; }
    """

    def __init__(self, sequence: Sequence, directory, *, lesson_id: str | None = None):
        super().__init__()
        self.sequence = sequence
        self.directory = directory
        self.lesson_id = lesson_id
        self.show_solution = False
        self.tasks = self.read_tasks()
        lesson = next((item for item in sequence.lessons if item.id == lesson_id), None)
        self.task_id = (
            lesson.tasks[0].id
            if lesson and lesson.tasks
            else (self.tasks[0].id if self.tasks else None)
        )

    def read_tasks(self) -> list[Task]:
        folder = material_path(self.directory, "aufgaben")
        if not folder.exists():
            return []
        tasks = []
        for entry in sorted(folder.iterdir(), key=lambda item: item.name):
            if not entry.is_dir() or entry.name.startswith("."):
                continue
            tasks.append(load_task(self.directory, entry.name))
        return tasks

    @property
    def selected_task(self):
        return next((task for task in self.tasks if task.id == self.task_id), None)

    def options(self):
        assigned = {
            task.id for lesson in self.sequence.lessons for task in lesson.tasks
        }
        lesson = next(
            (item for item in self.sequence.lessons if item.id == self.lesson_id), None
        )
        bookmarked = {task.id for task in lesson.tasks} if lesson else set()
        for task in self.tasks:
            label = Text(no_wrap=True, overflow="ellipsis")
            if task.id in bookmarked:
                label.append("✓ ", style="bold")
            label.append(task.metadata.title)
            if self.lesson_id is None and task.id not in assigned:
                label.append("\nNoch nicht zugeordnet", style="dim")
            yield Option(label, id=task.id)

    def material(self):
        task = self.selected_task
        if task is None:
            yield Static(
                "Noch keine Aufgaben in dieser Sequenz vorhanden.", markup=False
            )
            return
        filename = "loesung.md" if self.show_solution else "aufgabe.md"
        source = task.solution if self.show_solution else task.text
        if source is None:
            yield Static("Noch keine Lösung vorhanden.", markup=False)
        else:
            yield DocumentViewer(
                source,
                material_path(self.directory, "aufgaben", task.id, filename),
                self.directory,
            )

    def material_subtitle(self) -> Text:
        label = "Lösung" if self.show_solution else "Aufgabe"
        task = self.selected_task
        if task is not None:
            metadata = task.metadata
            label += f" · AFB {metadata.requirement_level} · {', '.join(metadata.competencies)}"
        return Text(label)

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action == "assign_task":
            return self.lesson_id is not None
        return True

    async def action_toggle_solution(self):
        self.show_solution = not self.show_solution
        await self.refresh_material()

    async def action_assign_task(self):
        task = self.selected_task
        lesson = next(
            (item for item in self.sequence.lessons if item.id == self.lesson_id), None
        )
        if task is None or lesson is None:
            return
        previous = lesson.tasks[:]
        lesson.tasks = (
            [item for item in lesson.tasks if item.id != task.id]
            if any(item.id == task.id for item in lesson.tasks)
            else [*lesson.tasks, task]
        )
        try:
            save_lesson_metadata(self.directory, lesson)
        except (OSError, ValueError) as error:
            lesson.tasks = previous
            self.notify(str(error), severity="error")
            return
        self.pult_app.require_sequence_library().invalidate()
        picker = self.query_one("#task-list", OptionList)
        with self.prevent(OptionList.OptionHighlighted):
            picker.clear_options()
            picker.add_options(self.options())
            picker.highlighted = picker.get_option_index(task.id)

    def compose(self):
        with Horizontal(id="task-workspace"):
            with Vertical(id="task-navigation", classes="teaching-navigation"):
                yield OptionList(*self.options(), id="task-list")
            with DocumentPane(id="task-content"):
                yield from self.material()
        yield PultFooter()

    def on_mount(self):
        self.query_one("#task-list").border_title = "AUFGABEN"
        lesson = next(
            (item for item in self.sequence.lessons if item.id == self.lesson_id), None
        )
        if lesson:
            self.query_one("#task-list").border_subtitle = f"Für: {lesson.title}"
        self.query_one("#task-content").border_subtitle = self.material_subtitle()
        self.query_one("#task-content").border_title = self.sequence.title
        picker = self.query_one(OptionList)
        with self.prevent(OptionList.OptionHighlighted):
            if self.task_id is not None:
                picker.highlighted = picker.get_option_index(self.task_id)
        picker.focus()

    @on(OptionList.OptionHighlighted, "#task-list")
    async def highlight_task(self, event: OptionList.OptionHighlighted):
        event.stop()
        if (
            event.option_index != self.query_one("#task-list", OptionList).highlighted
            or event.option.id == self.task_id
        ):
            return
        self.task_id = event.option.id
        self.show_solution = False
        await self.refresh_material()

    async def refresh_material(self):
        pane = self.query_one("#task-content", DocumentPane)
        await pane.remove_children()
        await pane.mount(*self.material())
        pane.border_title = self.sequence.title
        pane.border_subtitle = self.material_subtitle()
        pane.scroll_home(animate=False)

    def action_close(self):
        self.dismiss(self.sequence)

    def action_edit_task(self):
        if self.selected_task is not None:
            self.app.push_screen(
                SelectTaskFileScreen([self.selected_task], choose_file=True),
                self.edit_file,
            )

    def action_create_task(self):
        self.app.push_screen(CreateTaskScreen(), self.create_task)

    async def create_task(self, metadata: TaskMetadata | None):
        if metadata is None:
            return
        try:
            command = shlex.split(self.app_config.editor)
            if not command or shutil.which(command[0]) is None:
                raise ValueError("Der konfigurierte Editor wurde nicht gefunden.")
            task_id, paths = create_task_files(self.directory, metadata)
        except (OSError, ValueError) as error:
            self.notify(str(error), severity="error")
            return
        try:
            with self.app.suspend():
                result = subprocess.run(
                    [*command, *(str(path) for path in paths)], check=False
                )
            if result.returncode:
                self.notify(
                    f"Der Editor wurde mit Status {result.returncode} beendet.",
                    severity="warning",
                )
        except OSError as error:
            self.notify(
                f"Die Aufgabe wurde angelegt, aber der Editor konnte nicht geöffnet werden: {error}",
                severity="error",
            )
        await self.reload_tasks(select_task_id=task_id)

    async def edit_file(self, selection: tuple[str, str] | None):
        if selection is None:
            return
        task_id, filename = selection
        try:
            command = shlex.split(self.app_config.editor)
            if not command or shutil.which(command[0]) is None:
                raise ValueError("Der konfigurierte Editor wurde nicht gefunden.")
            path = material_path(self.directory, "aufgaben", task_id, filename)
            if filename == "loesung.md" and not path.exists():
                path.touch(exist_ok=False)
            with self.app.suspend():
                result = subprocess.run([*command, str(path)], check=False)
            if result.returncode:
                self.notify(
                    f"Der Editor wurde mit Status {result.returncode} beendet.",
                    severity="warning",
                )
        except (OSError, ValueError) as error:
            self.notify(str(error), severity="error")
            return
        await self.reload_tasks()

    async def reload_tasks(self, *, select_task_id: str | None = None):
        try:
            sequence = load_sequence(
                self.app_config.root,
                self.sequence.grade_level,
                self.sequence.subject_id,
                self.sequence.id,
            )
            tasks = self.read_tasks()
        except (OSError, ValueError) as error:
            self.notify(
                f"{error}\nDie letzte gültige Ansicht bleibt geöffnet.",
                severity="error",
            )
            return
        self.pult_app.require_sequence_library().invalidate()
        self.sequence, self.tasks = sequence, tasks
        if select_task_id is not None:
            self.task_id = select_task_id
        if not any(task.id == self.task_id for task in tasks):
            self.task_id = tasks[0].id if tasks else None
        picker = self.query_one(OptionList)
        with self.prevent(OptionList.OptionHighlighted):
            picker.clear_options()
            picker.add_options(self.options())
            if self.task_id is not None:
                picker.highlighted = picker.get_option_index(self.task_id)
        await self.refresh_material()
