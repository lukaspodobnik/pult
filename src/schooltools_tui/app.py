from typing import ClassVar

from textual.app import App

from schooltools_tui.config import AppConfig, load_app_config, save_app_config
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

    def __init__(self) -> None:
        super().__init__()
        self.app_config: AppConfig | None = None

    def on_mount(self) -> None:
        self.theme = "gruvbox"
        self.app_config = load_app_config()

        if self.app_config is None:
            self.push_screen(SetupScreen(), self.finish_setup,)
        else:
            self.push_screen(HomeScreen(self.app_config))

    def finish_setup(self, app_config: AppConfig | None) -> None:
        assert app_config is not None

        save_app_config(app_config)
        self.app_config = app_config
        self.push_screen(HomeScreen(app_config))

    def action_show_home(self) -> None:
        if self.app_config is None:
            self.notify("Schooltools muss zuerst eingerichtet werden.")
            return

        if isinstance(self.screen, HomeScreen):
            return

        self.switch_screen(HomeScreen(self.app_config))
