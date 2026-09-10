"""Wähle eine zugeordnete Aufgabe und anschließend die zu bearbeitende Datei."""

from typing import ClassVar

from rich.text import Text
from textual import on
from textual.widgets import OptionList
from textual.widgets.option_list import Option

from pult.curriculum.material import Task
from pult.screens.base_screen import PultModalScreen
from pult.widgets.form_dialog import FormDialog


class SelectTaskFileScreen(PultModalScreen[tuple[str, str] | None]):
    BINDINGS: ClassVar = [("escape", "back", "Zurück")]
    DEFAULT_CSS = """
    SelectTaskFileScreen OptionList { height: auto; max-height: 16; }
    """

    def __init__(self, tasks: list[Task]):
        super().__init__()
        self.tasks = tasks
        self.task_id: str | None = None

    def compose(self):
        with FormDialog("Aufgabe bearbeiten", id="task-file-dialog"):
            yield OptionList(
                *(Option(Text(f"{i} · {task.id}"), id=task.id)
                  for i, task in enumerate(self.tasks, 1)),
                id="task-file-picker",
            )

    @on(OptionList.OptionSelected, "#task-file-picker")
    def select_file(self, event: OptionList.OptionSelected):
        event.stop()
        if self.task_id is not None:
            self.dismiss((self.task_id, str(event.option.id)))
            return
        self.task_id = str(event.option.id)
        picker = self.query_one(OptionList)
        picker.clear_options()
        picker.add_options([
            Option("Aufgabentext", id="aufgabe.md"),
            Option("Lösung", id="loesung.md"),
        ])
        picker.border_title = self.task_id
        picker.highlighted = 0

    def action_back(self):
        if self.task_id is None:
            self.dismiss(None)
            return
        selected = self.task_id
        self.task_id = None
        picker = self.query_one(OptionList)
        picker.clear_options()
        picker.add_options(
            Option(Text(f"{i} · {task.id}"), id=task.id)
            for i, task in enumerate(self.tasks, 1)
        )
        picker.border_title = ""
        picker.highlighted = picker.get_option_index(selected)
