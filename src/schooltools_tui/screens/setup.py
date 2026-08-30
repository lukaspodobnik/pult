from pathlib import Path

from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label

from schooltools_tui.config import AppConfig, save_app_config


class SetupScreen(Screen[AppConfig]):

    def compose(self) -> ComposeResult:
        yield Header()

        with Vertical(id="setup-form"):
            yield Label("Willkommen bei Schooltools")
            yield Label("Wo sollen deine Daten gespeichert werden?")

            yield Input(
                value=str(Path.home() / "Schooltools"),
                placeholder="Pfad zum Dateiverzeichnis",
                id="data-directory",
            )

            yield Label("Welchen Editor möchtest du verwenden?")

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

        data_directory_value = data_directory_input.value.strip()
        editor_value = editor_input.value.strip()

        if not data_directory_value:
            self.notify(
                "Bitte gib ein Datenverzeichnis an.",
                severity="error",
            )
            return

        if not editor_input:
            self.notify(
                "Bitte gib einen Editor an.",
                severity="error",
            )
            return

        data_directory = Path(data_directory_value).expanduser()

        if data_directory.exists() and not data_directory.is_dir():
            self.notify(
                "Der angegebene Pfad ist kein Verzeichnis.",
                severity="error",
            )
            return

        app_config = AppConfig(
            data_directory=data_directory,
            editor=editor_value,
        )

        save_app_config(app_config)

        self.dismiss(app_config)
