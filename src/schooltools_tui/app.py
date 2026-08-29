from typing import ClassVar

from textual.app import App
from textual.widgets import Static

from schooltools_tui.config import load_app_config
from schooltools_tui.screens.home import HomeScreen


class SchooltoolsApp(App):
    CSS_PATH = "schooltools.tcss"
    
    TITLE = "Schooltools"
    SUB_TITLE = "Schulalltag im Blick"

    BINDINGS: ClassVar = [
        ("q", "quit", "Beenden"),
        ("h", "show_home", "Home"),
    ]

    def __init__(self):
        self.app_config = load_app_config()

    def on_mount(self) -> None:
        self.theme = "gruvbox"

        if self.app_config is None:
            pass
        else:
            self.push_screen(HomeScreen(self.app_config))

    def action_show_home(self) -> None:
        assert self.app_config is not None
        self.push_screen(HomeScreen(self.app_config))
