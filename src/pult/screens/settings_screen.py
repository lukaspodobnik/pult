from typing import ClassVar

from textual import on
from textual.app import ComposeResult
from textual.widgets import Button, Label, Select, Static

from pult.config import AppConfig
from pult.school.period import load_periods
from pult.school.school_year import get_school_year_options
from pult.screens.about_screen import AboutScreen
from pult.screens.base_screen import PultModalScreen
from pult.screens.edit_periods_screen import EditPeriodsScreen
from pult.services.settings import get_editor_options, update_settings
from pult.widgets.form_dialog import FormDialog, FormFields
from pult.widgets.scrolling import Horizontal


class SettingsScreen(PultModalScreen[AppConfig | None]):
    BINDINGS: ClassVar = [("escape", "cancel", "Abbrechen")]
    DEFAULT_CSS = """
    SettingsScreen #edit-periods, SettingsScreen #show-about {
        width: 100%;
        margin-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        config = self.app_config
        with FormDialog("EINSTELLUNGEN", id="settings-dialog"):
            with FormFields(classes="form-fields"):
                yield Label("Editor", classes="field-label")
                yield Select(
                    get_editor_options(config.editor),
                    value=config.editor,
                    allow_blank=False,
                    id="settings-editor",
                )
                yield Label("Schuljahr", classes="field-label")
                yield Select(
                    get_school_year_options(config.root),
                    value=config.active_school_year,
                    allow_blank=False,
                    id="settings-year",
                )
                yield Static(
                    "Vorhandene Jahresdaten bleiben erhalten. Neue Jahre beginnen mit einem leeren Stundenplan und ohne Klassen.",
                    classes="form-hint",
                )
                yield Button("Stundenzeiten", id="edit-periods")
                yield Button("Über PULT / Lizenz", id="show-about")
            with Horizontal(classes="form-actions"):
                yield Static(classes="form-action-spacer")
                yield Button("Abbrechen", id="cancel-settings")
                yield Button("Speichern", variant="primary", id="save-settings")

    @on(Button.Pressed, "#cancel-settings")
    def action_cancel(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, "#edit-periods")
    def edit_periods(self) -> None:
        try:
            periods = load_periods(self.app_config.root)
        except (OSError, ValueError) as error:
            self.notify(
                f"Stundenzeiten konnten nicht geladen werden: {error}", severity="error"
            )
            return
        self.app.push_screen(EditPeriodsScreen(periods))

    @on(Button.Pressed, "#show-about")
    def show_about(self) -> None:
        self.app.push_screen(AboutScreen())

    @on(Button.Pressed, "#save-settings")
    def save_settings(self) -> None:
        editor = self.query_one("#settings-editor", Select).value
        year = self.query_one("#settings-year", Select).value
        if editor is Select.NULL or year is Select.NULL:
            return
        try:
            updated = update_settings(self.app_config, str(editor), str(year))
        except (OSError, ValueError) as error:
            self.notify(
                f"Einstellungen konnten nicht gespeichert werden: {error}",
                severity="error",
            )
            return
        self.dismiss(updated)
