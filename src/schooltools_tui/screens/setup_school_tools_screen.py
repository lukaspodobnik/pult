from pathlib import Path

from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, Header, Input, Label, Select

from schooltools_tui.config import AppConfig
from schooltools_tui.initialization import (
    SetupError,
    initialize_schooltools,
)
from schooltools_tui.school.school_year import (
    get_likely_school_year,
    get_school_year_options,
)
from schooltools_tui.widgets.footer import SchooltoolsFooter


class SetupScreen(Screen[AppConfig]):
    def compose(self) -> ComposeResult:
        school_year_options = get_school_year_options()
        selected_school_year = get_likely_school_year(school_year_options)

        yield Header()

        with Vertical(id="setup-form"):
            yield Label("Willkommen bei Schooltools", id="setup-title")
            yield Label(
                "Wo sollen deine Daten gespeichert werden?",
                classes="field-label",
            )

            yield Input(
                value=str(Path.home() / "Schooltools"),
                placeholder="Pfad zum Root-Verzeichnis",
                id="root",
            )

            yield Label(
                "Welchen Editor möchtest du verwenden?",
                classes="field-label",
            )

            yield Input(
                value="nvim",
                placeholder="Editor",
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

        yield SchooltoolsFooter()

    @on(Button.Pressed, "#submit-setup")
    def submit_setup(self) -> None:
        root_input = self.query_one("#root", Input)
        editor_input = self.query_one("#editor", Input)
        school_year_select = self.query_one("#school-year", Select)

        try:
            app_config = initialize_schooltools(
                root=root_input.value,
                editor=editor_input.value,
                year=str(school_year_select.value),
            )
        except SetupError as error:
            self.notify(
                str(error),
                severity="error",
            )
            return

        self.dismiss(app_config)
