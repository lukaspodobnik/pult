from typing import ClassVar

from textual import on, work
from textual.app import ComposeResult
from textual.widgets import Input, Label, Select, Static

from pult.config import AppConfig
from pult.school.assessment_requirements import load_assessment_requirements
from pult.school.period import load_periods
from pult.school.school_year import get_school_year_options
from pult.school.subject import load_subjects
from pult.screens.about_screen import AboutScreen
from pult.screens.base_screen import PultModalScreen
from pult.screens.edit_assessment_requirements_screen import (
    EditAssessmentRequirementsScreen,
)
from pult.screens.edit_periods_screen import EditPeriodsScreen
from pult.screens.renderer_setup_screen import RendererSetupScreen
from pult.services.settings import get_editor_options, update_settings
from pult.widgets.button import Button
from pult.widgets.form_dialog import FormDialog, FormFields
from pult.widgets.scrolling import Horizontal


class SettingsScreen(PultModalScreen[AppConfig | None]):
    BINDINGS: ClassVar = [("escape", "cancel", "Abbrechen")]
    DEFAULT_CSS = """
    SettingsScreen #edit-periods, SettingsScreen #edit-requirements, SettingsScreen #show-about, SettingsScreen #setup-renderer {
        width: 100%;
        margin: 0;
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
                yield Button("Dokumentdarstellung einrichten", id="setup-renderer")
                yield Label("Dokumentschrift", classes="field-label")
                yield Select(
                    [("Automatisch", "auto"), ("Source Sans 3", "source-sans-3")],
                    value=(
                        config.document_font
                        if config.document_font != "avenir-next"
                        else "auto"
                    ),
                    allow_blank=False,
                    disabled=True,
                    id="settings-document-font",
                )
                yield Static("Schriftverfügbarkeit wird geprüft …", id="font-status")
                yield Label("Name auf Arbeitsblättern", classes="field-label")
                yield Input(
                    config.export_author,
                    placeholder="Optional",
                    id="settings-export-author",
                    max_length=80,
                )
                yield Label("Schuljahr", classes="field-label")
                yield Select(
                    get_school_year_options(config.root),
                    value=config.active_school_year,
                    allow_blank=False,
                    id="settings-year",
                )
                yield Button("Leistungsnachweise", id="edit-requirements")
                yield Button("Stundenzeiten", id="edit-periods")
                yield Button("Über PULT / Lizenz", id="show-about")
            with Horizontal(classes="form-actions"):
                yield Static(classes="form-action-spacer")
                yield Button("Abbrechen", id="cancel-settings")
                yield Button("Speichern", variant="primary", id="save-settings")

    def on_mount(self) -> None:
        self.call_after_refresh(self.load_font_options)

    @work(exclusive=True, group="font-options")
    async def load_font_options(self) -> None:
        picker = self.query_one("#settings-document-font", Select)
        selected = self.app_config.document_font if picker.disabled else picker.value
        available = await self.pult_app.document_renderer.avenir_available()
        if not self.is_mounted:
            return
        picker = self.query_one("#settings-document-font", Select)
        options = [("Automatisch", "auto")]
        if available:
            options.append(("Avenir Next", "avenir-next"))
        options.append(("Source Sans 3", "source-sans-3"))
        picker.set_options(options)
        picker.value = selected if available or selected != "avenir-next" else "auto"
        picker.disabled = False
        self.query_one("#font-status", Static).update(
            "Automatisch: Avenir Next"
            if available
            else "Automatisch: Source Sans 3 · Avenir Next nicht verfügbar"
        )

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

    @on(Button.Pressed, "#edit-requirements")
    def edit_requirements(self) -> None:
        year = self.query_one("#settings-year", Select).value
        if year is Select.NULL:
            return
        try:
            entries = load_assessment_requirements(self.app_config.root, str(year))
            subjects = {
                subject.id: subject.name
                for subject in load_subjects(self.app_config.root)
            }
        except (OSError, ValueError) as error:
            self.notify(
                f"LNW-Vorgaben konnten nicht geladen werden: {error}", severity="error"
            )
            return
        self.app.push_screen(
            EditAssessmentRequirementsScreen(str(year), entries, subjects)
        )

    @on(Button.Pressed, "#setup-renderer")
    def setup_renderer(self) -> None:
        self.app.push_screen(RendererSetupScreen(), self.renderer_setup_finished)

    def renderer_setup_finished(self, ready: bool | None) -> None:
        if ready:
            self.load_font_options()

    @on(Button.Pressed, "#show-about")
    def show_about(self) -> None:
        self.app.push_screen(AboutScreen())

    @on(Button.Pressed, "#save-settings")
    def save_settings(self) -> None:
        editor = self.query_one("#settings-editor", Select).value
        year = self.query_one("#settings-year", Select).value
        font_picker = self.query_one("#settings-document-font", Select)
        font = (
            self.app_config.document_font if font_picker.disabled else font_picker.value
        )
        if editor is Select.NULL or year is Select.NULL or font is Select.NULL:
            return
        try:
            updated = update_settings(
                self.app_config,
                str(editor),
                str(year),
                str(font),
                export_author=self.query_one("#settings-export-author", Input).value,
            )
        except (OSError, ValueError) as error:
            self.notify(
                f"Einstellungen konnten nicht gespeichert werden: {error}",
                severity="error",
            )
            return
        self.dismiss(updated)
