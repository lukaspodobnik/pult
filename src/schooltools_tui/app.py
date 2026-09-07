from dataclasses import replace
from typing import ClassVar

from textual.app import App

from schooltools_tui.config import AppConfig, load_app_config
from schooltools_tui.screens.main_screen import MainScreen
from schooltools_tui.screens.setup_school_tools_screen import SetupScreen
from schooltools_tui.services.omarchy_theme import OmarchyThemeWatcher
from schooltools_tui.services.sequence_library import SequenceLibrary


class SchooltoolsApp(App):
    CSS_PATH: ClassVar = [
        "styles/app.tcss",
        "styles/home.tcss",
        "styles/classes.tcss",
        "styles/calendar.tcss",
        "styles/progress.tcss",
        "styles/sequences.tcss",
        "styles/setup.tcss",
        "styles/school_year_setup.tcss",
        "styles/teaching_log.tcss",
    ]

    TITLE = "Schooltools"
    SUB_TITLE = "Schulalltag im Blick"
    ENABLE_COMMAND_PALETTE = False

    BINDINGS: ClassVar = [
        ("q", "quit", "Beenden"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.app_config: AppConfig | None = None
        self.sequence_library: SequenceLibrary | None = None
        self.omarchy_theme = OmarchyThemeWatcher()
        self._theme_slot = 0

    def require_config(self) -> AppConfig:
        """Gib die geladene Config zurück oder melde einen ungültigen App-Zustand."""
        if self.app_config is None:
            raise RuntimeError("AppConfig wurde vor abschluss des Setups angefordert.")

        return self.app_config

    def require_sequence_library(self) -> SequenceLibrary:
        """Gib den gemeinsamen Bibliothekscache der laufenden App zurück."""
        if self.sequence_library is None:
            raise RuntimeError(
                "SequenceLibrary wurde vor Abschluss des Setups angefordert."
            )

        return self.sequence_library

    def on_mount(self) -> None:
        self.theme = "gruvbox"
        self.refresh_omarchy_theme()
        self.set_interval(1, self.refresh_omarchy_theme)
        self.app_config = load_app_config()
        self.show_initial_screen()

    def refresh_omarchy_theme(self) -> None:
        """Übernimm neue Farben ohne Screens, Eingaben oder Fokus neu aufzubauen."""
        theme = self.omarchy_theme.poll()
        if theme is None:
            return
        # Zwei Namen lösen auch beim erneuten Anwenden desselben Omarchy-Themes
        # Textuals reaktiven Themewechsel aus, ohne unbegrenzt Themes anzusammeln.
        self._theme_slot = 1 - self._theme_slot
        theme = replace(theme, name=f"schooltools-omarchy-{self._theme_slot}")
        self.register_theme(theme)
        self.theme = theme.name

    def show_initial_screen(self) -> None:
        """Öffne abhängig vom Vorhandensein der Config Setup oder Hauptansicht."""
        if self.app_config is None:
            self.push_screen(
                SetupScreen(),
                self.on_setup_complete,
            )
            return

        if (
            self.sequence_library is None
            or self.sequence_library.root != self.app_config.root
        ):
            self.sequence_library = SequenceLibrary(self.app_config.root)
        self.push_screen(MainScreen())

    def on_setup_complete(self, app_config: AppConfig | None) -> None:
        assert app_config is not None
        self.app_config = app_config
        self.show_initial_screen()
