"""Eine Planungsdatei zum Bearbeiten auswählen."""

from typing import ClassVar

from textual import on
from textual.widgets.option_list import Option

from pult.screens.base_screen import PultModalScreen
from pult.widgets.form_dialog import FormDialog
from pult.widgets.scrolling import OptionList


class SelectLessonFileScreen(PultModalScreen[str | None]):
    BINDINGS: ClassVar = [("escape", "cancel", "Zurück")]

    def compose(self):
        with FormDialog("Planung bearbeiten", id="lesson-file-dialog"):
            yield OptionList(
                Option("Ziele", id="ziele.md"),
                Option("Verlauf", id="verlauf.md"),
                id="lesson-file-picker",
            )

    @on(OptionList.OptionSelected, "#lesson-file-picker")
    def select_file(self, event: OptionList.OptionSelected):
        self.dismiss(str(event.option.id))

    def action_cancel(self):
        self.dismiss(None)
