from typing import ClassVar

from textual.app import App

from schooltools_tui.config import AppConfig, load_app_config
from schooltools_tui.screens.home import HomeScreen
from schooltools_tui.screens.setup import SetupScreen


class SchooltoolsApp(App):
    CSS_PATH = "schooltools.tcss"
    
    TITLE = "Schooltools"
    SUB_TITLE = "Schulalltag im Blick"

    BINDINGS: ClassVar = [
        ("q", "quit", "Beenden"),
        ("h", "show_home", "Home"),
    ]

    app_config: AppConfig | None = None

    def on_mount(self) -> None:
        self.theme = "gruvbox"
        self.app_config = load_app_config()

        if self.app_config is None:
            self.push_screen(SetupScreen())
        else:
            self.push_screen(HomeScreen(self.app_config))

    def action_show_home(self) -> None:
        if self.app_config is None:
            self.notify("Schooltools muss zuerst eingerichtet werden.")
            return

        if isinstance(self.screen, HomeScreen):
            return

        self.switch_screen(HomeScreen(self.app_config))
