from pathlib import Path

from textual import on
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Select

from pult.config import AppConfig
from pult.initialization import (
    SetupError,
    initialize_pult,
)
from pult.school.school_year import (
    get_likely_school_year,
    get_school_year_options,
)
from pult.services.settings import get_editor_options
from pult.widgets.footer import PultFooter
from pult.widgets.scrolling import Vertical


class SetupScreen(Screen[AppConfig]):
    def compose(self) -> ComposeResult:
        school_year_options = get_school_year_options()
        selected_school_year = get_likely_school_year(school_year_options)

        form = Vertical(id="setup-form")
        form.border_title = "PULT EINRICHTEN"
        with form:
            yield Label("Willkommen bei PULT", id="setup-title")
            yield Label(
                "Wo sollen deine Daten gespeichert werden?",
                classes="field-label",
            )

            yield Input(
                value=str(Path.home() / "Pult"),
                placeholder="Pfad zum Root-Verzeichnis",
                id="root",
            )

            yield Label(
                "Welchen Editor möchtest du verwenden?",
                classes="field-label",
            )

            yield Select(
                get_editor_options(),
                value="nvim",
                allow_blank=False,
                id="editor",
            )

            yield Label(
                "Mit welchem Schuljahr möchtest du beginnen?",
                classes="field-label",
            )

            yield Select(
                school_year_options,
                value=selected_school_year,
                allow_blank=False,
                id="school-year",
            )

            yield Button(
                "Einrichten",
                id="submit-setup",
                variant="primary",
            )

        yield PultFooter()

    @on(Button.Pressed, "#submit-setup")
    def submit_setup(self) -> None:
        root_input = self.query_one("#root", Input)
        editor_input = self.query_one("#editor", Select)
        school_year_select = self.query_one("#school-year", Select)

        try:
            app_config = initialize_pult(
                root=root_input.value,
                editor=str(editor_input.value),
                year=str(school_year_select.value),
            )
        except SetupError as error:
            self.notify(
                str(error),
                severity="error",
            )
            return

        self.dismiss(app_config)
