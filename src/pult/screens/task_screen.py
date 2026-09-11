"""Alle Aufgaben einer Sequenz, einschließlich noch nicht zugeordneter Aufgaben."""

import shlex
import shutil
import subprocess
from typing import ClassVar

from rich.text import Text
from textual import on
from textual.widgets import Static
from textual.widgets.option_list import Option

from pult.curriculum.material import Task, material_path, validate_id
from pult.curriculum.sequence import Sequence, load_sequence
from pult.screens.base_screen import PultScreen
from pult.screens.create_task_screen import CreateTaskScreen
from pult.screens.lesson_screen import LessonPane
from pult.screens.select_task_file_screen import SelectTaskFileScreen
from pult.services.task_creation import create_task_files
from pult.widgets.footer import PultFooter
from pult.widgets.lesson_material import LessonMaterial
from pult.widgets.scrolling import Horizontal, OptionList, Vertical
from pult.widgets.sequence_context import SequenceContext


class TaskScreen(PultScreen[Sequence]):
    BINDINGS: ClassVar = [
        ("escape", "close", "Zurück"),
        ("e", "edit_task", "Bearbeiten"),
        ("n", "create_task", "Neue Aufgabe"),
    ]
    DEFAULT_CSS = """
    TaskScreen { padding: 1 0 0 0; }
    TaskScreen #task-workspace { height: 1fr; padding: 0 1; margin-bottom: 1; }
    TaskScreen #task-navigation { width: 28; margin-right: 1; }
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

    def __init__(self, sequence: Sequence, directory):
        super().__init__()
        self.sequence = sequence
        self.directory = directory
        self.tasks = self.read_tasks()
        self.task_id = self.tasks[0].id if self.tasks else None

    def read_tasks(self) -> list[Task]:
        folder = material_path(self.directory, "aufgaben")
        if not folder.exists():
            return []
        tasks = []
        for entry in sorted(folder.iterdir(), key=lambda item: item.name):
            if not entry.is_dir() or entry.name.startswith("."):
                continue
            if validate_id(entry.name, "Aufgaben-ID") != entry.name:
                raise ValueError(f"Ungültige Aufgaben-ID: {entry.name}")
            text = material_path(self.directory, "aufgaben", entry.name, "aufgabe.md")
            solution = material_path(
                self.directory, "aufgaben", entry.name, "loesung.md"
            )
            tasks.append(
                Task(
                    entry.name,
                    text.read_text(encoding="utf-8"),
                    solution.read_text(encoding="utf-8") if solution.exists() else None,
                )
            )
        return tasks

    @property
    def selected_task(self):
        return next((task for task in self.tasks if task.id == self.task_id), None)

    @staticmethod
    def task_title(task: Task) -> str:
        for line in task.text.splitlines():
            if line.startswith("# ") and line[2:].strip():
                return line[2:].strip()
        return task.id

    def options(self):
        assigned = {
            task.id for lesson in self.sequence.lessons for task in lesson.tasks
        }
        for task in self.tasks:
            label = Text(self.task_title(task))
            if task.id not in assigned:
                label.append("\nNoch nicht zugeordnet", style="dim")
            yield Option(label, id=task.id)

    def material(self):
        task = self.selected_task
        if task is None:
            yield Static(
                "Noch keine Aufgaben in dieser Sequenz vorhanden.", markup=False
            )
            return
        yield LessonMaterial(
            task.text,
            material_path(self.directory, "aufgaben", task.id, "aufgabe.md"),
            self.directory,
        )
        if task.solution is not None:
            yield Static("Lösung", classes="lesson-solution-title")
            yield LessonMaterial(
                task.solution,
                material_path(self.directory, "aufgaben", task.id, "loesung.md"),
                self.directory,
            )

    def compose(self):
        with Horizontal(id="task-workspace"):
            with Vertical(id="task-navigation"):
                yield SequenceContext(
                    self.sequence, self.app_config.root, id="task-sequence"
                )
                yield OptionList(*self.options(), id="task-list")
            with LessonPane(id="task-content"):
                yield from self.material()
        yield PultFooter()

    def on_mount(self):
        self.query_one("#task-content", LessonPane).can_focus = False
        self.query_one("#task-sequence").border_title = "SEQUENZ"
        self.query_one("#task-list").border_title = "AUFGABEN"
        self.query_one("#task-content").border_title = (
            self.task_title(self.selected_task) if self.selected_task else "AUFGABEN"
        )
        self.query_one(OptionList).focus()

    @on(OptionList.OptionHighlighted, "#task-list")
    async def highlight_task(self, event: OptionList.OptionHighlighted):
        event.stop()
        if event.option.id == self.task_id:
            return
        self.task_id = event.option.id
        await self.refresh_material()

    async def refresh_material(self):
        pane = self.query_one("#task-content", LessonPane)
        await pane.remove_children()
        await pane.mount(*self.material())
        pane.border_title = (
            self.task_title(self.selected_task) if self.selected_task else "AUFGABEN"
        )
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

    async def create_task(self, title: str | None):
        if title is None:
            return
        try:
            command = shlex.split(self.app_config.editor)
            if not command or shutil.which(command[0]) is None:
                raise ValueError("Der konfigurierte Editor wurde nicht gefunden.")
            task_id, paths = create_task_files(self.directory, title)
        except (OSError, ValueError) as error:
            self.notify(str(error), severity="error")
            return
        self.task_id = task_id
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
        await self.reload_tasks()

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

    async def reload_tasks(self):
        try:
            self.pult_app.require_sequence_library().invalidate()
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
        self.sequence, self.tasks = sequence, tasks
        self.query_one(SequenceContext).update_sequence(sequence)
        if not any(task.id == self.task_id for task in tasks):
            self.task_id = tasks[0].id if tasks else None
        picker = self.query_one(OptionList)
        with self.prevent(OptionList.OptionHighlighted):
            picker.clear_options()
            picker.add_options(self.options())
            if self.task_id is not None:
                picker.highlighted = picker.get_option_index(self.task_id)
        await self.refresh_material()
