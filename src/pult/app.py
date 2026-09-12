from dataclasses import replace
from datetime import datetime
from typing import ClassVar
from zoneinfo import ZoneInfo

from textual.app import App
from textual.events import Event, Key
from textual.widgets import Input, TextArea

from pult.config import AppConfig, load_app_config
from pult.presentation import format_school_year
from pult.screens.confirmation_screen import ConfirmationScreen
from pult.screens.main_screen import MainScreen
from pult.screens.setup_pult_screen import SetupScreen
from pult.services.omarchy_theme import OmarchyThemeWatcher
from pult.services.sequence_library import SequenceLibrary
from pult.services.settings import get_suggested_school_year, update_settings
from pult.services.themes import standard_theme


class PultApp(App):
    CSS_PATH: ClassVar = [
        "styles/app.tcss",
        "styles/home.tcss",
        "styles/classes.tcss",
        "styles/calendar.tcss",
        "styles/progress.tcss",
        "styles/sequences.tcss",
        "styles/lesson.tcss",
        "styles/setup.tcss",
        "styles/school_year_setup.tcss",
        "styles/teaching_log.tcss",
    ]

    TITLE = "PULT"
    SUB_TITLE = "Schulalltag im Blick"
    ENABLE_COMMAND_PALETTE = False

    BINDINGS: ClassVar = [
        ("q", "quit", "Beenden"),
    ]

    async def on_event(self, event: Event) -> None:
        """Behandle h/j/k/l außerhalb von Textfeldern wie die Pfeiltasten."""
        if (
            isinstance(event, Key)
            and event.key in ("h", "j", "k", "l")
            and self.focused is not None
            and not isinstance(self.focused, (Input, TextArea))
        ):
            directions = {"h": "left", "j": "down", "k": "up", "l": "right"}
            event = Key(directions[event.key], None)
        await super().on_event(event)

    def __init__(self) -> None:
        super().__init__()
        self.app_config: AppConfig | None = None
        self.sequence_library: SequenceLibrary | None = None
        self.omarchy_theme = OmarchyThemeWatcher()
        self._theme_slot = 0

    def require_config(self) -> AppConfig:
        """Gib die geladene Config zurück oder melde einen ungültigen App-Zustand."""
        if self.app_config is None:
            raise RuntimeError("AppConfig wurde vor Abschluss des Setups angefordert.")

        return self.app_config

    def require_sequence_library(self) -> SequenceLibrary:
        """Gib den gemeinsamen Bibliothekscache der laufenden App zurück."""
        if self.sequence_library is None:
            raise RuntimeError(
                "SequenceLibrary wurde vor Abschluss des Setups angefordert."
            )

        return self.sequence_library

    def on_mount(self) -> None:
        theme = standard_theme()
        self.register_theme(theme)
        self.theme = theme.name
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
        theme = replace(theme, name=f"pult-omarchy-{self._theme_slot}")
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
        self.call_after_refresh(self.offer_school_year_change)

    def offer_school_year_change(self) -> None:
        # Ein verzögerter Aufruf kann noch während des App-Abbaus eintreffen.
        if not self.screen_stack or not isinstance(self.screen, MainScreen):
            return
        if self.screen._pending_view_id is not None:
            self.set_timer(0.1, self.offer_school_year_change)
            return
        config = self.require_config()
        try:
            year = get_suggested_school_year(
                config, datetime.now(ZoneInfo("Europe/Berlin")).date()
            )
        except (OSError, ValueError) as error:
            self.notify(
                f"Schuljahreswechsel konnte nicht geprüft werden: {error}",
                severity="warning",
            )
            return
        if year is None:
            return

        def selected(confirmed: bool | None) -> None:
            if not confirmed:
                return
            try:
                updated = update_settings(config, config.editor, year)
            except (OSError, ValueError) as error:
                self.notify(
                    f"Schuljahr konnte nicht gewechselt werden: {error}",
                    severity="error",
                )
                return
            self.app_config = updated
            self.switch_screen(MainScreen())

        self.push_screen(
            ConfirmationScreen(
                "Schuljahr wechseln?",
                f"Das Schuljahr {format_school_year(year)} hat begonnen. Möchtest du zu diesem Jahr wechseln? Vorhandene Daten bleiben erhalten.",
                confirm_id="confirm-year-change",
                cancel_id="cancel-year-change",
            ),
            selected,
        )

    def on_setup_complete(self, app_config: AppConfig | None) -> None:
        assert app_config is not None
        self.app_config = app_config
        self.show_initial_screen()
