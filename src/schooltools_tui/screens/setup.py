from pathlib import Path

from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label

from schooltools_tui.config import AppConfig
from schooltools_tui.initialization import (
    SetupError,
    initialize_schooltools,
)


class SetupScreen(Screen[AppConfig]):
    def compose(self) -> ComposeResult:
        yield Header()

        with Vertical(id="setup-form"):
            yield Label("Willkommen bei Schooltools", id="setup-title")
            yield Label(
                "Wo sollen deine Daten gespeichert werden?",
                classes="field-label",
            )

            yield Input(
                value=str(Path.home() / "Schooltools"),
                placeholder="Pfad zum Dateiverzeichnis",
                id="data-directory",
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

            yield Button(
                "Einrichten",
                id="submit-setup",
                variant="primary",
            )

        yield Footer()

    @on(Button.Pressed, "#submit-setup")
    def submit_setup(self) -> None:
        data_directory_input = self.query_one("#data-directory", Input)
        editor_input = self.query_one("#editor", Input)

        try:
            app_config = initialize_schooltools(
                root=data_directory_input.value,
                editor=editor_input.value,
            )
        except SetupError as error:
            self.notify(
                str(error),
                severity="error",
            )
            return

        self.dismiss(app_config)
