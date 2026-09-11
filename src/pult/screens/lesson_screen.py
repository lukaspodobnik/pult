"""Unterrichtsansicht einer Sequenz, geöffnet auf einer bestimmten Stunde."""

import shlex
import shutil
import subprocess
from pathlib import Path
from typing import ClassVar

from rich.text import Text
from textual import on
from textual.widgets import Static
from textual.widgets.option_list import Option

from pult.curriculum.material import Lesson, material_path
from pult.curriculum.sequence import Sequence, get_sequence_path, load_sequence
from pult.school.subject import load_subjects
from pult.screens.base_screen import PultScreen
from pult.screens.select_task_file_screen import SelectTaskFileScreen
from pult.widgets.footer import PultFooter
from pult.widgets.lesson_material import LessonMaterial
from pult.widgets.scrolling import Horizontal, OptionList, Vertical, VerticalScroll


class LessonPane(VerticalScroll):
    can_focus = True
    can_focus_children = False


class LessonScreen(PultScreen[Sequence]):
    BINDINGS: ClassVar = [
        ("escape", "close", "Zurück"),
        ("space", "toggle_material", "Vorbereitung / Aufgaben"),
        ("e", "edit_preparation", "Bearbeiten"),
        ("m", "edit_metadata", "Stundendaten"),
    ]

    def __init__(self, sequence: Sequence, lesson_id: str):
        super().__init__()
        if not any(lesson.id == lesson_id for lesson in sequence.lessons):
            raise ValueError("Die ausgewählte Stunde ist nicht mehr vorhanden.")
        self.sequence = sequence
        self.lesson_id = lesson_id
        self.show_tasks = False

    @property
    def lesson(self) -> Lesson | None:
        return next(
            (lesson for lesson in self.sequence.lessons if lesson.id == self.lesson_id),
            None,
        )

    @property
    def directory(self) -> Path:
        return get_sequence_path(
            self.app_config.root,
            self.sequence.grade_level,
            self.sequence.subject_id,
            self.sequence.id,
        ).parent

    def source(self, text: str, *parts: str) -> LessonMaterial:
        return LessonMaterial(
            text, material_path(self.directory, *parts), self.directory
        )

    def preparation(self):
        lesson = self.lesson
        if lesson is None:
            yield Static("Noch keine Stunden vorhanden.", classes="lesson-empty")
        else:
            text = lesson.preparation_markdown()
            if text:
                yield self.source(text, "stunden", lesson.id, "vorbereitung.md")
            else:
                yield Static(
                    "Noch keine Vorbereitung vorhanden. Mit e im Editor anlegen.",
                    classes="lesson-empty",
                )

    def tasks(self):
        lesson = self.lesson
        if lesson is None or not lesson.tasks:
            yield Static("Noch keine Aufgaben zugeordnet.", classes="lesson-empty")
            return
        for number, task in enumerate(lesson.tasks, 1):
            yield Static(
                f"{number} · {task.id}", classes="lesson-task-title", markup=False
            )
            yield self.source(task.text, "aufgaben", task.id, "aufgabe.md")
            if task.solution is not None:
                yield Static("Lösung", classes="lesson-solution-title")
                yield self.source(task.solution, "aufgaben", task.id, "loesung.md")

    def goals(self) -> str:
        return (
            "\n\n".join(f"• {goal}" for goal in self.lesson.goals)
            if self.lesson and self.lesson.goals
            else "Noch keine Ziele eingetragen."
        )

    def phases(self) -> Text:
        text = Text()
        for index, phase in enumerate(self.lesson.phases if self.lesson else []):
            if index:
                text.append("\n\n")
            text.append(phase.title, style="bold")
            text.append("\n\n" + phase.text)
        return text or Text("Noch kein Verlauf eingetragen.")

    def context(self) -> str:
        subjects = {
            subject.id: subject.name for subject in load_subjects(self.app_config.root)
        }
        return f"{subjects.get(self.sequence.subject_id, self.sequence.subject_id)}\n{self.sequence.grade_level}. Jahrgang\n\n{self.sequence.title}"

    def compose(self):
        with Horizontal(id="lesson-workspace"):
            with Vertical(id="lesson-navigation"):
                with Vertical(id="lesson-sequence"):
                    yield Static(self.context(), id="lesson-context", markup=False)
                with Vertical(id="lesson-list-frame"):
                    yield OptionList(
                        *(
                            Option(f"{i:02}  {lesson.title}", id=lesson.id)
                            for i, lesson in enumerate(self.sequence.lessons, 1)
                        ),
                        id="lesson-list",
                    )
            with Vertical(id="lesson-primary"):
                with LessonPane(id="lesson-preparation"):
                    yield from self.preparation()
                with LessonPane(id="lesson-tasks"):
                    yield from self.tasks()
            with Vertical(id="lesson-orientation"):
                with LessonPane(id="lesson-goals"):
                    yield Static(self.goals(), id="lesson-goals-text", markup=False)
                with LessonPane(id="lesson-schedule"):
                    yield Static(self.phases(), id="lesson-phases-text")
        yield PultFooter()

    def on_mount(self):
        for pane in self.query(LessonPane):
            pane.can_focus = False
        for selector, title in [
            ("lesson-sequence", "SEQUENZ"),
            ("lesson-list-frame", "STUNDEN"),
            ("lesson-goals", "ZIELE"),
            ("lesson-schedule", "VERLAUF"),
        ]:
            self.query_one("#" + selector).border_title = title
        self.update_view()

    def update_view(self):
        self.query_one("#lesson-preparation").display = not self.show_tasks
        self.query_one("#lesson-tasks").display = self.show_tasks
        for selector, label in [
            ("lesson-preparation", "Vorbereitung"),
            ("lesson-tasks", "Aufgaben"),
        ]:
            pane = self.query_one("#" + selector)
            pane.border_title = (
                self.lesson.title if self.lesson else self.sequence.title
            )
            pane.border_subtitle = label
        listing = self.query_one("#lesson-list", OptionList)
        if self.lesson:
            listing.highlighted = listing.get_option_index(self.lesson.id)
        listing.focus()

    @on(OptionList.OptionSelected, "#lesson-list")
    async def select_lesson(self, event: OptionList.OptionSelected):
        event.stop()
        if event.option.id == self.lesson_id:
            self.update_view()
            return
        self.lesson_id = str(event.option.id)
        self.show_tasks = False
        await self.refresh_contents()

    async def refresh_contents(self):
        for selector, widgets in [
            ("lesson-preparation", list(self.preparation())),
            ("lesson-tasks", list(self.tasks())),
        ]:
            pane = self.query_one("#" + selector, LessonPane)
            await pane.remove_children()
            await pane.mount(*widgets)
            pane.scroll_home(animate=False)
        self.query_one("#lesson-goals-text", Static).update(self.goals())
        self.query_one("#lesson-phases-text", Static).update(self.phases())
        for selector in ["lesson-goals", "lesson-schedule"]:
            self.query_one("#" + selector, LessonPane).scroll_home(animate=False)
        self.update_view()

    def action_close(self):
        self.dismiss(self.sequence)

    def action_toggle_material(self):
        self.show_tasks = not self.show_tasks
        self.update_view()

    async def action_edit_preparation(self):
        if self.show_tasks:
            if self.lesson is None or not self.lesson.tasks:
                self.notify("Dieser Stunde sind noch keine Aufgaben zugeordnet.")
                return
            self.app.push_screen(SelectTaskFileScreen(self.lesson.tasks), self.task_file_selected)
            return
        await self.edit("vorbereitung.md")

    async def task_file_selected(self, selection: tuple[str, str] | None):
        if selection is not None:
            task_id, filename = selection
            await self.edit(filename, task_id=task_id)

    async def action_edit_metadata(self):
        await self.edit("stunde.toml")

    async def edit(self, filename: str, *, task_id: str | None = None):
        lesson = self.lesson
        if lesson is None:
            return
        if task_id is not None and not any(task.id == task_id for task in lesson.tasks):
            return
        try:
            command = shlex.split(self.app_config.editor)
            if not command or shutil.which(command[0]) is None:
                self.notify(
                    "Der konfigurierte Editor wurde nicht gefunden.", severity="error"
                )
                return
            path = material_path(
                self.directory,
                "aufgaben" if task_id is not None else "stunden",
                task_id if task_id is not None else lesson.id,
                filename,
            )
            if filename in {"vorbereitung.md", "loesung.md"} and not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch(exist_ok=False)
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
        listing.clear_options()
        listing.add_options(
            Option(f"{i:02}  {item.title}", id=item.id)
            for i, item in enumerate(updated.lessons, 1)
        )
        self.query_one("#lesson-context", Static).update(self.context())
        await self.refresh_contents()
