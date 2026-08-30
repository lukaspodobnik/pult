from typing import ClassVar

from textual.app import App

from schooltools_tui.config import AppConfig, load_app_config, save_app_config
from schooltools_tui.screens.home import HomeScreen
from schooltools_tui.screens.school_year_setup import SchoolYearSetupScreen
from schooltools_tui.screens.setup import SetupScreen


class SchooltoolsApp(App):
    CSS_PATH: ClassVar = [
        "styles/app.tcss",
        "styles/home.tcss",
        "styles/setup.tcss",
        "styles/school_year_setup.tcss",
    ]

    TITLE = "Schooltools"
    SUB_TITLE = "Schulalltag im Blick"

    BINDINGS: ClassVar = [
        ("q", "quit", "Beenden"),
        ("h", "show_home", "Home"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.app_config: AppConfig | None = None

    def require_config(self) -> AppConfig:
        if self.app_config is None:
            raise RuntimeError("AppConfig wurde vor abschluss des Setups angefordert.")

        return self.app_config

    def on_mount(self) -> None:
        self.theme = "gruvbox"
        self.app_config = load_app_config()
        self.show_initial_screen()

    def show_initial_screen(self) -> None:
        if self.app_config is None:
            self.push_screen(
                SetupScreen(),
                self.on_setup_complete,
            )
            return

        if self.app_config.active_school_year is None:
            self.push_screen(
                SchoolYearSetupScreen(),
                self.on_school_year_setup_complete,
            )
            return

        self.push_screen(HomeScreen())

    def on_setup_complete(self, app_config: AppConfig | None) -> None:
        assert app_config is not None
        self.app_config = app_config
        self.show_initial_screen()

    def on_school_year_setup_complete(self, year: str | None) -> None:
        if year is None:
            self.show_initial_screen()
            return

        app_config = self.require_config()
        app_config.active_school_year = year
        save_app_config(app_config)
        self.show_initial_screen()

    def action_show_home(self) -> None:
        if self.app_config is None:
            self.notify("Schooltools muss zuerst eingerichtet werden.")
            return

        if self.app_config.active_school_year is None:
            self.notify(
                "Bitte richte zuerst ein Schuljahr ein.",
                severity="warning",
            )
            return

        if isinstance(self.screen, HomeScreen):
            return

        self.switch_screen(HomeScreen())
