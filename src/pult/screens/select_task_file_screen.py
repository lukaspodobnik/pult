"""Wähle eine zugeordnete Aufgabe und anschließend die zu bearbeitende Datei."""

from typing import ClassVar

from rich.text import Text
from textual import on
from textual.widgets.option_list import Option

from pult.curriculum.material import Task
from pult.screens.base_screen import PultModalScreen
from pult.widgets.form_dialog import FormDialog
from pult.widgets.scrolling import OptionList


class SelectTaskFileScreen(PultModalScreen[tuple[str, str] | None]):
    BINDINGS: ClassVar = [("escape", "back", "Zurück")]
    DEFAULT_CSS = """
    SelectTaskFileScreen OptionList { height: auto; max-height: 16; }
    """

    def __init__(self, tasks: list[Task], *, choose_file: bool = False):
        super().__init__()
        self.tasks = tasks
        self.choose_file = choose_file
        self.task_id: str | None = tasks[0].id if choose_file else None

    def on_mount(self):
        if self.choose_file:
            self.show_files()

    def show_files(self):
        picker = self.query_one(OptionList)
        picker.clear_options()
        picker.add_options(
            [
                Option("Aufgabentext", id="aufgabe.md"),
                Option("Lösung", id="loesung.md"),
                Option("Titel und Einordnung", id="aufgabe.toml"),
            ]
        )
        task = next(task for task in self.tasks if task.id == self.task_id)
        picker.border_title = Text(task.metadata.title)
        picker.highlighted = 0

    def compose(self):
        with FormDialog("Aufgabe bearbeiten", id="task-file-dialog"):
            yield OptionList(
                *(
                    Option(Text(f"{i} · {task.metadata.title}"), id=task.id)
                    for i, task in enumerate(self.tasks, 1)
                ),
                id="task-file-picker",
            )

    @on(OptionList.OptionSelected, "#task-file-picker")
    def select_file(self, event: OptionList.OptionSelected):
        event.stop()
        if self.task_id is not None:
            self.dismiss((self.task_id, str(event.option.id)))
            return
        self.task_id = str(event.option.id)
        self.show_files()

    def action_back(self):
        if self.task_id is None or self.choose_file:
            self.dismiss(None)
            return
        selected = self.task_id
        self.task_id = None
        picker = self.query_one(OptionList)
        picker.clear_options()
        picker.add_options(
            Option(Text(f"{i} · {task.metadata.title}"), id=task.id)
            for i, task in enumerate(self.tasks, 1)
        )
        picker.border_title = ""
        picker.highlighted = picker.get_option_index(selected)
